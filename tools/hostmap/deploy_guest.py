"""Stage guest hosting closed, probe privately, then explicitly publish. No game restarts."""
import argparse
import json
import os
from pathlib import Path
import shutil
import sqlite3
import time
from deploy import ROOT,PROJECT,run,inspect,same_before
from enable_uploads import SITE,MARKER,write_owned,nginx_check_reload
from ui_assets import WEB_FILES


def workers():
    return {name:dict(id=v['Id'],pid=v['State']['Pid'],started=v['State']['StartedAt'])
            for name in ('hostmap1','hostmap2') for v in [inspect(PROJECT+'-'+name+'-1')]}


def guard():
    same_before()
    if workers()!=json.loads((ROOT/'guest-workers-before.json').read_text()):
        raise RuntimeError('A game worker changed; inspect before continuing')


def prepare():
    same_before()
    marker=ROOT/'controller/guest-enabled'
    if marker.exists(): raise RuntimeError('Guest access is already enabled; inspect before updating')
    baseline=ROOT/'guest-workers-before.json'
    if baseline.exists(): guard()
    else: baseline.write_text(json.dumps(workers(),indent=2)+'\n')
    backup=ROOT/'backups'/('guest-web-'+str(int(time.time())))
    backup.mkdir(parents=True,mode=0o700)
    shutil.copyfile(ROOT/'compose.json',backup/'compose.json')
    shutil.copytree(ROOT/'app',backup/'app')
    with sqlite3.connect(ROOT/'controller/hostmap.db') as source,sqlite3.connect(backup/'hostmap.db') as destination:
        source.backup(destination)
    (backup/'hostmap.db').chmod(0o600)
    for path in ROOT.glob('*.py'): shutil.copyfile(path,ROOT/'app'/path.name)
    destination=ROOT/'app/web';destination.mkdir(exist_ok=True)
    for name in WEB_FILES:
        shutil.copyfile(ROOT/'web'/name,destination/name)
    public=Path('/var/www/wc3-hostmap')
    ownership=public/'.hostmap-owned'
    if public.is_symlink() or (public.exists() and not ownership.is_file()):
        raise RuntimeError('Unexpected public webroot')
    public.mkdir(parents=True,exist_ok=True);public.chmod(0o755)
    ownership.write_text('HostMap static frontend only\n')
    for name in WEB_FILES:
        temporary=public/(name+'.next')
        shutil.copyfile(ROOT/'web'/name,temporary);temporary.chmod(0o644);os.replace(temporary,public/name)
    compose=json.loads((ROOT/'compose.json').read_text())
    expected=['python3','/app/uploads.py']
    if compose['services']['uploads']['entrypoint'] not in (expected,['python3','/app/guest_http.py']):
        raise RuntimeError('Unexpected receiver entrypoint')
    compose['services']['uploads']['entrypoint']=['python3','/app/guest_http.py']
    temporary=ROOT/'compose.guest-next.json';temporary.write_text(json.dumps(compose,indent=2)+'\n')
    os.replace(temporary,ROOT/'compose.json')
    command=['docker','compose','-p',PROJECT,'-f',str(ROOT/'compose.json')]
    run(*command,'up','-d','--no-deps','--force-recreate','uploads')
    # Imports all new modules together; workers remain the old, untouched image/processes.
    run(*command,'restart','controller')
    current=SITE.read_text()
    if not current.startswith(MARKER): raise RuntimeError('Foreign nginx site')
    line='    server_name maps.wc3.uplay2.ru;'
    position=current.index('    listen 443 ssl;')
    prefix,suffix=current[:position],current[position:]
    suffix=suffix.replace('limit_conn hostmap_upload_conn 4;','limit_conn hostmap_upload_conn 8;')
    redirect='    if ($host != maps.wc3.uplay2.ru) { return 308 https://maps.wc3.uplay2.ru/; }'
    if redirect not in suffix:
        suffix=suffix.replace(line,line+'\n'+redirect,1)
    # Buffer only the bounded control body; large maps still stream through the receiver's quota guard.
    if 'location = /api/host' not in suffix:
        location='''    location = /api/host {
        client_max_body_size 1k;
        client_body_timeout 5s;
        proxy_pass http://127.0.0.1:6129;
        proxy_http_version 1.1;
        proxy_request_buffering on;
        proxy_buffering off;
        proxy_set_header Host maps.wc3.uplay2.ru;
        proxy_set_header X-Forwarded-Proto https;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_connect_timeout 3s;
        proxy_send_timeout 5s;
        proxy_read_timeout 10s;
    }
'''
        suffix=suffix.replace('    location / {',location+'    location / {',1)
    if 'location = / {' not in suffix:
        static='''    location = / {
        root /var/www/wc3-hostmap;
        try_files /index.html =404;
        add_header Cache-Control "no-store";
        add_header X-Content-Type-Options "nosniff";
        add_header Content-Security-Policy "default-src 'none'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self'; connect-src 'self'; form-action 'self'; frame-ancestors 'none'";
    }
    location ~ ^/web/__HOSTMAP_STATIC_FILES__$ {
        alias /var/www/wc3-hostmap/$1;
        add_header Cache-Control "no-store";
        add_header X-Content-Type-Options "nosniff";
    }
    location /web/ { return 404; }
'''
        static=static.replace('__HOSTMAP_STATIC_FILES__','('+'|'.join(re.escape(n) for n in WEB_FILES if n!='index.html')+')')
        suffix=suffix.replace('    location / {',static+'    location / {',1)
    if prefix+suffix!=current: write_owned(SITE,prefix+suffix,nginx_check_reload)
    guard()
    (ROOT/'guest-prepared.json').write_text(json.dumps(dict(prepared=True,public=False,backup=str(backup)))+'\n')
    print('GUEST_WEB_PREPARED_CLOSED; WORKER_RESTARTS=0; BACKUP='+str(backup))


def publish():
    # This final action needs action-time confirmation for new anonymous public access.
    guard()
    result=json.loads((ROOT/'guest-probe-verified.json').read_text())
    if not all(result.get(k) for k in ('renamed_script_rejected','fake_mpq_rejected','valid_map_published','guest_room_advertised')):
        raise RuntimeError('The private guest proof did not pass')
    marker=ROOT/'controller/guest-enabled'
    with marker.open('x') as stream: stream.write('approved-public-guest-web\n')
    os.chown(marker,10003,10005);marker.chmod(0o640)
    run('docker','compose','-p',PROJECT,'-f',str(ROOT/'compose.json'),'restart','uploads')
    guard()
    (ROOT/'guest-published.json').write_text(json.dumps(dict(public=True,time=int(time.time())))+'\n')
    print('GUEST_WEB_PUBLIC; GAME_WORKER_RESTARTS=0; PERMANENT_SERVICES_UNCHANGED')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['prepare','publish'])
    {'prepare':prepare,'publish':publish}[parser.parse_args().action]()
