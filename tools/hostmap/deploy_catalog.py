"""Upgrade only the map receiver/broker and static frontend; preserve active games."""
import http.client
import json
import os
import shutil
import sqlite3
import time
from deploy import ROOT, PROJECT, run
from deploy_chrome import processes, main as style


def probe():
    headers={'Host':'maps.wc3.uplay2.ru','Origin':'https://maps.wc3.uplay2.ru','X-Real-IP':'192.0.2.254'}
    def request(method,path,data=b''):
        connection=http.client.HTTPConnection('127.0.0.1',6129,timeout=5)
        try:
            connection.request(method,path,body=data,headers=headers)
            response=connection.getresponse();body=json.loads(response.read())
            if response.status!=200: raise RuntimeError('Catalog probe failed: '+str(response.status))
            if method=='POST' and path=='/api/session':
                headers['Cookie']=response.getheader('Set-Cookie').split(';')[0]
                headers['X-CSRF-Token']=body['csrf']
            return body
        finally: connection.close()
    request('POST','/api/session')
    result=request('GET','/api/maps')
    if result['maps']:
        chosen=result['maps'][0]
        state=request('POST','/api/select',json.dumps(dict(code=chosen['code'])).encode())
        if state['job']['id']!='map:'+chosen['code']: raise RuntimeError('Selection probe failed')
    return len(result['maps'])


def main():
    before=processes();marker=ROOT/'controller/guest-enabled';access=marker.read_bytes()
    if access!=b'approved-public-guest-web\n': raise RuntimeError('Unexpected access state')
    with sqlite3.connect(ROOT/'controller/hostmap.db') as db:
        if db.execute("SELECT 1 FROM jobs WHERE state IN ('receiving','pending')").fetchone():
            raise RuntimeError('An upload is in progress; retry after validation finishes')
    if '/broker.py' not in run('systemctl','show','warcraft-iii-hostmap-maps.service','--property=ExecStart','--value'):
        raise RuntimeError('Unexpected broker service')
    backup=ROOT/'backups'/('catalog-'+str(int(time.time())))
    backup.mkdir(parents=True,mode=0o700)
    with sqlite3.connect(ROOT/'controller/hostmap.db') as source,sqlite3.connect(backup/'hostmap.db') as destination:
        source.backup(destination)
    (backup/'hostmap.db').chmod(0o600)
    if (ROOT/'.broker-before-catalog.py').is_file():
        shutil.copyfile(ROOT/'.broker-before-catalog.py',backup/'broker.py')
    for name in ('guest.py','guest_http.py','uploads.py'):
        target=ROOT/'app'/name
        shutil.copyfile(target,backup/name)
        temporary=target.with_suffix('.catalog-next')
        shutil.copyfile(ROOT/name,temporary);temporary.chmod(0o644);os.replace(temporary,target)
    run('docker','compose','-p',PROJECT,'-f',str(ROOT/'compose.json'),'restart','uploads')
    run('systemctl','restart','warcraft-iii-hostmap-maps.service')
    for attempt in range(15):
        try: count=probe();break
        except (OSError,ValueError,http.client.HTTPException): time.sleep(0.3)
    else: raise RuntimeError('Map receiver did not become ready')
    style()
    after=processes()
    protected={k:v for k,v in before.items() if k!=PROJECT+'-uploads-1'}
    if any(after[k]!=v for k,v in protected.items()) or marker.read_bytes()!=access:
        raise RuntimeError('A game/controller process or access state changed')
    if run('systemctl','is-active','warcraft-iii-hostmap-maps.service')!='active': raise RuntimeError('Broker inactive')
    with sqlite3.connect(ROOT/'controller/hostmap.db') as db:
        maps=db.execute('SELECT count(*) FROM maps').fetchone()[0]
    result=dict(catalog_visible=count,map_records=maps,map_files=len(list((ROOT/'assets/maps').glob('*.w3?'))),game_restarts=0,controller_restarts=0,guest_access_unchanged=True,backup=str(backup))
    (ROOT/'catalog-verified.json').write_text(json.dumps(result,indent=2)+'\n')
    print('HOSTMAP_CATALOG_DEPLOYED '+json.dumps(result))


if __name__=='__main__':main()
