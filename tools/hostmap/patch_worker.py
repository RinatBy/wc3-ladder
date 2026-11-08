"""Patch an isolated upstream tree. Every anchor must match once; never patch production."""
from pathlib import Path
import shutil
import sys


def replace(root, name, old, new):
    path = root / 'ghost' / name
    text = path.read_text()
    if text.count(old) != 1:
        raise RuntimeError(f'Unexpected upstream anchor: {name}: {old[:65]!r}')
    path.write_text(text.replace(old, new), newline='\n')


def patch(root):
    root = Path(root)
    replace(root, 'ghost.h', '\tCUDPSocket *m_UDPSocket;',
            '\tbool m_HostMapPublic;\n\tuint32_t m_HostMapLastStatus;\n\tCUDPSocket *m_UDPSocket;')
    replace(root, 'ghost.cpp', '\tm_LCPings = CFG->GetInt(',
            '\tm_HostMapPublic = CFG->GetInt( "hostmap_public", 0 ) == 1;\n'
            '\tm_HostMapLastStatus = 0;\n\tm_LCPings = CFG->GetInt(')
    replace(root, 'ghost.cpp', '\t// get rid of any deleted games', '''
    if( m_HostMapPublic && GetTime() != m_HostMapLastStatus ) {
        bool logged = !m_BNETs.empty() && m_BNETs[0]->GetLoggedIn();
        ofstream status("/state/hostmap.status.tmp");
        status << GetTime() << "\\t" << ((m_CurrentGame || !m_Games.empty() || !logged) ? 1 : 0) << "\\n";
        status.close();
        rename("/state/hostmap.status.tmp", "/state/hostmap.status");
        m_HostMapLastStatus = GetTime();
    }
\t// get rid of any deleted games''')
    replace(root, 'bnet.cpp', '#include <boost/filesystem.hpp>', '#include <boost/filesystem.hpp>\n#include <regex>')
    replace(root, 'bnet.cpp', '\tif( IsAdmin( User ) || IsRootAdmin( User ) || ForceRoot )\n\t{', '''
    if( m_GHost->m_HostMapPublic ) {
        // A realm-authenticated controller, never arbitrary players, can select a map.
        if( !Whisper || !IsRootAdmin(User) || Command != "hmhost" ) return;
        string Code, Owner, Name;
        uint32_t Issued = 0;
        stringstream request(Payload);
        request >> Issued >> Code >> Owner;
        getline(request, Name);
        if( !Name.empty() && Name[0] == ' ' ) Name.erase(0,1);
        if( GetTime() < Issued || GetTime()-Issued > 30 ||
            !regex_match(Code, regex("[a-f0-9]{12}")) ||
            !regex_match(Owner, regex("[A-Za-z0-9_\\\\[\\\\].()-]{1,15}")) ||
            !regex_match(Name, regex("[A-Za-z0-9][A-Za-z0-9 _.,!()\\\\[\\\\]+-]{0,29}")) ) return;
        {
            boost::mutex::scoped_lock lock(m_GHost->m_GamesMutex);
            if( m_GHost->m_CurrentGame || !m_GHost->m_Games.empty() ) return;
        }
        CConfig MapCFG;
        MapCFG.Read(m_GHost->m_MapCFGPath + Code + ".cfg");
        m_GHost->m_Map->Load(&MapCFG, Code + ".cfg");
        if( !m_GHost->m_Map->GetValid() ) {
            QueueChatCommand("Map is incompatible with this Warcraft version.", Owner, true);
            return;
        }
        m_GHost->CreateGame(m_GHost->m_Map, GAME_PUBLIC, false, Name, Owner, User, m_Server, true);
        QueueChatCommand("Room requested: " + Name + ". In the lobby all players type !go.", Owner, true);
        return;
    }
\tif( IsAdmin( User ) || IsRootAdmin( User ) || ForceRoot )
\t{''')
    replace(root, 'game_base.h', '#include "gameslot.h"', '#include "gameslot.h"\n#include "hostmap_ready.hpp"')
    replace(root, 'game_base.h', '\tCGHost *m_GHost;',
            '\thostmap::Ready m_HostMapReady;\n\tvoid SyncHostMapReady();\n\tCGHost *m_GHost;')
    path = root/'ghost'/'game_base.cpp'
    text = path.read_text()
    anchor = 'if( JoinedRealm.empty( ) )\n\t\tPlayer->SetSpoofed( true );'
    if text.count(anchor) != 2:
        raise RuntimeError('Unexpected LAN authentication anchors')
    path.write_text(text.replace(anchor, 'if( JoinedRealm.empty( ) && !m_GHost->m_HostMapPublic )\n\t\tPlayer->SetSpoofed( true );'))
    replace(root, 'game_base.cpp', '\t// countdown every 500 ms', '''
    if( m_GHost->m_HostMapPublic && !m_GameLoading && !m_GameLoaded ) SyncHostMapReady();
\t// countdown every 500 ms''')
    replace(root, 'game_base.cpp', 'bool CBaseGame :: EventPlayerBotCommand( CGamePlayer *player, string command, string payload )', '''
void CBaseGame :: SyncHostMapReady() {
    if( !m_GHost->m_HostMapPublic ) return;
    stringstream fingerprint;
    set<unsigned> voters;
    bool allowed = true;
    for( unsigned sid = 0; sid < m_Slots.size(); ++sid ) {
        CGameSlot &slot = m_Slots[sid];
        fingerprint << sid << ":" << (unsigned)slot.GetPID() << ":" <<
            (unsigned)slot.GetSlotStatus() << ":" << (unsigned)slot.GetComputer() << ":" <<
            (unsigned)slot.GetTeam() << ";";
    }
    for( vector<CGamePlayer*>::iterator i = m_Players.begin(); i != m_Players.end(); ++i ) {
        CGamePlayer *p = *i;
        unsigned sid = GetSIDFromPID(p->GetPID());
        fingerprint << (unsigned)p->GetPID() << ":" << p->GetName() << ";";
        if( sid >= m_Slots.size() || p->GetDeleteMe() || !p->GetSpoofed() ||
            m_Slots[sid].GetDownloadStatus() != 100 ) allowed = false;
        if( sid < m_Slots.size() && !m_Slots[sid].GetComputer() &&
            m_Slots[sid].GetTeam() != MAX_SLOTS && !p->GetDeleteMe() ) voters.insert(p->GetPID());
    }
    if( m_HostMapReady.sync(fingerprint.str(), voters, allowed) && m_CountDownStarted ) {
        m_CountDownStarted = false;
        SendAllChat("Roster changed. All players must type !go again.");
    }
}

bool CBaseGame :: EventPlayerBotCommand( CGamePlayer *player, string command, string payload )''')
    replace(root, 'game.cpp', '\tbool AdminCheck = false;', '''
    if( m_GHost->m_HostMapPublic ) {
        if( m_GameLoading || m_GameLoaded ) return true;
        SyncHostMapReady();
        if( Command == "go" || Command == "start" || Command == "votestart" ) {
            if( !player->GetSpoofed() ) {
                SendChat(player, "Confirm your account: /w " + m_GHost->m_BNETs[0]->GetUserName() + " sc");
                return true;
            }
            unsigned sid = GetSIDFromPID(player->GetPID());
            if( sid >= m_Slots.size() || m_Slots[sid].GetTeam() == MAX_SLOTS ) return true;
            if( m_HostMapReady.vote(player->GetPID()) ) {
                if( !m_CountDownStarted ) StartCountDown(false);
            } else SendAllChat("Ready: " + UTIL_ToString(m_HostMapReady.count()) + "/" +
                UTIL_ToString(m_HostMapReady.total()) + ". All players must download the map, confirm accounts and type !go.");
            return true;
        }
        if( Command == "ping" ) {
            // Upstream !ping with payload can kick players, so erase it for public use.
            Payload.clear();
        } else if( !player->GetSpoofed() || !IsOwner(User) ||
            !(Command == "swap" || Command == "open" || Command == "close" ||
              Command == "sp" || Command == "kick" || Command == "unhost" || Command == "abort") ) return true;
    }
\tbool AdminCheck = false;''')
    # Allow the harmless ping implementation to execute without promoting the user elsewhere.
    replace(root, 'game.cpp', '\n\tif( player->GetSpoofed( ) && ( AdminCheck || RootAdminCheck || IsOwner( User ) ) )',
            '\n\tif( player->GetSpoofed( ) && ( AdminCheck || RootAdminCheck || IsOwner( User ) || (m_GHost->m_HostMapPublic && Command == "ping") ) )')
    replace(root, 'game.cpp', '\t\t\t\tm_CountDownStarted = false;',
            '\t\t\t\tm_CountDownStarted = false;\n                if(m_GHost->m_HostMapPublic) m_HostMapReady.clear();')
    shutil.copyfile(Path(__file__).with_name('ready.hpp'), root/'ghost'/'hostmap_ready.hpp')
    print('HOSTMAP_WORKER_PATCHED')


if __name__ == '__main__':
    patch(Path(sys.argv[1]))
