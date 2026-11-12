"""Read GHost SQLite snapshots and emit only public preview statistics (stdlib)."""
import argparse
from collections import Counter, defaultdict
from contextlib import closing
import json
from pathlib import Path
import sqlite3
from lod_modes import game_mode, replay_index
from rating import replay

MAPS = {'classic':'DotA_v6.85n_RB_Allstars.w3x', 'newyear':'DotA v6.85k Allstars.w3x', 'lod':'DotAv6.85ozLoD.w3x'}
BOTS = {'ghost','hostclassic','hostnewyear','hostlod'}
COLOURS = set(range(1,6)) | set(range(7,12))
METRICS = ('kills','deaths','assists','creepkills','creepdenies','neutralkills','towerkills','raxkills','courierkills')

# Saddzz played these two games on a replacement account. Credit the
# original account in the public export while retaining the recorded roster.
MATCH_PLAYER_CORRECTIONS = {
    ('lod', 17, '2026-11-11 18:54:13'): ('saddzz', 'saddz'),
    ('lod', 18, '2026-11-11 19:59:28'): ('saddzz', 'saddz'),
}

MODE_LADDERS = (
    ('lod-4x4', 'DotA LoD 4×4 · без мида', 4, 'no-mid'),
    ('lod-3x3', 'DotA LoD 3×3 · только мид', 3, 'only-mid'),
)


def mode_ladder(label, size, lane, events, histories, people):
    result = replay((event for event in events if event.get('lane_mode') == lane), size)
    awards = result['match_awards']
    matches = []
    for event_id, match in histories:
        if event_id not in awards:
            continue
        rows = [{**row, **awards[event_id][row['name'].casefold()]} for row in match['players']]
        matches.append({**match, 'rated': True, 'players': rows})
    matches.sort(key=lambda match: (match['date'], int(match['id'].rsplit('-', 1)[1])), reverse=True)
    player_matches = defaultdict(list)
    for match in matches:
        for row in match['players']:
            player_matches[row['name'].casefold()].append((match['id'], row))

    players = []
    for identity, state in result['players'].items():
        base = people[identity]
        recent = player_matches[identity]
        last = next((row for _, row in recent if row['hero']), {})
        players.append(dict(name=base['name'], clan=base['clan'], portrait=base['portrait'],
                            appearances=state['rated_games'], result_games=state['rated_games'],
                            all_result_games=state['rated_games'], all_wins=state['wins'],
                            all_losses=state['losses'], last_hero=last.get('hero'),
                            hero_name=last.get('hero_name'),
                            recent_match_ids=[match_id for match_id, _ in recent[:10]],
                            **{f'all_{metric}': state[metric] for metric in METRICS}, **state))
    players.sort(key=lambda player: (-player['mmr'], -player['wins'], -player['xp'], player['name'].casefold()))
    for rank, player in enumerate(players, 1):
        player['rank'] = rank
    retained = {match_id for player in players for match_id in player['recent_match_ids']}
    count = result['rated_matches']
    return dict(label=label, maps=[MAPS['lod']], players=players, recorded_matches=count,
                completed_matches=count, rated_matches=count, rated_match_ids=result['match_ids'],
                matches=[match for match in matches if match['id'] in retained])


def read_snapshot(path):
    path = Path(path).resolve(strict=True)
    with closing(sqlite3.connect(path.as_uri()+'?mode=ro', uri=True, timeout=10)) as source:
        snapshot = sqlite3.connect(':memory:')
        source.backup(snapshot)
    snapshot.row_factory = sqlite3.Row
    return snapshot


def load_display_names(directory):
    """Read only the public username field, never serialize account records."""
    result={}
    if not Path(directory).is_dir(): return result
    expected='BNET'+chr(92)+'acct'+chr(92)+'username'
    for path in Path(directory).iterdir():
        if not path.is_file() or path.is_symlink(): continue
        for line in path.read_text(encoding='utf-8',errors='replace').splitlines():
            left,sep,right=line.partition('=')
            if sep and left.strip().strip('"').replace(chr(92)*2,chr(92))==expected:
                name=right.strip().strip('"')
                if name and len(name)<=32 and not any(ord(c)<32 for c in name):result[name.casefold()]=name
    return result


