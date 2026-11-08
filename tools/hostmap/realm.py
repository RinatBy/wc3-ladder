"""Minimal client for the owner's private Warcraft realm, with RSA and SRP proof checks."""
import ctypes as c
import hashlib
import json
import os
from pathlib import Path
import secrets
import socket
import struct
import time

SERVER = '176.124.218.23'
PUBLIC_HASH = '52ea750f9773182b94ea87698959201f284056b296d0fa11fb2ccdd24e1cd7fe'


class Frames:
    def __init__(self):
        self.buffer = bytearray()

    def feed(self, data):
        self.buffer.extend(data)
        result = []
        while len(self.buffer) >= 4:
            size = struct.unpack_from('<H', self.buffer, 2)[0]
            if self.buffer[0] != 255 or size < 4:
                raise ValueError('Invalid realm frame')
            if len(self.buffer) < size:
                break
            result.append((self.buffer[1], bytes(self.buffer[4:size])))
            del self.buffer[:size]
        return result


def chat_event(body):
    if len(body) < 26:
        return None
    parts = body[24:].split(b'\0', 2)
    if len(parts) < 3:
        return None
    return struct.unpack_from('<I', body)[0], parts[0].decode('utf-8', 'replace'), parts[1].decode('utf-8', 'replace')


def library():
    lib = c.CDLL('/opt/ghost/lib/libbncsutil.so')
    signatures = dict(nls_init=([c.c_char_p,c.c_char_p],c.c_void_p),
        nls_free=([c.c_void_p],None), nls_get_A=([c.c_void_p,c.c_void_p],None),
        nls_get_v=([c.c_void_p,c.c_void_p,c.c_char_p],None),
        nls_get_M1=([c.c_void_p,c.c_void_p,c.c_char_p,c.c_char_p],None),
        nls_check_M2=([c.c_void_p,c.c_char_p,c.c_char_p,c.c_char_p],c.c_int))
    for name, (args, result) in signatures.items():
        getattr(lib,name).argtypes = args
        getattr(lib,name).restype = result
    return lib


class Realm:
    def __init__(self, credentials, public_path='/assets/realm-public-modulus.bin'):
        self.credentials = credentials
        self.public_path = Path(public_path)
        self.socket = None
        self.frames = Frames()
        self.pending = []

    def close(self):
        if self.socket:
            self.socket.close()
            self.socket = None

    def send(self, kind, body=b''):
        self.socket.sendall(bytes([255,kind])+struct.pack('<H',len(body)+4)+body)

    def receive(self):
        while not self.pending:
            data = self.socket.recv(8192)
            if not data:
                raise ConnectionError('Realm connection closed')
            self.pending.extend(self.frames.feed(data))
        return self.pending.pop(0)

    def wait(self, wanted):
        deadline = time.monotonic()+20
        while time.monotonic() < deadline:
            kind, body = self.receive()
            if kind == 0x25:
                self.send(kind, body)
            elif kind == wanted:
                return body
        raise TimeoutError('Realm login timeout')

    def connect(self, create=False):
        self.close()
        self.frames = Frames()
        self.pending = []
        self.socket = socket.create_connection((SERVER,6112),8)
        self.socket.sendall(b'\x01')
        self.send(0x50, struct.pack('<9I',0,0x49583836,0x57335850,29,0,0,0,1033,1033)+b'USA\0United States\0')
        challenge = self.wait(0x50)
        first = challenge.index(0,20)
        second = challenge.index(0,first+1)
        signature = challenge[second+1:]
        public = self.public_path.read_bytes()
        if hashlib.sha256(public).hexdigest() != PUBLIC_HASH or len(signature) != 128:
            raise ValueError('Wrong realm identity')
        decoded = pow(int.from_bytes(signature,'little'),65537,int.from_bytes(public,'little')).to_bytes(128,'little')
        if decoded != socket.inet_aton(SERVER)+b'\xbb'*123+b'\x0b':
            raise ValueError('Realm signature mismatch')
        self.send(0x51,struct.pack('<5I',secrets.randbits(32),0x011d020f,0xfeed2881,0,0)+b'Private realm HostMap\0HostMap\0')
        if struct.unpack_from('<I',self.wait(0x51))[0] != 0:
            raise ValueError('Bot revision rejected')
        lib = library()
        user = self.credentials['account'].encode('ascii')
        nls = lib.nls_init(user,self.credentials['password'].encode('ascii'))
        if not nls:
            raise RuntimeError('NLS initialization failed')
        try:
            if create:
                salt = secrets.token_bytes(32)
                verifier = c.create_string_buffer(32)
                lib.nls_get_v(nls,verifier,salt)
                self.send(0x52,salt+verifier.raw+user+b'\0')
                if struct.unpack_from('<I',self.wait(0x52))[0] != 0:
                    raise ValueError('Account already exists; never resetting another account')
                return
            key = c.create_string_buffer(32)
            lib.nls_get_A(nls,key)
            self.send(0x53,key.raw+user+b'\0')
            reply = self.wait(0x53)
            if len(reply) != 68 or struct.unpack_from('<I',reply)[0] != 0:
                raise ValueError('Bot login rejected')
            salt, server_key = reply[4:36],reply[36:68]
            proof = c.create_string_buffer(20)
            lib.nls_get_M1(nls,proof,server_key,salt)
            self.send(0x54,proof.raw)
            reply = self.wait(0x54)
            if len(reply) < 24 or struct.unpack_from('<I',reply)[0] not in (0,14):
                raise ValueError('Bot password rejected')
            if not lib.nls_check_M2(nls,reply[4:24],server_key,salt):
                raise ValueError('Server password proof rejected')
        finally:
            lib.nls_free(nls)
        self.send(0x0a,b'\0\0')
        self.wait(0x0a)
        self.send(0x0c,struct.pack('<I',2)+b'Warcraft 3 Frozen Throne\0')
        self.socket.settimeout(1)

    def whisper(self, target, message):
        from core import account
        account(target)
        if any(c in message for c in '\r\n\0'):
            raise ValueError('Invalid chat text')
        body = f'/w {target} {message}'.encode('utf-8')
        if len(body) > 240:
            raise ValueError('Chat text too long')
        self.send(0x0e,body+b'\0')
