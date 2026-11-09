"""Add only HostMap's HTTPS virtual host; preserve existing certificates and games."""
import argparse
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import socket
import subprocess
import time
from urllib.request import Request, urlopen
from urllib.error import HTTPError

from deploy import ROOT, PROJECT, same_before, run, inspect as container_info
from finish import unit

DOMAIN='maps.wc3.uplay2.ru'
URL='https://'+DOMAIN+'/'
WEBROOT=Path('/var/lib/wc3-hostmap-acme')
SITE=Path('/etc/nginx/conf.d/wc3-hostmap-upload.conf')
MARKER='# HostMap managed upload endpoint\n'


def certificate_command(account):
    if not re.fullmatch('[a-f0-9]{32,64}',account): raise ValueError('Unexpected ACME account')
    # Existing registration only. Do not silently accept new Terms of Service.
    return ['certbot','certonly','--webroot','-w',str(WEBROOT),'--cert-name',DOMAIN,
        '-d',DOMAIN,'--account',account,'--non-interactive','--keep-until-expiring',
        '--deploy-hook','/usr/bin/systemctl reload nginx']


def set_upload_url(path,url):
    path=Path(path)
    if url not in (None,URL) or path.is_symlink(): raise ValueError('Unexpected controller setting')
    metadata=path.stat()
    value=json.loads(path.read_text())
    if set(value)!={'workers','upload_url'} or value['workers']!=['HostMap1','HostMap2']:
        raise ValueError('Unexpected controller config')
    value['upload_url']=url
    temporary=path.with_name('.upload-config-'+secrets.token_hex(8))
    try:
        with temporary.open('x') as stream:
            stream.write(json.dumps(value)+'\n')
        temporary.chmod(0o600)
        if hasattr(os,'chown'): os.chown(temporary,metadata.st_uid,metadata.st_gid)
        os.replace(temporary,path)
    finally:
        temporary.unlink(missing_ok=True)


def write_owned(path,text,check):
    path=Path(path)
    if path.is_symlink() or not text.startswith(MARKER): raise ValueError('Unexpected site path')
    old=path.read_text() if path.exists() else None
    if old is not None and not old.startswith(MARKER): raise ValueError('Foreign nginx configuration')
    temporary=path.with_name(path.name+'.hostmap-next')
    try:
        with temporary.open('x') as stream: stream.write(text)
        temporary.chmod(0o644)
        os.replace(temporary,path)
        try:
            check()
        except BaseException:
            if old is None: path.unlink(missing_ok=True)
            else: path.write_text(old)
            raise
    finally:
        temporary.unlink(missing_ok=True)


def site_config(tls=False):
    text=MARKER+f'''server {{
    listen 80;
    listen [::]:80;
    server_name {DOMAIN};
    location ^~ /.well-known/acme-challenge/ {{
        root {WEBROOT};
        try_files $uri =404;
    }}
    location / {{ {'return 301 https://'+DOMAIN+'$request_uri;' if tls else 'return 404;'} }}
}}
'''
    if not tls: return text
    return text+f'''
limit_req_zone $binary_remote_addr zone=hostmap_upload_rate:1m rate=6r/s;
limit_conn_zone $binary_remote_addr zone=hostmap_upload_conn:1m;
server {{
    listen 443 ssl;
    listen [::]:443 ssl;
    server_name {DOMAIN};
    ssl_certificate /etc/letsencrypt/live/{DOMAIN}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/{DOMAIN}/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_session_cache shared:HostMapTLS:1m;
    ssl_session_timeout 1d;
    client_max_body_size 32m;
    client_header_timeout 10s;
    client_body_timeout 30s;
    keepalive_timeout 10s;
    access_log /var/log/nginx/hostmap-upload.access.log;
    error_log /var/log/nginx/hostmap-upload.error.log warn;
    limit_conn hostmap_upload_conn 4;
    limit_req zone=hostmap_upload_rate burst=12 nodelay;
    location / {{
        proxy_pass http://127.0.0.1:6129;
        proxy_http_version 1.1;
        proxy_request_buffering off;
        proxy_buffering off;
        proxy_set_header Host {DOMAIN};
        proxy_set_header X-Forwarded-Proto https;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_connect_timeout 3s;
        proxy_send_timeout 65s;
        proxy_read_timeout 65s;
    }}
}}
'''


def nginx_check_reload():
    run('nginx','-t',stderr=subprocess.STDOUT)
    run('systemctl','reload','nginx')


def wait_http(url,expected,seconds=12,contains=False):
    # A successful reload signals the master before old workers stop accepting.
    # Keep certificate verification enabled while waiting for the new vhost.
    deadline=time.monotonic()+seconds
    last=None
    while time.monotonic()<deadline:
        try:
            with urlopen(url,timeout=min(3,max(0.1,deadline-time.monotonic()))) as response:
                body=response.read(65536)
                if response.status==200 and (expected in body if contains else body==expected): return
        except HTTPError as error:
            error.close()
            last=error
        except OSError as error:
            last=error
        time.sleep(0.25)
    raise RuntimeError('HTTP/TLS vhost did not become ready') from last


