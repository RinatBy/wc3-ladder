"""Loopback-only visual preview using disposable local state, no realm connection."""
import os
from pathlib import Path
import tempfile
from core import Store
from guest import Guest
from guest_http import GuestHandler
from uploads import Server


if __name__=='__main__':
    os.umask(0o007)
    with tempfile.TemporaryDirectory(prefix='hostmap-preview-') as temporary:
        root=Path(temporary); (root/'incoming').mkdir()
        server=Server(('127.0.0.1',8051),GuestHandler)
        server.store=Store(root/'hostmap.db',['HostMap1','HostMap2'])
        server.guest=Guest(server.store,secret=b'preview-only-not-a-live-secret!!')
        server.incoming=root/'incoming'; server.trust_proxy=False;server.enabled=True
        server.origin='http://127.0.0.1:8051';server.cookie_name='hostmap-preview'
        print('HostMap local preview: http://127.0.0.1:8051/',flush=True)
        server.serve_forever()
