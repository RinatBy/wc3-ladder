"""Private loopback HTTP proof against the real bounded queue/controller, no login links."""
import http.client
import json
import os
from pathlib import Path
import secrets
import threading
import time
from core import Store,read_status,fresh
from deploy import ROOT,WORKERS
from deploy_guest import guard
from guest import Guest
from guest_http import GuestHandler,GuestServer


def main():
    guard();os.setgid(10005);os.umask(0o007)
    server=GuestServer(('127.0.0.1',6130),GuestHandler)
    server.store=Store(ROOT/'controller/hostmap.db',list(WORKERS))
    server.guest=Guest(server.store);server.incoming=ROOT/'incoming';server.trust_proxy=True;server.enabled=True
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    base=int(time.time())%200+1

    def client(index):
        ip='192.0.2.'+str((base+index)%250+1); cookie='';csrf=''
        def request(method,path,data=b'',headers=None):
            connection=http.client.HTTPConnection('127.0.0.1',6130,timeout=45)
            try:
                connection.request(method,path,body=data,headers={'Host':'maps.wc3.uplay2.ru',
                    'Origin':'https://maps.wc3.uplay2.ru','X-Real-IP':ip,'Cookie':cookie,'X-CSRF-Token':csrf,**(headers or {})})
                reply=connection.getresponse(); status=reply.status; body=json.loads(reply.read())
                return status,dict(reply.getheaders()),body
            finally: connection.close()
        status,headers,body=request('POST','/api/session')
        if status!=200: raise RuntimeError('Guest session failed')
        cookie=headers['Set-Cookie'].split(';')[0];csrf=body['csrf']
        return request

    try:
        result={};first=client(0);second=client(1);valid=client(2)
        status,_,_=first('POST','/api/upload',b'print("renamed script")',{'X-Map-Name':'script.py.w3x'})
        result['renamed_script_rejected']=status==400
        status,_,fake=second('POST','/api/upload',b'MPQ\x1a'+b'\0'*256,{'X-Map-Name':'fake.w3x'})
        if status!=202: raise RuntimeError('Fake archive did not reach quarantine test')
        for _ in range(45):
            _,_,state=second('GET','/api/job?id='+fake['id'])
            if state.get('state')=='rejected':break
            time.sleep(1)
        result['fake_mpq_rejected']=state.get('state')=='rejected'
        paths=list((ROOT/'assets/maps').glob('7235147e923f*.w3x'))
        if len(paths)!=1: raise RuntimeError('Echo Isles fixture not found')
        status,_,job=valid('POST','/api/upload',paths[0].read_bytes(),{'X-Map-Name':'EchoIsles.w3x'})
        if status!=202: raise RuntimeError('Valid guest upload failed')
        for _ in range(45):
            _,_,state=valid('GET','/api/job?id='+job['id'])
            if state.get('state') in ('ready','rejected'):break
            time.sleep(1)
        result['valid_map_published']=state.get('state')=='ready' and state.get('code')=='7235147e923f'
        if not all(result.values()): raise RuntimeError('Guest upload protection proof failed')
        statuses=[read_status(ROOT/'status'/worker/'hostmap.status') for worker in WORKERS]
        if not any(fresh(s,int(time.time())) and not s['busy'] for s in statuses):
            raise RuntimeError('No idle worker; existing games must not be interrupted')
        identifier=secrets.token_hex(16);room='Guest Check '+str(int(time.time()))[-6:]
        payload=json.dumps(dict(id=identifier,job=job['id'],room=room)).encode()
        status,_,request=valid('POST','/api/host',payload)
        if status!=202: raise RuntimeError('Guest room request failed')
        # A duplicate click returns the same request, not another allocation.
        status,_,duplicate=valid('POST','/api/host',payload)
        if status!=202 or duplicate['id']!=identifier: raise RuntimeError('Guest request replay changed identity')
        for _ in range(50):
            _,_,request=valid('GET','/api/request?id='+identifier)
            if request.get('state') in ('advertised','failed'):break
            time.sleep(1)
        result['guest_room_advertised']=request.get('state')=='advertised'
        result['room']=room;result['game_worker_restarts']=0
        result['test_room_cleanup']='Left empty for normal ten-minute lobby expiration; never restart a worker to clean it'
        if not result['guest_room_advertised']: raise RuntimeError('Guest room was not advertised: '+request.get('error','unknown'))
        guard();(ROOT/'guest-probe-verified.json').write_text(json.dumps(result,indent=2)+'\n')
        print('GUEST_PRIVATE_END_TO_END_VERIFIED '+json.dumps(result))
    finally:
        server.shutdown();server.server_close();thread.join(2)


if __name__=='__main__': main()