def prepare_http():
    same_before()
    addresses={a[4][0] for a in socket.getaddrinfo(DOMAIN,80,socket.AF_INET)}
    if addresses!={'176.124.218.23'}: raise RuntimeError('DNS does not point only to the authorized VDS')
    configuration=run('nginx','-T',stderr=subprocess.STDOUT)
    if DOMAIN in configuration and not SITE.exists(): raise RuntimeError('Hostname already configured elsewhere')
    WEBROOT.mkdir(parents=True,exist_ok=True)
    WEBROOT.chmod(0o755)
    write_owned(SITE,site_config(False),nginx_check_reload)
    challenge=WEBROOT/'.well-known/acme-challenge'
    challenge.mkdir(parents=True,exist_ok=True)
    challenge.chmod(0o755)
    (WEBROOT/'.well-known').chmod(0o755)
    token=secrets.token_hex(12)
    probe=challenge/('hostmap-'+token)
    probe.write_text(token);probe.chmod(0o644)
    try:
        wait_http('http://'+DOMAIN+'/.well-known/acme-challenge/'+probe.name,token.encode())
    finally:
        probe.unlink(missing_ok=True)
    same_before()
    print('HOSTMAP_HTTP_CHALLENGE_READY; EXISTING_GAMES_UNCHANGED')


def certificate():
    same_before()
    accounts=list(Path('/etc/letsencrypt/accounts/acme-v02.api.letsencrypt.org/directory').glob('*/regr.json'))
    if len(accounts)!=1: raise RuntimeError('Expected one existing ACME registration; no new agreement will be accepted automatically')
    registration=json.loads(accounts[0].read_text())
    if registration.get('body',{}).get('status','valid')!='valid': raise RuntimeError('Existing ACME account is not valid')
    subprocess.run(certificate_command(accounts[0].parent.name),check=True,timeout=150)
    same_before()
    print('HOSTMAP_CERTIFICATE_READY')


def activate():
    same_before()
    if run('systemctl','is-active','warcraft-iii-hostmap.service')!='active':
        raise RuntimeError('HostMap parent unit must already be active; do not start it during matches')
    def workers():
        result={}
        for name in ('hostmap1','hostmap2'):
            value=container_info(PROJECT+'-'+name+'-1')
            result[name]=dict(id=value['Id'],pid=value['State']['Pid'],started=value['State']['StartedAt'])
        return result
    workers_before=workers()
    (ROOT/'uploads-workers-before.json').write_text(json.dumps(workers_before,indent=2)+'\n')
    cert=Path('/etc/letsencrypt/live')/DOMAIN/'fullchain.pem'
    run('openssl','x509','-in',str(cert),'-noout','-checkhost',DOMAIN)
    run('openssl','x509','-in',str(cert),'-noout','-checkend','86400')
    source=ROOT/'uploads.py'
    if source.is_symlink(): raise RuntimeError('Unexpected receiver source')
    shutil.copyfile(source,ROOT/'app/uploads.py')
    compose=['docker','compose','-p',PROJECT,'-f',str(ROOT/'compose.json')]
    # Only the idle, loopback receiver is updated; game workers keep their matches.
    run(*compose,'restart','uploads')
    for _ in range(12):
        try:
            with urlopen('http://127.0.0.1:6129/',timeout=2) as response:
                if response.status==200: break
        except OSError: time.sleep(1)
    else: raise RuntimeError('Loopback map receiver unavailable')
    write_owned(SITE,site_config(True),nginx_check_reload)
    wait_http(URL,b'HostMap',contains=True)
    unit('warcraft-iii-hostmap-maps.service',f'''[Unit]
Description=Warcraft HostMap isolated map validation queue
Requires=docker.service warcraft-iii-hostmap.service
After=docker.service warcraft-iii-hostmap.service
[Service]
Type=simple
WorkingDirectory={ROOT}
ExecStart=/usr/bin/python3 {ROOT}/broker.py
Restart=on-failure
RestartSec=5
Group=10005
UMask=0077
NoNewPrivileges=true
CapabilityBoundingSet=
ProtectSystem=strict
ProtectHome=true
PrivateTmp=true
PrivateDevices=true
ReadWritePaths={ROOT}/controller {ROOT}/incoming {ROOT}/validation {ROOT}/assets/maps {ROOT}/assets/mapcfgs
RestrictAddressFamilies=AF_UNIX
MemoryMax=128M
TasksMax=64
CPUQuota=25%
Environment=PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 DOCKER_HOST=unix:///var/run/docker.sock
[Install]
WantedBy=multi-user.target
''')
    run('systemctl','daemon-reload')
    run('systemctl','enable','--now','warcraft-iii-hostmap-maps.service')
    if run('systemctl','is-active','warcraft-iii-hostmap-maps.service')!='active': raise RuntimeError('Map broker unavailable')
    config=ROOT/'config/controller.json'
    try:
        set_upload_url(config,URL)
        # The chat controller reconnects; game workers are separate processes.
        run(*compose,'restart','controller')
        same_before()
        if workers()!=workers_before: raise RuntimeError('A game worker changed during upload activation')
    except BaseException:
        set_upload_url(config,None)
        run(*compose,'restart','controller')
        raise
    (ROOT/'uploads-enabled.json').write_text(json.dumps(dict(url=URL,enabled=True,time=int(time.time())))+'\n')
    print('HOSTMAP_HTTPS_UPLOAD_ENABLED; WORKER_RESTARTS=0; PERMANENT_GAMES_UNCHANGED')


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=['prepare-http','certificate','activate'])
    action=parser.parse_args().action
    {'prepare-http':prepare_http,'certificate':certificate,'activate':activate}[action]()