def export(sources,display_names=None,hero_catalog=None):
    display_names=display_names or {};hero_catalog=hero_catalog or {}
    pools = {key:dict(label=label, maps=maps, players=[], matches=[], recorded_matches=0, completed_matches=0) for key,label,maps in [
        ('classic','DotA Classic',[MAPS['classic'],MAPS['newyear']]), ('lod','DotA LoD',[MAPS['lod']])]}
    people = {'classic':{},'lod':{}}
    events = {'classic':[],'lod':[]}
    histories = {'classic':[],'lod':[]}
    hero_seen={}
    for profile, path in sorted(sources.items()):
        if profile not in MAPS: raise ValueError('Unknown map profile')
        poolkey = 'lod' if profile=='lod' else 'classic'
        pool, players = pools[poolkey], people[poolkey]
        replays = replay_index(Path(path).parent/'replays') if profile == 'lod' else {}
        db = read_snapshot(path)
        try:
            tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if not {'games','gameplayers'} <= tables: raise ValueError('Missing game tables')
            columns={r[1] for r in db.execute('PRAGMA table_info(games)')}
            extra=','.join(name if name in columns else 'NULL AS '+name for name in ('duration','gamename'))
            for game in db.execute('SELECT id,map,datetime,'+extra+' FROM games ORDER BY id'):
                if str(game['map']).replace('\\','/').split('/')[-1] != MAPS[profile]: continue
                pool['recorded_matches'] += 1
                roster = [dict(r) for r in db.execute('SELECT name,team,colour FROM gameplayers WHERE gameid=?',(game['id'],))
                          if r['team'] in (0,1) and r['colour'] in COLOURS and r['name'].casefold() not in BOTS]
                correction = MATCH_PLAYER_CORRECTIONS.get((profile, game['id'], game['datetime']))
                if correction:
                    source, destination = correction
                    participants = [row for row in roster if row['name'].casefold() == source]
                    if len(participants) != 1 or any(row['name'].casefold() == destination for row in roster):
                        raise ValueError(f"Ambiguous player correction in {profile}-{game['id']}")
                    participants[0]['name'] = display_names.get(destination, destination)
                identities = Counter(r['name'].casefold() for r in roster)
                colours = Counter(r['colour'] for r in roster)
                # Ambiguous identity/slot joins must not silently create player results.
                roster = [r for r in roster if identities[r['name'].casefold()]==1 and colours[r['colour']]==1]
                for r in roster:
                    key = r['name'].casefold()
                    if key not in players:
                        players[key] = dict(name=display_names.get(key,r['name']), rank=None, level=1, progress=0, clan='', portrait=None,
                                            xp=0, mmr=1000, wins=0, losses=0, appearances=0, result_games=0,rated_games=0,
                                            all_wins=None,all_losses=None,all_result_games=0,
                                            **{m:0 for m in METRICS})
                    players[key]['appearances'] += 1
                if not {'dotagames','dotaplayers'} <= tables: continue
                results = list(db.execute('SELECT winner FROM dotagames WHERE gameid=?',(game['id'],)))
                if len(results)!=1 or results[0]['winner'] not in (1,2): continue
                stats = [dict(r) for r in db.execute('SELECT * FROM dotaplayers WHERE gameid=?',(game['id'],))]
                stats_colours = Counter(r['colour'] for r in stats)
                final_colours = Counter(r.get('newcolour',r['colour']) for r in stats)
                if any(n!=1 for n in stats_colours.values()) or any(n!=1 for n in final_colours.values()): continue
                joined = [(r,s) for r in roster for s in stats if r['colour']==s['colour'] and s.get('newcolour',s['colour']) in COLOURS]
                if joined: pool['completed_matches'] += 1
                event=dict(id=f"{profile}:{game['id']:012d}",date=game['datetime'] or '',winner=results[0]['winner'],players=[])
                match=dict(id=f"{profile}-{game['id']}",date=game['datetime'] or '',map_profile=profile,
                           map=MAPS[profile],name=game['gamename'] or '',duration_seconds=game['duration'],
                           winner=results[0]['winner'],team_sizes=[sum(r['team']==t for r in roster) for t in (0,1)],
                           rated=False,replay_url=None,players=[])
                if profile == 'lod':
                    mode = game_mode(game, replays)
                    if mode:
                        event['lane_mode'], match['mode_source'] = mode
                        match['lane_mode'] = mode[0]
                for r,s in joined:
                    p = players[r['name'].casefold()]
                    final_colour = s.get('newcolour',s['colour'])
                    team = 1 if final_colour<=5 else 2
                    p['all_wins'] = (p['all_wins'] or 0) + int(team==results[0]['winner'])
                    p['all_losses'] = (p['all_losses'] or 0) + int(team!=results[0]['winner'])
                    p['all_result_games'] += 1
                    for metric in METRICS:
                        if s.get(metric) is not None: p['all_'+metric] = (p.get('all_'+metric) or 0)+int(s[metric])
                    hero_order=(game['datetime'] or '',profile,game['id'])
                    hero_identity=(poolkey,r['name'].casefold())
                    if s.get('hero') and hero_order>=hero_seen.get(hero_identity,('','',-1)):
                        hero_seen[hero_identity]=hero_order
                        p['last_hero'] = str(s['hero'])[:4]
                        p['hero_name'] = hero_catalog.get(profile,{}).get(p['last_hero'])
                    event['players'].append(dict(name=r['name'],team=team,start_team=r['team']+1,**{m:int(s.get(m) or 0) for m in METRICS}))
                final_stats={r['name'].casefold():s for r,s in joined}
                for r in roster:
                    s=final_stats.get(r['name'].casefold(),{})
                    colour=s.get('newcolour',s.get('colour'))
                    team=(1 if colour<=5 else 2) if colour in COLOURS else None
                    hero=str(s.get('hero') or '')[:4]
                    match['players'].append(dict(name=players[r['name'].casefold()]['name'],team=team,start_team=r['team']+1,
                                                hero=hero,hero_name=hero_catalog.get(profile,{}).get(hero),
                                                mmr_before=None,mmr_after=None,mmr_delta=None,xp_gained=None,
                                                **{m:int(s[m]) if s.get(m) is not None else None for m in (*METRICS,'gold')}))
                # Preserve the complete start roster requirement even if result rows are partial.
                event['roster_valid']=(len(roster)==len(identities)==len(colours)==len(event['players']))
                events[poolkey].append(event)
                histories[poolkey].append((event['id'],match))
        finally:
            db.close()
    for key, pool in pools.items():
        result=replay(events[key]);pool['rated_matches']=result['rated_matches'];pool['rated_match_ids']=result['match_ids']
        for identity,state in result['players'].items():
            people[key][identity].update(state)
            people[key][identity]['result_games']=state['rated_games']
        pool['players']=sorted(people[key].values(),key=lambda p:(not bool(p['rated_games']),-p['mmr'],-p['wins'],-p['xp'],p['name'].casefold()))
        ranked=0
        for p in pool['players']:
            if p['rated_games']: ranked+=1;p['rank']=ranked
        matches=[]
        for event_id,match in histories[key]:
            match['rated']=event_id in result['match_awards']
            for p in match['players']:
                p.update(result['match_awards'].get(event_id,{}).get(p['name'].casefold(),{}))
            matches.append(match)
        matches.sort(key=lambda m:(m['date'],m['map_profile'],int(m['id'].rsplit('-',1)[1])),reverse=True)
        retained=set()
        for p in pool['players']:
            p['recent_match_ids']=[m['id'] for m in matches if any(r['name'].casefold()==p['name'].casefold() for r in m['players'])][:10]
            retained.update(p['recent_match_ids'])
        pool['matches']=[m for m in matches if m['id'] in retained]
    for key, label, size, lane in MODE_LADDERS:
        pools[key] = mode_ladder(label, size, lane, events['lod'], histories['lod'], people['lod'])
    return dict(schema_version=1,status='active',rating_status='active',rating_version=1,pools=pools)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root',type=Path,default=Path('/opt/warcraft-iii-online/hostbot/dota-profiles'))
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    userdir=Path('/var/lib/docker/volumes/warcraft-iii-online_pvpgn-test-state/_data/pvpgn/users')
    catalog_path=Path(__file__).with_name('hero_names.json')
    catalog=json.loads(catalog_path.read_text(encoding='utf-8')) if catalog_path.exists() else {}
    result = export({key:args.root/key/'ghost.dbs' for key in MAPS},load_display_names(userdir),catalog)
    payload = json.dumps(result,ensure_ascii=False,indent=2)+'\n'
    args.output.parent.mkdir(parents=True,exist_ok=True)
    if args.output.exists() and args.output.read_text(encoding='utf-8')==payload:
        print('PUBLIC_STATS_UNCHANGED')
        return
    temporary = args.output.with_suffix('.tmp')
    temporary.write_text(payload,encoding='utf-8')
    temporary.chmod(0o644)
    temporary.replace(args.output)
    print('PUBLIC_STATS_UPDATED', {key:len(pool['players']) for key,pool in result['pools'].items()})


if __name__=='__main__': main()
