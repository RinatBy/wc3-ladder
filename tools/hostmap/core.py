"""Persistent allocation and upload capabilities; no network or process privileges."""
import contextlib
import hashlib
from pathlib import Path
import re
import secrets
import sqlite3
import time


class Rejected(ValueError):
    pass


def account(value):
    if not re.fullmatch(r'[A-Za-z0-9_\[\].()-]{1,15}', value):
        raise Rejected('Invalid account name.')
    return value


def room_name(value):
    # Initial protocol deliberately uses plain printable ASCII, never slash commands.
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9 _.,!()\[\]+-]{0,29}', value):
        raise Rejected('Room name: 1-30 Latin letters, digits or spaces.')
    return value


def fresh(status, now):
    return status and isinstance(status.get('time'), int) and -2 <= now-status['time'] <= 8


class Store:
    def __init__(self, path, workers):
        self.path = Path(path)
        self.workers = tuple(account(w) for w in workers)
        with self.db() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS maps (
                    digest TEXT PRIMARY KEY, code TEXT UNIQUE, ext TEXT, title TEXT);
                CREATE TABLE IF NOT EXISTS leases (
                    worker TEXT PRIMARY KEY, owner TEXT UNIQUE COLLATE NOCASE,
                    room TEXT UNIQUE COLLATE NOCASE, created INTEGER, active INTEGER DEFAULT 0);
                CREATE TABLE IF NOT EXISTS uploads (
                    hash TEXT PRIMARY KEY, owner TEXT COLLATE NOCASE,
                    created INTEGER, expires INTEGER, used INTEGER DEFAULT 0);
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY, owner TEXT, digest TEXT, ext TEXT, title TEXT,
                    bytes INTEGER, state TEXT, code TEXT DEFAULT '', created INTEGER DEFAULT 0);
            ''')

    @contextlib.contextmanager
    def db(self):
        with contextlib.closing(sqlite3.connect(self.path, timeout=5)) as db:
            db.row_factory = sqlite3.Row
            with db:
                yield db

    def add_map(self, digest, ext, title):
        if not re.fullmatch('[a-f0-9]{64}', digest) or ext not in ('w3x', 'w3m'):
            raise Rejected('Invalid map identity.')
        title = ''.join(c for c in title if c.isprintable())[:100]
        with self.db() as db:
            existing=db.execute('SELECT digest FROM maps WHERE code=?',(digest[:12],)).fetchone()
            if existing and existing[0]!=digest:
                raise Rejected('Map identifier collision. Contact the administrator.')
            db.execute('INSERT OR IGNORE INTO maps VALUES (?,?,?,?)',
                       (digest, digest[:12], ext, title))
        return digest[:12]

    def maps(self, query=''):
        with self.db() as db:
            # LIKE wildcards intentionally not accepted as a search language.
            return [dict(r) for r in db.execute(
                'SELECT * FROM maps WHERE instr(lower(title),lower(?))>0 ORDER BY title LIMIT 8',
                (query[:60],))]

    def _reconcile(self, db, statuses, now):
        for row in db.execute('SELECT * FROM leases').fetchall():
            status = statuses.get(row['worker'])
            if not fresh(status, now):
                continue
            if status.get('busy'):
                db.execute('UPDATE leases SET active=1 WHERE worker=?', (row['worker'],))
            elif row['active'] or now-row['created'] > 60:
                db.execute('DELETE FROM leases WHERE worker=?', (row['worker'],))

    def reconcile(self, statuses, now=None):
        now = int(time.time()) if now is None else now
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            self._reconcile(db, statuses, now)

    def host(self, owner, code, room, statuses, now=None):
        account(owner)
        now = int(time.time()) if now is None else now
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            return self._reserve(db,owner,code,room,statuses,now,owner)

    def _reserve(self, db, owner, code, room, statuses, now, command_owner):
        # Internal caller may use a guest: namespace; wire owner is always an existing service/account.
        account(command_owner)
        room_name(room)
        if not re.fullmatch('[a-f0-9]{12}', code):
            raise Rejected('Use the map code from !maps.')
        self._reconcile(db, statuses, now)
        item = db.execute('SELECT * FROM maps WHERE code=?', (code,)).fetchone()
        if item is None:
            raise Rejected('Map not found. Use !maps.')
        used = {r[0] for r in db.execute('SELECT worker FROM leases')}
        worker = next((w for w in self.workers if w not in used and
                       fresh(statuses.get(w), now) and not statuses[w].get('busy')), None)
        if not worker:
            raise Rejected('All rooms are busy. Try again after a game finishes.')
        try:
            db.execute('INSERT INTO leases VALUES (?,?,?,?,0)', (worker, owner, room, now))
        except sqlite3.IntegrityError:
            raise Rejected('You already have a room, or this room name is in use.') from None
        return dict(worker=worker, owner=owner, room=room, code=code, created=now,
                    command=f'!hmhost {now} {code} {command_owner} {room}')

    def issue_upload(self, owner, now=None):
        account(owner)
        now = int(time.time()) if now is None else now
        token = secrets.token_urlsafe(32)
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            recent = db.execute('SELECT created FROM uploads WHERE owner=? AND created>?',
                                (owner, now-86400)).fetchall()
            if len(recent) >= 5 or any(now-r[0] < 60 for r in recent):
                raise Rejected('Upload limit reached. Please try later.')
            db.execute('UPDATE uploads SET used=1 WHERE owner=?', (owner,))
            db.execute('INSERT INTO uploads VALUES (?,?,?,?,0)',
                       (hashlib.sha256(token.encode()).hexdigest(), owner, now, now+900))
            db.execute('DELETE FROM uploads WHERE expires<?', (now-86400,))
        return token

    def claim_upload(self, token, now=None):
        if not re.fullmatch('[A-Za-z0-9_-]{43}', token):
            raise Rejected('Invalid upload link.')
        now = int(time.time()) if now is None else now
        digest = hashlib.sha256(token.encode()).hexdigest()
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT * FROM uploads WHERE hash=? AND used=0 AND expires>=?',
                             (digest, now)).fetchone()
            if row is None:
                raise Rejected('Upload link expired or already used. Request !upload again.')
            db.execute('UPDATE uploads SET used=1 WHERE hash=?', (digest,))
            return row['owner']


def read_status(path):
    try:
        fields = Path(path).read_text(encoding='ascii').strip().split('\t')
        return dict(time=int(fields[0]), busy=int(fields[1]) > 0)
    except (OSError, ValueError, IndexError):
        return None
