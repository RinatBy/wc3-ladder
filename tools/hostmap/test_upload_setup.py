import json
from pathlib import Path
import tempfile
import unittest
import http.server
import threading
from enable_uploads import certificate_command, set_upload_url, write_owned, wait_http


class SetupTests(unittest.TestCase):
    def test_probe_waits_for_graceful_nginx_reload(self):
        class Endpoint(http.server.BaseHTTPRequestHandler):
            calls=0
            def do_GET(self):
                Endpoint.calls+=1
                self.send_response(404 if Endpoint.calls==1 else 200)
                self.end_headers();self.wfile.write(b'ready')
            def log_message(self,*args): pass
        server=http.server.HTTPServer(('127.0.0.1',0),Endpoint)
        worker=threading.Thread(target=lambda:server.serve_forever(poll_interval=0.01),daemon=True)
        worker.start()
        try:
            wait_http('http://127.0.0.1:'+str(server.server_port)+'/',b'ready',seconds=2)
            self.assertGreaterEqual(Endpoint.calls,2)
        finally:
            server.shutdown();server.server_close();worker.join(1)
    def test_certificate_uses_existing_account_without_accepting_new_terms(self):
        command=certificate_command('a'*32)
        self.assertIn('--webroot',command)
        self.assertNotIn('--agree-tos',command)
        self.assertEqual(command[command.index('--account')+1],'a'*32)
        with self.assertRaises(ValueError): certificate_command('../other-account')

    def test_enabling_upload_preserves_workers_and_rejects_foreign_origins(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'controller.json'
            path.write_text(json.dumps(dict(workers=['HostMap1','HostMap2'],upload_url=None)))
            set_upload_url(path,'https://maps.wc3.uplay2.ru/')
            self.assertEqual(json.loads(path.read_text()),dict(workers=['HostMap1','HostMap2'],upload_url='https://maps.wc3.uplay2.ru/'))
            before=path.read_bytes()
            with self.assertRaises(ValueError): set_upload_url(path,'http://other.example/')
            self.assertEqual(path.read_bytes(),before)

    def test_failed_nginx_check_restores_owned_config_and_never_overwrites_foreign_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'hostmap.conf'
            old='# HostMap managed upload endpoint\nold\n'
            path.write_text(old)
            def invalid(): raise RuntimeError('nginx rejected config')
            with self.assertRaises(RuntimeError):
                write_owned(path,'# HostMap managed upload endpoint\nnew\n',invalid)
            self.assertEqual(path.read_text(),old)
            path.write_text('another service\n')
            with self.assertRaises(ValueError):
                write_owned(path,'# HostMap managed upload endpoint\nnew\n',lambda:None)
            self.assertEqual(path.read_text(),'another service\n')


if __name__=='__main__': unittest.main()
