"""Opaque browser ownership and bounded, at-most-once requests. No realm credentials here."""
import hashlib
import hmac
import ipaddress
import os
import re
import secrets
import socket
import struct
import time
from core import Rejected, fresh, room_name


def clock(now): return int(time.time()) if now is None else now
def digest(value): return hashlib.sha256(value.encode('ascii')).hexdigest()


class Guest:
    def __init__(self, store, secret=None):
        self.store = store
        if secret is None:
            path=store.path.with_suffix('.guest-key')
            if path.is_symlink(): raise RuntimeError('Unexpected guest key path')
            try:
                with path.open('xb') as stream:
                    stream.write(secrets.token_bytes(32)); stream.flush(); os.fsync(stream.fileno())
                path.chmod(0o660)
            except FileExistsError: pass
            secret=path.read_bytes()
        if len(secret)!=32: raise RuntimeError('Invalid guest key')
        self.secret=secret
        with store.db() as db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS guest_sessions (id TEXT PRIMARY KEY, ip TEXT, created INTEGER);
            CREATE TABLE IF NOT EXISTS guest_events (kind TEXT, session TEXT, ip TEXT, created INTEGER);
            CREATE INDEX IF NOT EXISTS guest_event_time ON guest_events(created);
            CREATE TABLE IF NOT EXISTS guest_requests (
                id TEXT PRIMARY KEY, session TEXT, ip TEXT, job TEXT, code TEXT, room TEXT,
                created INTEGER, state TEXT, worker TEXT DEFAULT '', dispatched INTEGER DEFAULT 0,
                error TEXT DEFAULT '');
            CREATE INDEX IF NOT EXISTS guest_request_session ON guest_requests(session);
            CREATE TABLE IF NOT EXISTS guest_choices (session TEXT PRIMARY KEY, code TEXT);
            ''')

    def ip(self, value):
        address=str(ipaddress.ip_address(value))
        return hmac.new(self.secret,('ip:'+address).encode(),hashlib.sha256).hexdigest()

    def csrf(self, token):
        return hmac.new(self.secret,('csrf:'+token).encode(),hashlib.sha256).hexdigest()

    def _auth(self, db, token, now):
        if not isinstance(token,str) or not re.fullmatch('[A-Za-z0-9_-]{43}',token):
            raise Rejected('session_expired')
        sid=digest(token)
        if not db.execute('SELECT 1 FROM guest_sessions WHERE id=? AND created>?',(sid,now-86400)).fetchone():
            raise Rejected('session_expired')
        return sid

    def session(self, token, ip, now=None):
        now=clock(now); ip=self.ip(ip)
        with self.store.db() as db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('DELETE FROM guest_events WHERE created<?',(now-86400,))
            db.execute('DELETE FROM guest_sessions WHERE created<=?',(now-86400,))
            db.execute('DELETE FROM guest_choices WHERE session NOT IN (SELECT id FROM guest_sessions)')
            db.execute('DELETE FROM uploads WHERE expires<?',(now-86400,))
            db.execute("DELETE FROM jobs WHERE owner LIKE 'guest:%' AND state='rejected' AND created<?",(now-86400,))
            db.execute("DELETE FROM guest_requests WHERE created<? AND state IN ('failed','ended')",(now-86400,))
            try: self._auth(db,token,now)
            except Rejected:
                if (db.execute('SELECT count(*) FROM guest_sessions').fetchone()[0]>=2048 or
                    db.execute('SELECT count(*) FROM guest_sessions WHERE ip=?',(ip,)).fetchone()[0]>=20):
                    raise Rejected('session_limit')
                token=secrets.token_urlsafe(32)
                db.execute('INSERT INTO guest_sessions VALUES (?,?,?)',(digest(token),ip,now))
        return token,dict(csrf=self.csrf(token),**self.state(token,now=now))

    def _limit(self, db, kind, sid, ip, now, maximum, interval):
        rows=db.execute('SELECT created FROM guest_events WHERE kind=? AND created>? AND (session=? OR ip=?)',
                        (kind,now-86400,sid,ip)).fetchall()
        if len(rows)>=maximum or any(now-r[0]<interval for r in rows): raise Rejected('rate_limit')
        if db.execute('SELECT count(*) FROM guest_events').fetchone()[0]>=20000: raise Rejected('service_busy')
        db.execute('INSERT INTO guest_events VALUES (?,?,?,?)',(kind,sid,ip,now))

    def upload_ticket(self, token, ip, now=None):
        now=clock(now); ip=self.ip(ip)
        with self.store.db() as db:
            db.execute('BEGIN IMMEDIATE'); sid=self._auth(db,token,now); owner='guest:'+sid
            if (db.execute("SELECT 1 FROM jobs WHERE owner=? AND state IN ('receiving','pending')",(owner,)).fetchone() or
                db.execute('SELECT 1 FROM uploads WHERE owner=? AND used=0 AND expires>=?',(owner,now)).fetchone()):
                raise Rejected('upload_pending')
            self._limit(db,'upload',sid,ip,now,5,60)
            db.execute('DELETE FROM guest_choices WHERE session=?',(sid,))
            ticket=secrets.token_urlsafe(32)
            db.execute('INSERT INTO uploads VALUES (?,?,?,?,0)',(digest(ticket),owner,now,now+120))
        return ticket

    def job(self, token, job, now=None):
        with self.store.db() as db:
            sid=self._auth(db,token,clock(now))
            row=db.execute('SELECT id,state,code,title FROM jobs WHERE id=? AND owner=?',(job,'guest:'+sid)).fetchone()
            if not row: raise Rejected('not_found')
            return dict(row)

    def request(self, token, identifier, now=None):
        with self.store.db() as db:
            sid=self._auth(db,token,clock(now))
            row=db.execute('SELECT id,state,room,error FROM guest_requests WHERE id=? AND session=?',(identifier,sid)).fetchone()
            if not row: raise Rejected('not_found')
            return dict(row)

    def state(self, token, now=None):
        with self.store.db() as db:
            sid=self._auth(db,token,clock(now))
            job=db.execute('SELECT id,state,code,title FROM jobs WHERE owner=? ORDER BY rowid DESC LIMIT 1',('guest:'+sid,)).fetchone()
            chosen=db.execute('SELECT m.code,m.title FROM guest_choices c JOIN maps m ON m.code=c.code WHERE c.session=?',(sid,)).fetchone()
            if chosen: job=dict(id='map:'+chosen['code'],state='ready',code=chosen['code'],title=chosen['title'])
            request=db.execute('SELECT id,state,room,error FROM guest_requests WHERE session=? ORDER BY rowid DESC LIMIT 1',(sid,)).fetchone()
            return dict(job=dict(job) if job else None,request=dict(request) if request else None)

    def catalog(self, token, query='', digest='', now=None):
        if not isinstance(query,str) or len(query)>60 or (digest and not re.fullmatch('[a-f0-9]{64}',digest)):
            raise Rejected('invalid_request')
        with self.store.db() as db:
            self._auth(db,token,clock(now))
            rows=db.execute('SELECT code,title,ext,digest FROM maps WHERE instr(lower(title),lower(?))>0 AND (?=\'\' OR digest=?) ORDER BY title COLLATE NOCASE,code LIMIT 101',(query,digest,digest)).fetchall()
            return dict(maps=[dict(r) for r in rows[:100]],more=len(rows)>100)

    def select(self, token, code, now=None):
        now=clock(now)
        if not isinstance(code,str) or not re.fullmatch('[a-f0-9]{12}',code): raise Rejected('map_not_ready')
        with self.store.db() as db:
            db.execute('BEGIN IMMEDIATE');sid=self._auth(db,token,now)
            if not db.execute('SELECT 1 FROM maps WHERE code=?',(code,)).fetchone(): raise Rejected('map_not_ready')
            if db.execute("SELECT 1 FROM jobs WHERE owner=? AND state IN ('receiving','pending')",('guest:'+sid,)).fetchone(): raise Rejected('upload_pending')
            db.execute('INSERT OR REPLACE INTO guest_choices VALUES (?,?)',(sid,code))
        return self.state(token,now=now)

    def create(self, token, identifier, job, room, ip, now=None):
        now=clock(now); ip=self.ip(ip); room_name(room)
        if not re.fullmatch('[a-f0-9]{32}',identifier): raise Rejected('invalid_request')
        with self.store.db() as db:
            db.execute('BEGIN IMMEDIATE'); sid=self._auth(db,token,now)
            existing=db.execute('SELECT * FROM guest_requests WHERE id=?',(identifier,)).fetchone()
            if existing:
                if existing['session']!=sid or existing['job']!=job or existing['room']!=room: raise Rejected('not_found')
                return dict(id=existing['id'],state=existing['state'],room=existing['room'],error=existing['error'])
            if isinstance(job,str) and re.fullmatch('map:[a-f0-9]{12}',job):
                item=db.execute('SELECT code FROM maps WHERE code=?',(job[4:],)).fetchone()
            else:
                item=db.execute("SELECT code FROM jobs WHERE id=? AND owner=? AND state='ready'",(job,'guest:'+sid)).fetchone()
            if not item: raise Rejected('map_not_ready')
            if (db.execute("SELECT 1 FROM guest_requests WHERE session=? AND state IN ('queued','dispatched')",(sid,)).fetchone() or
                db.execute('SELECT 1 FROM leases WHERE owner=? AND (active=1 OR created>?)',('guest:'+sid,now-60)).fetchone()):
                raise Rejected('already_hosting')
            active=db.execute("SELECT count(DISTINCT r.session) FROM guest_requests r WHERE r.ip=? AND (r.state IN ('queued','dispatched') OR EXISTS(SELECT 1 FROM leases l WHERE l.owner='guest:'||r.session))",(ip,)).fetchone()[0]
            if active>=2: raise Rejected('ip_rooms_full')
            if db.execute("SELECT count(*) FROM guest_requests WHERE state IN ('queued','dispatched')").fetchone()[0]>=128: raise Rejected('service_busy')
            self._limit(db,'host',sid,ip,now,20,5)
            db.execute('INSERT INTO guest_requests (id,session,ip,job,code,room,created,state) VALUES (?,?,?,?,?,?,?,?)',
                       (identifier,sid,ip,job,item['code'],room,now,'queued'))
        return dict(id=identifier,state='queued',room=room,error='')

    def dispatch(self, statuses, now=None):
        now=clock(now)
        with self.store.db() as db:
            db.execute('BEGIN IMMEDIATE'); self.store._reconcile(db,statuses,now)
            db.execute("UPDATE guest_requests SET state='ended' WHERE state='advertised' AND NOT EXISTS(SELECT 1 FROM leases l WHERE l.owner='guest:'||guest_requests.session)")
            db.execute("UPDATE guest_requests SET state='failed',error='confirmation_timeout' WHERE state='dispatched' AND dispatched<?",(now-45,))
            row=db.execute("SELECT * FROM guest_requests WHERE state='queued' ORDER BY created,rowid LIMIT 1").fetchone()
            if not row: return None
            if row['created']<now-30:
                db.execute("UPDATE guest_requests SET state='failed',error='controller_unavailable' WHERE id=?",(row['id'],));return None
            try:
                lease=self.store._reserve(db,'guest:'+row['session'],row['code'],row['room'],statuses,now,'HostMap')
            except Rejected as error:
                message='rooms_busy' if str(error).startswith('All rooms are busy') else 'room_unavailable'
                db.execute("UPDATE guest_requests SET state='failed',error=? WHERE id=?",(message,row['id']));return None
            db.execute("UPDATE guest_requests SET state='dispatched',worker=?,dispatched=? WHERE id=?",(lease['worker'],now,row['id']))
            return dict(id=row['id'],**lease)

    def waiting(self):
        with self.store.db() as db:
            row=db.execute("SELECT room FROM guest_requests WHERE state='dispatched' ORDER BY dispatched LIMIT 1").fetchone()
            return row['room'] if row else None

    def confirm(self, body, statuses, now=None):
        now=clock(now)
        if len(body)<38 or struct.unpack_from('<I',body)[0]<1: return False
        try:
            port=struct.unpack_from('>H',body,14)[0]; ip=socket.inet_ntoa(body[16:20])
            # Warcraft response includes a full sockaddr, game status and elapsed time.
            room=body[36:body.index(0,36)].decode('ascii')
        except (ValueError,UnicodeError): return False
        if ip!='176.124.218.23': return False
        worker={6117:'HostMap1',6118:'HostMap2'}.get(port)
        if not worker or not fresh(statuses.get(worker),now) or not statuses[worker]['busy']: return False
        with self.store.db() as db:
            changed=db.execute("UPDATE guest_requests SET state='advertised' WHERE state='dispatched' AND room=? AND worker=?",(room,worker)).rowcount
            return bool(changed)
