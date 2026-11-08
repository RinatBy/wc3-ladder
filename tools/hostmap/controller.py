"""HostMap's public commands; only this account can allocate worker rooms."""
from collections import deque
import json
import os
from pathlib import Path
import socket
import time

from core import Store, Rejected, account, read_status, fresh
from realm import Realm, chat_event


class Commands:
    def __init__(self, store, statuses, upload_url=None):
        self.store, self.statuses = store, statuses
        self.upload_url = upload_url
        if upload_url and upload_url != 'https://maps.wc3.uplay2.ru/':
            raise ValueError('Unexpected upload origin')
        self.last = {}

    def handle(self, user, message, now=None):
        now = int(time.time()) if now is None else now
        if user.lower() in {w.lower() for w in self.store.workers} | {'hostmap'}:
            return []
        if not message.startswith('!') or len(message.encode('utf-8')) > 220:
            return []
        try:
            account(user)
            if now-self.last.get(user.lower(), -10) < 2:
                return []
            self.last = {k:v for k,v in self.last.items() if now-v < 60}
            if len(self.last) > 1000:
                return []
            self.last[user.lower()] = now
            command, _, payload = message.partition(' ')
            command = command.lower()
            if command == '!maps':
                items = self.store.maps(payload.strip())
                if not items:
                    return [(user,'No maps found. To add your map: !upload')]
                return [(user,f'{item["code"]}: {item["title"][:60]}') for item in items[:5]]
            if command == '!host':
                code, _, room = payload.strip().partition(' ')
                lease = self.store.host(user,code,room.strip(),self.statuses(),now=now)
                return [(lease['worker'],lease['command']),
                        (user,f'Creating "{lease["room"]}". Open Custom Games; all players type !go in the lobby.')]
            if command == '!upload':
                if not self.upload_url:
                    raise Rejected('Map upload is not enabled yet. Available maps: !maps')
                token = self.store.issue_upload(user,now=now)
                return [(user,self.upload_url+'#'+token)]
            return [(user,'HostMap: !maps [name] | !host MAP_CODE Room name | !upload. In lobby: !go.')]
        except Rejected as error:
            return [(user,str(error))]


def main():
    os.umask(0o007)
    state = Path('/state')
    config = json.loads(Path('/config/controller.json').read_text())
    workers = config['workers']
    store = Store(state/'hostmap.db',workers)
    def statuses():
        return {w:read_status(Path('/workers')/w/'hostmap.status') for w in workers}
    commands = Commands(store,statuses,config.get('upload_url'))
    credentials = json.loads(Path('/config/credentials.json').read_text())
    if credentials['account'] != 'HostMap':
        raise ValueError('Wrong controller account')
    client = Realm(credentials)
    outbound = deque()
    last_sent = 0
    last_tick = 0
    connected = False
    while True:
        try:
            if not connected:
                client.connect()
                connected = True
                print('HOSTMAP_REALM_AUTHENTICATED',flush=True)
            try:
                kind,body = client.receive()
                if kind == 0x25:
                    client.send(kind,body)
                elif kind == 0x0f:
                    event = chat_event(body)
                    if event and event[0] in (4,5) and len(outbound) < 32:
                        outbound.extend(commands.handle(event[1],event[2]))
            except socket.timeout:
                pass
            now = time.monotonic()
            if outbound and now-last_sent >= 0.6:
                target,text = outbound.popleft()
                while len(text.encode('utf-8')) > 185:
                    text = text[:-1]
                client.whisper(target,text)
                last_sent = now
            if now-last_tick >= 2:
                store.reconcile(statuses())
                tmp = state/'controller.status.tmp'
                tmp.write_text(json.dumps(dict(time=int(time.time()),authenticated=True,
                    workers={w:bool(fresh(s,int(time.time())) and not s['busy']) for w,s in statuses().items()})))
                tmp.replace(state/'controller.status.json')
                last_tick = now
        except (OSError,ValueError,ConnectionError) as error:
            # Never log user commands, capabilities, passwords, or binary handshake packets.
            print('HOSTMAP_RECONNECT',type(error).__name__,flush=True)
            client.close()
            connected = False
            outbound.clear()
            tmp=state/'controller.status.tmp'
            tmp.write_text(json.dumps(dict(time=int(time.time()),authenticated=False,workers={})))
            tmp.replace(state/'controller.status.json')
            time.sleep(5)


if __name__ == '__main__':
    main()
