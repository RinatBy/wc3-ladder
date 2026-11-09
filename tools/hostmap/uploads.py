"""Bounded HTTPS-facing receiver: writes quarantine only, never parses native map data."""
import hashlib
import http.server
import json
import os
from pathlib import Path
import re
import secrets
import socketserver
import socket
import threading
import time
from urllib.parse import unquote, urlsplit, parse_qs
from core import Rejected, Store

MAX_BYTES = 32*1024*1024


def receive(store, token, filename, size, stream, incoming, now=None):
    if (not isinstance(size,int) or not 4 <= size <= MAX_BYTES or len(filename) > 120 or
        '/' in filename or '\\' in filename or any(not c.isprintable() for c in filename) or
        not filename.lower().endswith(('.w3x','.w3m'))):
        raise Rejected('Choose a .w3x or .w3m file, up to 32 MiB.')
    owner = store.claim_upload(token,now=now)
    root = Path(incoming)
    if root.is_symlink() or not root.is_dir():
        raise Rejected('Upload directory unavailable.')
    job = secrets.token_hex(16)
    # Reserve bytes in the same write transaction as the quota check, before streaming.
    with store.db() as db:
        db.execute('BEGIN IMMEDIATE')
        usage = db.execute("SELECT coalesce(sum(bytes),0) FROM jobs WHERE state!='rejected'").fetchone()[0]
        if usage+size > 1024*1024*1024:
            raise Rejected('Map storage is full. Contact the administrator.')
        db.execute('INSERT INTO jobs (id,owner,digest,ext,title,bytes,state,created) VALUES (?,?,?,?,?,?,?,?)',
            (job,owner,'',filename[-3:].lower(),filename,size,'receiving',int(time.time()) if now is None else now))
    path = root/(job+'.upload')
    digest = hashlib.sha256()
    try:
        with path.open('xb') as file:
            left = size
            while left:
                block = stream.read(min(left,65536))
                if not block:
                    raise Rejected('Incomplete upload. Request a new link and retry.')
                if left == size and not block.startswith((b'HM3W',b'MPQ\x1a')):
                    raise Rejected('This is not a Warcraft map archive.')
                file.write(block)
                digest.update(block)
                left -= len(block)
            file.flush()
            os.fsync(file.fileno())
        with store.db() as db:
            db.execute("UPDATE jobs SET digest=?,state='pending' WHERE id=?",(digest.hexdigest(),job))
    except BaseException:
        path.unlink(missing_ok=True)
        with store.db() as db:
            db.execute("UPDATE jobs SET state='rejected' WHERE id=?",(job,))
        raise
    return job


def job_status(store, job):
    if not re.fullmatch('[a-f0-9]{32}',job):
        raise Rejected('Invalid request.')
    with store.db() as db:
        row = db.execute('SELECT state,code FROM jobs WHERE id=?',(job,)).fetchone()
    if row is None:
        raise Rejected('Request not found.')
    return dict(row)


