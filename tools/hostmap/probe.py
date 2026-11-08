"""End-to-end check through an ordinary, dedicated test account. No user credentials."""
import json
from pathlib import Path
import socket
import struct
import sys
import time
from realm import Realm, chat_event, SERVER


def main():
    code,room=sys.argv[1:3]
    client=Realm(json.loads(Path('/credentials.json').read_text()))
    try:
        client.connect()
        client.whisper('HostMap','!maps Echo')
        end=time.monotonic()+12
        found=False
        while time.monotonic()<end:
            try: kind,body=client.receive()
            except socket.timeout: continue
            if kind==0x25: client.send(kind,body)
            event=chat_event(body) if kind==0x0f else None
            if event and event[0]==4 and event[1].lower()=='hostmap' and code in event[2]:
                found=True;break
        if not found: raise RuntimeError('HostMap did not answer the ordinary account')
        time.sleep(2.1)
        client.whisper('HostMap','!host '+code+' '+room)
        end=time.monotonic()+40
        next_query=time.monotonic()+5
        while time.monotonic()<end:
            if time.monotonic()>=next_query:
                client.send(0x09,struct.pack('<4I',1023,1023,0,1)+room.encode()+b'\0\0\0')
                next_query=time.monotonic()+3
            try: kind,body=client.receive()
            except socket.timeout: continue
            if kind==0x25: client.send(kind,body)
            if kind==0x09 and len(body)>4 and struct.unpack_from('<I',body)[0]>0 and room.encode() in body:
                ports=[p for p in (6117,6118) if struct.pack('>H',p)+socket.inet_aton(SERVER) in body]
                if not ports: raise RuntimeError('Room advertised an unexpected endpoint')
                print(json.dumps(dict(ordinary_account=True,chat_command=True,room=room,
                    realm_advertised=True,address=SERVER,port=ports[0])))
                return
        raise RuntimeError('User command did not produce an advertised room')
    finally:
        client.close()


if __name__=='__main__': main()
