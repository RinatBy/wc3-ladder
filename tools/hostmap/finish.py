"""Complete private probe, then publish only when the owner authorizes the new ports."""
import argparse
import json
import os
from pathlib import Path
import secrets
import time
from deploy import ROOT, BASE, PROJECT, WORKERS, credential, python_in_image, run, same_before
from core import Store


def probe():
    same_before()
    path=ROOT/'config/probe.json'
    credential(path,'HostMapProbe',10003,10005)
    print(python_in_image('bootstrap.py','/credentials.json',credentials=path,uid=10003,gid=10005),flush=True)
    store=Store(ROOT/'controller/hostmap.db',list(WORKERS))
    item=next(m for m in store.maps('Echo') if m['title']=='Echo Isles')
    report=json.loads(python_in_image('probe.py',item['code'],'HostMap Check '+secrets.token_hex(2),
        credentials=path,uid=10003,gid=10005))
    with store.db() as db:
        row=db.execute('SELECT worker,room FROM leases WHERE owner=?',('HostMapProbe',)).fetchone()
    if not row or row['room']!=report['room']: raise RuntimeError('Probe lease not found')
    port=WORKERS[row['worker']]
    connections=run('ss','-Htan','state','established',f'( sport = :{port} )')
    if connections: raise RuntimeError('Test room has a client; leave it running')
    # Firewall remains closed; only retire the proven self-test room, never another room.
    run('docker','compose','-p',PROJECT,'-f',str(ROOT/'compose.json'),'restart',row['worker'].lower())
    same_before()
    report['permanent_services_unchanged']=True
    (ROOT/'probe-result.json').write_text(json.dumps(report,indent=2)+'\n')
    print('HOSTMAP_PROBE_OK',json.dumps(report),flush=True)


def unit(name,contents):
    path=Path('/etc/systemd/system')/name
    if path.exists() and path.read_text()!=contents: raise RuntimeError('Refusing to replace an existing unit')
    if not path.exists(): path.write_text(contents)


def persist():
    same_before()
    unit('warcraft-iii-hostmap.service',f'''[Unit]
Description=Warcraft III HostMap public hosting
Requires=docker.service
After=docker.service network-online.target warcraft-iii-online.service
Wants=network-online.target
[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory={ROOT}
ExecStart=/usr/bin/docker compose -p {PROJECT} -f {ROOT}/compose.json up -d --no-build
ExecStop=/usr/bin/docker compose -p {PROJECT} -f {ROOT}/compose.json stop
TimeoutStartSec=90
TimeoutStopSec=40
[Install]
WantedBy=multi-user.target
''')
    run('systemctl','daemon-reload')
    run('systemctl','enable','--now','warcraft-iii-hostmap.service')
    same_before()
    print('HOSTMAP_AUTOSTART_ENABLED; FIREWALL_UNCHANGED')


def publish():
    same_before()
    report=json.loads((ROOT/'probe-result.json').read_text())
    if not report.get('realm_advertised'): raise RuntimeError('Private probe has not passed')
    # This action requires explicit confirmation of new public TCP ports 6117-6118.
    run('ufw','allow','6117:6118/tcp','comment','Warcraft HostMap rooms')
    same_before()
    (ROOT/'published.json').write_text(json.dumps(dict(ports=[6117,6118],public=True,uploaded_maps_enabled=False,
        time=int(time.time())))+'\n')
    print('HOSTMAP_PUBLIC_PORTS_6117_6118_OPEN; PERMANENT_BOTS_UNCHANGED')


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=['probe','persist','publish'])
    action=parser.parse_args().action
    {'probe':probe,'persist':persist,'publish':publish}[action]()