PAGE = '''<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>HostMap вЂ” Р·Р°РіСЂСѓР·РєР° РєР°СЂС‚С‹</title><style>body{background:#111;color:#ddd;font:18px Arial;max-width:650px;margin:60px auto;padding:20px}h1{color:#e5c66c}button,input{font:inherit;margin:15px 0}button{padding:12px}a{color:#e5c66c}</style>
<h1>HostMap</h1><p>Р’С‹Р±РµСЂРёС‚Рµ РєР°СЂС‚Сѓ Warcraft III 1.29.2: .w3x РёР»Рё .w3m, РґРѕ 32 РњР‘.</p>
<input id="file" type="file" accept=".w3x,.w3m"><br><button id="send">Р—Р°РіСЂСѓР·РёС‚СЊ РєР°СЂС‚Сѓ</button>
<p id="status">РћС‚РєСЂРѕР№С‚Рµ Р»РёС‡РЅСѓСЋ СЃСЃС‹Р»РєСѓ, РєРѕС‚РѕСЂСѓСЋ РІС‹РґР°Р» HostMap РєРѕРјР°РЅРґРѕР№ !upload.</p>
<script src="/upload.js"></script></html>'''
JS = '''let token=location.hash.slice(1);history.replaceState(null,'','/');
const status=document.getElementById('status'),button=document.getElementById('send');
if(token)status.textContent='РЎСЃС‹Р»РєР° РґРµР№СЃС‚РІСѓРµС‚ 15 РјРёРЅСѓС‚ Рё РїРѕРґС…РѕРґРёС‚ РґР»СЏ РѕРґРЅРѕР№ Р·Р°РіСЂСѓР·РєРё.';
button.onclick=async()=>{let f=document.getElementById('file').files[0];if(!f||!token)return;
button.disabled=true;status.textContent='РљР°СЂС‚Р° Р·Р°РіСЂСѓР¶Р°РµС‚СЃСЏвЂ¦';try{
let r=await fetch('/upload',{method:'POST',headers:{'Authorization':'Bearer '+token,'X-Map-Name':encodeURIComponent(f.name),'Content-Type':'application/octet-stream'},body:f});
token='';let j=await r.json();if(!r.ok)throw Error(j.error||'РћС€РёР±РєР° Р·Р°РіСЂСѓР·РєРё');
status.textContent='РљР°СЂС‚Р° РїРѕР»СѓС‡РµРЅР°. РџСЂРѕРІРµСЂСЏРµРј СЃРѕРІРјРµСЃС‚РёРјРѕСЃС‚СЊвЂ¦';
for(let i=0;i<120;i++){await new Promise(r=>setTimeout(r,1000));let s=await(await fetch('/status?id='+j.id)).json();
if(s.state==='ready'){status.textContent='Р“РѕС‚РѕРІРѕ! Р’ С‡Р°С‚Рµ Warcraft РЅР°РїРёС€РёС‚Рµ: /w HostMap !host '+s.code+' My game';return;}
if(s.state==='rejected')throw Error('РљР°СЂС‚Р° РЅРµ РїСЂРѕС€Р»Р° РїСЂРѕРІРµСЂРєСѓ. Р¤Р°Р№Р» РЅРµ РґРѕР±Р°РІР»РµРЅ.');}
status.textContent='РџСЂРѕРІРµСЂРєР° РїСЂРѕРґРѕР»Р¶Р°РµС‚СЃСЏ. РќР°Р№РґРёС‚Рµ РєР°СЂС‚Сѓ РїРѕР·Р¶Рµ РєРѕРјР°РЅРґРѕР№ !maps.';
}catch(e){status.textContent=e.message+' Р”Р»СЏ РїРѕРІС‚РѕСЂРЅРѕР№ РїРѕРїС‹С‚РєРё РїРѕР»СѓС‡РёС‚Рµ РЅРѕРІСѓСЋ СЃСЃС‹Р»РєСѓ С‡РµСЂРµР· !upload.';}};'''


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self,*args):
        pass # No URL, header or token logging.

    def reply(self,code,body,kind='application/json; charset=utf-8'):
        if isinstance(body,dict):
            body=json.dumps(body,ensure_ascii=False).encode('utf-8')
        elif isinstance(body,str):
            body=body.encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type',kind)
        self.send_header('Content-Length',str(len(body)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Referrer-Policy','no-referrer')
        self.send_header('Content-Security-Policy',"default-src 'none'; script-src 'self'; style-src 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        url=urlsplit(self.path)
        try:
            if url.path=='/': self.reply(200,PAGE,'text/html; charset=utf-8')
            elif url.path=='/upload.js': self.reply(200,JS,'text/javascript; charset=utf-8')
            elif url.path=='/status': self.reply(200,job_status(self.server.store,parse_qs(url.query).get('id',[''])[0]))
            else: self.reply(404,{'error':'Not found'})
        except Rejected as error:
            self.reply(404,{'error':str(error)})

    def do_POST(self):
        self.connection.settimeout(60)
        try:
            if self.path!='/upload' or self.headers.get('Transfer-Encoding'):
                raise Rejected('Invalid request.')
            auth=self.headers.get('Authorization','')
            if not auth.startswith('Bearer '): raise Rejected('Open the personal upload link.')
            job=receive(self.server.store,auth[7:],unquote(self.headers.get('X-Map-Name','')),
                int(self.headers.get('Content-Length','0')),self.rfile,'/incoming')
            self.reply(202,{'id':job})
        except (Rejected,ValueError,TimeoutError) as error:
            self.close_connection=True
            self.reply(400,{'error':str(error)})


class Server(socketserver.ThreadingMixIn,http.server.HTTPServer):
    daemon_threads=True
    request_queue_size=8
    max_connection_seconds=180
    def __init__(self,*args,**kwargs):
        self.slots=threading.BoundedSemaphore(2)
        super().__init__(*args,**kwargs)
    def process_request(self,request,address):
        if not self.slots.acquire(blocking=False):
            request.close();return
        request.settimeout(60)
        super().process_request(request,address)
    def process_request_thread(self,request,address):
        def expire():
            try: request.shutdown(socket.SHUT_RDWR)
            except OSError: pass
            request.close()
        deadline=threading.Timer(self.max_connection_seconds,expire)
        deadline.daemon=True
        deadline.start()
        try: super().process_request_thread(request,address)
        finally:
            deadline.cancel()
            self.slots.release()


if __name__=='__main__':
    os.umask(0o007)
    server=Server(('127.0.0.1',6129),Handler)
    server.store=Store('/data/hostmap.db',['HostMap1','HostMap2'])
    server.serve_forever()
