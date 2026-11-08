"""Owner-specific, additive deployment. Never restarts or rewrites the realm/DotA services."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import time

from core import Store, read_status, fresh

ROOT=Path('/opt/warcraft-iii-online/hostmap')
BASE=ROOT.parent
IMAGE='warcraft-iii-hostmap:trial'
PROJECT='warcraft-iii-hostmap'
WORKERS={'HostMap1':6117,'HostMap2':6118}
PERMANENT=['warcraft-iii-online-pvpgn-1']+['warcraft-iii-dota-bots-'+p+'-1' for p in ('classic','newyear','lod')]


def run(*args,**kwargs):
    return subprocess.check_output(args,text=True,timeout=kwargs.pop('timeout',90),**kwargs).strip()


def inspect(name): return json.loads(run('docker','inspect',name))[0]


def snapshot():
    return {n:{'id':v['Id'],'pid':v['State']['Pid'],'started':v['State']['StartedAt']} for n in PERMANENT for v in [inspect(n)]}


def same_before():
    before=json.loads((ROOT/'before.json').read_text())
    if snapshot()!=before:
        raise RuntimeError('A pre-existing service changed; investigate before continuing')


def mkdir(path,uid=0,gid=0,mode=0o755):
    path.mkdir(parents=True,exist_ok=True)
    if path.is_symlink(): raise RuntimeError('Unexpected symlink')
    os.chown(path,uid,gid);path.chmod(mode)


def private(path,content,uid,gid):
    if path.exists():
        if path.is_symlink() or path.read_text()!=content: raise RuntimeError('Existing private config differs: '+path.name)
    else:
        with path.open('x') as stream: stream.write(content)
    os.chown(path,uid,gid);path.chmod(0o600)


def credential(path,name,uid,gid):
    if path.exists():
        if path.is_symlink() or json.loads(path.read_text())['account']!=name: raise RuntimeError('Unexpected existing account file')
    else:
        private(path,json.dumps(dict(account=name,password=secrets.token_hex(20)))+'\n',uid,gid)
    return json.loads(path.read_text())


def python_in_image(script,*args,credentials=None,uid=10002,gid=10002):
    mounts=['-v',str(ROOT)+':/app:ro','-v',str(ROOT/'assets')+':/assets:ro']
    if credentials: mounts+=['-v',str(credentials)+':/credentials.json:ro']
    return run('docker','run','--rm','--network','host','--read-only','--user',f'{uid}:{gid}',
        '--memory','128m','--cpus','0.25','--pids-limit','32','--cap-drop','ALL',
        '--security-opt','no-new-privileges:true','--tmpfs','/tmp:rw,noexec,nosuid,size=16m',
        *mounts,'--entrypoint','python3',IMAGE,'/app/'+script,*args)


def prepare():
    assert os.getuid()==0 and socket.gethostname().startswith('3589885-io30655')
    if (ROOT/'compose.json').exists(): raise RuntimeError('Already prepared; inspect rather than overwrite')
    if (ROOT/'build.exit').read_text().strip()!='0': raise RuntimeError('Image build has not passed')
    image=inspect(IMAGE)['Id']
    shipped=run('docker','run','--rm','--network','none','--read-only','--entrypoint','sha256sum',image,'/app/patch_worker.py').split()[0]
    if shipped!=hashlib.sha256((ROOT/'patch_worker.py').read_bytes()).hexdigest():
        raise RuntimeError('Loaded image does not contain the current reviewed worker patch')
    for port in WORKERS.values():
        with socket.socket() as listener: listener.bind(('176.124.218.23',port))
    if os.statvfs(ROOT).f_bavail*os.statvfs(ROOT).f_frsize<1024**3: raise RuntimeError('Insufficient disk reserve')
    if (ROOT/'before.json').exists(): same_before()
    else: (ROOT/'before.json').write_text(json.dumps(snapshot(),indent=2)+'\n')
    for path in ('assets','assets/auth','assets/maps','assets/mapcfgs','workers','status'):
        mkdir(ROOT/path)
    mkdir(ROOT/'controller',10003,10005,0o2770)
    mkdir(ROOT/'config',10003,10005,0o700)
    mkdir(ROOT/'incoming',10004,10005,0o2770)
    mkdir(ROOT/'validation',0,0,0o700)
    original=BASE/'hostbot/assets'
    for src,target in [(original/'auth/Warcraft III.exe',ROOT/'assets/auth/Warcraft III.exe'),
                       (original/'realm-public-modulus.bin',ROOT/'assets/realm-public-modulus.bin')]+[
                       (original/'mapcfgs'/n,ROOT/'assets/mapcfgs'/n) for n in ('common.j','blizzard.j')]:
        if not target.exists(): shutil.copyfile(src,target)
        if hashlib.sha256(src.read_bytes()).digest()!=hashlib.sha256(target.read_bytes()).digest(): raise RuntimeError('Asset mismatch')
        target.chmod(0o444)
    store=Store(ROOT/'controller/hostmap.db',list(WORKERS))
    os.chown(store.path,10003,10005);store.path.chmod(0o660)
    from broker import publish
    initial=[('EchoIsles.w3x','Echo Isles'),('DotAv6.85ozLoD.w3x','DotA LoD 6.85oz'),
             ('DotA_v6.85n_RB_Allstars.w3x','DotA Classic 6.85n'),('DotA v6.85k Allstars.w3x','DotA NewYear 6.85k')]
    default=None
    for filename,title in initial:
        source=original/'maps'/filename
        if not source.is_file(): continue
        digest=hashlib.sha256(source.read_bytes()).hexdigest()
        # These are the existing operator-selected maps, not untrusted uploads.
        with store.db() as db:
            db.execute("INSERT OR IGNORE INTO jobs (id,owner,digest,ext,title,bytes,state) VALUES (?,?,?,?,?,?,?)",
                (digest[:32],'uPlay',digest,'w3x',title,source.stat().st_size,'pending'))
        publish(store,dict(id=digest[:32],digest=digest,ext='w3x',title=title),source)
        if filename=='EchoIsles.w3x': default=digest[:12]
    if not default: raise RuntimeError('Echo Isles asset missing')
    manager_cred=ROOT/'config/credentials.json'
    credential(manager_cred,'HostMap',10003,10005)
    private(ROOT/'config/controller.json',json.dumps(dict(workers=list(WORKERS),upload_url=None))+'\n',10003,10005)
    print(python_in_image('bootstrap.py','/credentials.json',credentials=manager_cred,uid=10003,gid=10005),flush=True)
    services={}
    def service(user,memory,cpu,volumes,entry=None):
        config=dict(image=image,restart='unless-stopped',network_mode='host',user=user,read_only=True,
            mem_limit=memory,cpus=cpu,pids_limit=64,cap_drop=['ALL'],security_opt=['no-new-privileges:true'],
            tmpfs=['/tmp:rw,noexec,nosuid,size=16m,mode=1777'],volumes=volumes,
            logging=dict(driver='json-file',options={'max-size':'2m','max-file':'2'}))
        if entry: config['entrypoint']=entry
        return config
    for name,port in WORKERS.items():
        state=ROOT/'workers'/name
        mkdir(state,10002,10002,0o700)
        mkdir(ROOT/'status'/name,10002,10002)
        creds=credential(state/'credentials.json',name,10002,10002)
        print(python_in_image('bootstrap.py','/credentials.json',credentials=state/'credentials.json'),flush=True)
        cfg=dict(hostmap_public='1',bot_log='/state/ghost.log',bot_logmethod='1',
            bot_language='/opt/ghost/language.cfg',bot_war3path='/assets/auth/',bot_tft='1',
            bot_bindaddress='176.124.218.23',bot_hostport=str(port),bot_reconnect='0',bot_maxgames='1',
            bot_commandtrigger='!',bot_mapcfgpath='/assets/mapcfgs/',bot_mappath='/assets/maps/',
            bot_defaultmap=default+'.cfg',bot_savereplays='0',bot_spoofchecks='1',bot_requirespoofchecks='1',
            bot_allowdownloads='1',bot_maxdownloaders='2',bot_maxdownloadspeed='512',bot_lobbytimelimit='10',
            bot_reserveadmins='0',bot_localadminmessages='0',bot_latency='30',bot_synclimit='50',
            bot_ipblacklistfile='',bot_motdfile='/state/motd.txt',bot_gameloadedfile='/state/motd.txt',
            bot_gameoverfile='/state/motd.txt',replay_war3version='29',replay_buildnumber='6060',
            lan_war3version='29',admingame_create='0',udp_broadcasttarget='127.0.0.1',autohost_maxgames='0',
            db_type='sqlite3',db_sqlite3_file='/state/ghost.dbs',bnet_server='176.124.218.23',
            bnet_serveralias='Warcraft VDS',bnet_cdkeyroc='F'*26,bnet_cdkeytft='F'*26,
            bnet_username=name,bnet_password=creds['password'],bnet_firstchannel='Warcraft Admin',
            bnet_rootadmin='HostMap',bnet_commandtrigger='!',bnet_publiccommands='0',bnet_locale='1033',
            bnet_custom_war3version='29',bnet_custom_exeversion='15 2 29 1',bnet_custom_exeversionhash='129 40 237 254',
            bnet_custom_passwordhashtype='',bnet_custom_pvpgnrealmname='PvPGN Realm')
        private(state/'ghost.cfg',''.join(k+' = '+v+'\n' for k,v in cfg.items()),10002,10002)
        private(state/'motd.txt','HostMap: all players type !go when ready. Owner: !swap, !open, !close, !kick, !unhost.\n',10002,10002)
        services[name.lower()]=service('10002:10002','192m',0.25,[str(state)+':/state',
            str(ROOT/'assets')+':/assets:ro',str(ROOT/'status'/name)+':/status'])
    services['controller']=service('10003:10005','64m',0.15,[str(ROOT)+':/app:ro',
        str(ROOT/'controller')+':/state',str(ROOT/'config')+':/config:ro',
        str(ROOT/'status')+':/workers:ro',str(ROOT/'assets')+':/assets:ro'],['python3','/app/controller.py'])
    # Receiver is loopback-only. No capabilities are issued until TLS is configured.
    services['uploads']=service('10004:10005','64m',0.15,[str(ROOT)+':/app:ro',
        str(ROOT/'controller')+':/data',str(ROOT/'incoming')+':/incoming'],['python3','/app/uploads.py'])
    # Do not expose ROOT recursively: app source has no service credentials but ROOT now does.
    mkdir(ROOT/'app')
    for source in ROOT.glob('*.py'): shutil.copyfile(source,ROOT/'app'/source.name)
    for key in ('controller','uploads'):
        services[key]['volumes']=[str(ROOT/'app')+':/app:ro' if v==str(ROOT)+':/app:ro' else v for v in services[key]['volumes']]
    (ROOT/'compose.json').write_text(json.dumps(dict(services=services),indent=2)+'\n')
    (ROOT/'prepared.json').write_text(json.dumps(dict(image=image,workers=WORKERS,maps=store.maps()))+'\n')
    same_before()
    print('HOSTMAP_PREPARED; FIREWALL_UNCHANGED; TLS_UPLOAD_DISABLED')


def start():
    same_before()
    run('docker','compose','-p',PROJECT,'-f',str(ROOT/'compose.json'),'up','-d','--no-build')
    deadline=time.monotonic()+75
    while time.monotonic()<deadline:
        values=[read_status(ROOT/'status'/w/'hostmap.status') for w in WORKERS]
        try: controller=json.loads((ROOT/'controller/controller.status.json').read_text())
        except (OSError,ValueError): controller={}
        if all(fresh(s,int(time.time())) and not s['busy'] for s in values) and fresh(controller,int(time.time())) and controller.get('authenticated'):
            same_before()
            print('HOSTMAP_AUTHENTICATED; TWO_WORKERS_READY; EXISTING_BOTS_UNCHANGED')
            return
        time.sleep(2)
    raise RuntimeError('New HostMap service did not become ready; inspect its logs')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=['prepare','start','status'])
    args=parser.parse_args()
    if args.action=='prepare': prepare()
    elif args.action=='start': start()
    else:
        same_before()
        print((ROOT/'controller/controller.status.json').read_text())
        print('PERMANENT_SERVICES_UNCHANGED')


if __name__=='__main__': main()
