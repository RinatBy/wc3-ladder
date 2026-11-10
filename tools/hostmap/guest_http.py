"""Same-origin guest website. Loopback listener only; no realm or Docker access."""
from http.cookies import SimpleCookie, CookieError
import ipaddress
import json
from pathlib import Path
import secrets
import socket
import threading
from urllib.parse import parse_qs, unquote, urlsplit
import uploads
from core import Rejected, Store
from guest import Guest

ORIGIN='https://maps.wc3.uplay2.ru'
COOKIE='__Host-hostmap'
WEB=Path(__file__).with_name('web')


class GuestServer(uploads.Server):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.slots=threading.BoundedSemaphore(8)
        self.upload_slots=threading.BoundedSemaphore(2)


class GuestHandler(uploads.Handler):
    def reply(self,*args,**kwargs):
        try: return super().reply(*args,**kwargs)
        except OSError: self.close_connection=True

    def origin(self): return getattr(self.server,'origin',ORIGIN)

    def token(self):
        try:
            cookie=SimpleCookie(self.headers.get('Cookie',''))
            return cookie[getattr(self.server,'cookie_name',COOKIE)].value
        except (KeyError,ValueError,CookieError): return None

    def client_ip(self):
        address=ipaddress.ip_address(self.client_address[0])
        if self.server.trust_proxy:
            if not address.is_loopback: raise Rejected('invalid_proxy')
            address=ipaddress.ip_address(self.headers.get('X-Real-IP',''))
        return str(address)

    def gate(self, mutate=False):
        enabled=self.server.enabled
        if not (enabled() if callable(enabled) else enabled): raise Rejected('temporarily_unavailable')
        if mutate and self.headers.get('Origin')!=self.origin():
            raise PermissionError('wrong_origin')

    def csrf(self):
        token=self.token()
        if not token or not secrets.compare_digest(self.headers.get('X-CSRF-Token',''),self.server.guest.csrf(token)):
            raise PermissionError('invalid_csrf')
        return token

    def session_reply(self, token, state):
        data=json.dumps(state,ensure_ascii=False).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type','application/json; charset=utf-8')
        name=getattr(self.server,'cookie_name',COOKIE)
        secure='; Secure' if self.origin().startswith('https:') else ''
        self.send_header('Set-Cookie',f'{name}={token}; Path=/; Max-Age=86400; HttpOnly; SameSite=Strict'+secure)
        self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(data)))
        self.end_headers();self.wfile.write(data)

    def canonical(self):
        if self.headers.get('Host')==urlsplit(self.origin()).netloc: return True
        self.send_response(308);self.send_header('Location',ORIGIN+'/');self.send_header('Content-Length','0');self.end_headers()
        self.close_connection=True;return False

    def do_GET(self):
        if not self.canonical(): return
        url=urlsplit(self.path)
        if url.path=='/': return self.reply(200,(WEB/'index.html').read_bytes(),'text/html; charset=utf-8')
        assets={'/web/app.js':('app.js','text/javascript; charset=utf-8'),'/web/style.css':('style.css','text/css; charset=utf-8'),
                '/web/header.gif':('header.gif','image/gif'),'/web/wood.gif':('wood.gif','image/gif')}
        if url.path in assets:
            name,kind=assets[url.path];return self.reply(200,(WEB/name).read_bytes(),kind)
        if url.path=='/legacy': return self.reply(200,uploads.PAGE,'text/html; charset=utf-8')
        if url.path.startswith('/api/'):
            try:
                self.gate(); token=self.token(); query=parse_qs(url.query)
                if url.path=='/api/state': result=self.server.guest.state(token)
                elif url.path=='/api/job': result=self.server.guest.job(token,query.get('id',[''])[0])
                elif url.path=='/api/request': result=self.server.guest.request(token,query.get('id',[''])[0])
                else: return self.reply(404,dict(error='not_found'))
                return self.reply(200,result)
            except (Rejected,ValueError): return self.reply(400,dict(error='not_found'))
        return super().do_GET()

    def do_POST(self):
        if not self.canonical(): return
        if not self.path.startswith('/api/'):
            if self.path!='/upload': return super().do_POST()
            if not self.server.upload_slots.acquire(blocking=False): return self.reply(429,dict(error='service_busy'))
            try: return super().do_POST()
            finally: self.server.upload_slots.release()
        self.connection.settimeout(60)
        deadline=None; upload_slot=False;expired=threading.Event()
        def expire():
            expired.set()
            try: self.connection.shutdown(socket.SHUT_RDWR)
            except OSError: pass
            self.connection.close()
        try:
            self.gate(mutate=True)
            if self.headers.get('Transfer-Encoding') or len(self.headers.get_all('Content-Length',[]))!=1:
                raise Rejected('invalid_request')
            size=int(self.headers.get('Content-Length','0'))
            if self.path=='/api/session':
                if size!=0: raise Rejected('invalid_request')
                token,state=self.server.guest.session(self.token(),self.client_ip())
                return self.session_reply(token,state)
            token=self.csrf()
            if self.path=='/api/upload':
                name=unquote(self.headers.get('X-Map-Name',''))
                if not 4<=size<=uploads.MAX_BYTES: raise Rejected('invalid_size')
                if not self.server.upload_slots.acquire(blocking=False): raise Rejected('service_busy')
                upload_slot=True
                ticket=self.server.guest.upload_ticket(token,self.client_ip())
                job=uploads.receive(self.server.store,ticket,name,size,self.rfile,self.server.incoming)
                return self.reply(202,dict(id=job))
            if self.path=='/api/host':
                if not 1<=size<=1024: raise Rejected('invalid_request')
                deadline=threading.Timer(getattr(self.server,'control_seconds',5),expire)
                deadline.daemon=True;deadline.start()
                data=json.loads(self.rfile.read(size))
                if not isinstance(data,dict) or set(data)!={'id','job','room'} or not all(isinstance(v,str) for v in data.values()):
                    raise Rejected('invalid_request')
                result=self.server.guest.create(token,data['id'],data['job'],data['room'],self.client_ip())
                return self.reply(202,result)
            return self.reply(404,dict(error='not_found'))
        except PermissionError as error:
            self.close_connection=True
            if not expired.is_set(): self.reply(403,dict(error=str(error)))
        except (Rejected,ValueError,TimeoutError) as error:
            self.close_connection=True
            if not expired.is_set(): self.reply(400,dict(error=str(error)))
        except OSError:
            self.close_connection=True
        finally:
            if deadline: deadline.cancel()
            if upload_slot: self.server.upload_slots.release()


def main():
    import os
    os.umask(0o007)
    server=GuestServer(('127.0.0.1',6129),GuestHandler)
    server.store=Store('/data/hostmap.db',['HostMap1','HostMap2'])
    server.guest=Guest(server.store)
    server.incoming=Path('/incoming');server.trust_proxy=True
    # File is provisioned only after the publication approval; restart is not needed to revoke.
    server.enabled=lambda:Path('/data/guest-enabled').is_file()
    server.serve_forever()


if __name__=='__main__': main()
