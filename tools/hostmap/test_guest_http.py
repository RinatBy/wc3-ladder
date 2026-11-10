import importlib.util
import http.client
import http.server
import json
from pathlib import Path
import tempfile
import threading
import socket
import time
import unittest
import core
import uploads


class HttpTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('guest_http'),'Guest HTTP flow has not been implemented')
        from guest import Guest
        from guest_http import GuestHandler
        import guest_http
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        root=Path(self.tmp.name); (root/'incoming').mkdir()
        self.server=getattr(guest_http,'GuestServer',uploads.Server)(('127.0.0.1',0),GuestHandler)
        self.server.store=core.Store(root/'state.db',['HostMap1','HostMap2'])
        self.server.guest=Guest(self.server.store,secret=b'x'*32)
        self.server.incoming=root/'incoming'; self.server.trust_proxy=False; self.server.enabled=True
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True); self.thread.start()
        self.addCleanup(self.stop)

    def stop(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join(2)

    def request(self, method, path, data=b'', headers=None):
        client=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=3)
        try:
            client.request(method,path,body=data,headers={'Origin':'https://maps.wc3.uplay2.ru','Host':'maps.wc3.uplay2.ru',**(headers or {})})
            response=client.getresponse(); return response.status,dict(response.getheaders()),response.read()
        finally: client.close()

    def session(self):
        status,headers,data=self.request('POST','/api/session')
        self.assertEqual(status,200)
        cookie=headers['Set-Cookie']; self.assertIn('HttpOnly',cookie); self.assertIn('Secure',cookie)
        return cookie.split(';')[0],json.loads(data)['csrf']

    def test_origin_csrf_and_foreign_session_blocked(self):
        self.assertEqual(self.request('POST','/api/session',headers={'Origin':'https://evil.example'})[0],403)
        cookie,csrf=self.session()
        self.assertEqual(self.request('POST','/api/upload',b'MPQ\x1atest',{'Cookie':cookie,'X-Map-Name':'x.w3x'})[0],403)
        status,_,data=self.request('POST','/api/upload',b'HM3Wtest',{'Cookie':cookie,'X-CSRF-Token':csrf,'X-Map-Name':'x.w3x'})
        self.assertEqual(status,202)
        job=json.loads(data)['id']; other,_=self.session()
        self.assertEqual(self.request('GET','/api/job?id='+job,headers={'Cookie':other})[0],400)

    def test_catalog_selection_requires_session_csrf_and_validated_identity(self):
        self.assertEqual(self.request('GET','/api/maps')[0],400)
        cookie,csrf=self.session()
        code=self.server.store.add_map('a'*64,'w3x','Spec Arena')
        status,_,body=self.request('GET','/api/maps?q=Arena',headers={'Cookie':cookie})
        self.assertEqual(status,200);self.assertEqual(json.loads(body)['maps'][0]['code'],code)
        payload=json.dumps(dict(code=code)).encode()
        self.assertEqual(self.request('POST','/api/select',payload,{'Cookie':cookie})[0],403)
        status,_,body=self.request('POST','/api/select',payload,{'Cookie':cookie,'X-CSRF-Token':csrf})
        self.assertEqual(status,200);self.assertEqual(json.loads(body)['job']['id'],'map:'+code)
        invalid=json.dumps(dict(code='../../etc/passwd')).encode()
        self.assertEqual(self.request('POST','/api/select',invalid,{'Cookie':cookie,'X-CSRF-Token':csrf})[0],400)

    def test_fake_proxy_header_does_not_change_local_address(self):
        for index in range(20):
            status,_,_=self.request('POST','/api/session',headers={'X-Real-IP':'192.0.2.'+str(index+1)})
            self.assertEqual(status,200)
        self.assertEqual(self.request('POST','/api/session',headers={'X-Real-IP':'198.51.100.1'})[0],400)

    def test_guest_cannot_inject_owner_and_ip_host_redirects(self):
        cookie,csrf=self.session()
        body=json.dumps(dict(id='a'*32,job='b'*32,room='Room',owner='uPlay')).encode()
        self.assertEqual(self.request('POST','/api/host',body,{'Cookie':cookie,'X-CSRF-Token':csrf})[0],400)
        self.assertEqual(self.request('GET','/',headers={'Host':'176.124.218.23'})[0],308)

    def test_publication_can_be_revoked_without_restart(self):
        enabled=[True];self.server.enabled=lambda:enabled[0]
        self.session();enabled[0]=False
        self.assertEqual(self.request('POST','/api/session')[0],400)

    def test_incomplete_small_control_body_has_total_deadline(self):
        cookie,csrf=self.session();self.server.control_seconds=0.2
        slow=socket.create_connection(self.server.server_address,timeout=1)
        self.addCleanup(slow.close)
        headers=f'POST /api/host HTTP/1.0\r\nHost: maps.wc3.uplay2.ru\r\nOrigin: https://maps.wc3.uplay2.ru\r\nCookie: {cookie}\r\nX-CSRF-Token: {csrf}\r\nContent-Length: 1000\r\n\r\n{{'
        slow.sendall(headers.encode())
        try: data=slow.recv(100)
        except socket.timeout: data=None
        self.assertEqual(data,b'', 'Incomplete control body must release the handler promptly')
        self.assertEqual(self.request('POST','/api/session')[0],200)

    def test_status_and_session_remain_available_during_two_uploads(self):
        sockets=[]
        self.server.trust_proxy=True
        try:
            for index in range(2):
                ip='192.0.2.'+str(index+1)
                status,headers,state=self.request('POST','/api/session',headers={'X-Real-IP':ip})
                self.assertEqual(status,200)
                cookie=headers['Set-Cookie'].split(';')[0];csrf=json.loads(state)['csrf']
                connection=socket.create_connection(self.server.server_address,timeout=2);sockets.append(connection)
                header=f'POST /api/upload HTTP/1.0\r\nHost: maps.wc3.uplay2.ru\r\nOrigin: https://maps.wc3.uplay2.ru\r\nCookie: {cookie}\r\nX-CSRF-Token: {csrf}\r\nX-Real-IP: {ip}\r\nX-Map-Name: test.w3x\r\nContent-Length: 100\r\n\r\nHM3W'
                connection.sendall(header.encode())
            time.sleep(0.1)
            try: status=self.request('POST','/api/session',headers={'X-Real-IP':'192.0.2.19'})[0]
            except (OSError,http.client.HTTPException): status=None
            self.assertEqual(status,200,'Two map streams must not block the control interface')
        finally:
            for connection in sockets: connection.close()


if __name__=='__main__': unittest.main()
