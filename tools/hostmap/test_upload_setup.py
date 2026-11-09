import json
from pathlib import Path
import tempfile
import unittest
from enable_uploads import certificate_command, set_upload_url, write_owned


class SetupTests(unittest.TestCase):
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
