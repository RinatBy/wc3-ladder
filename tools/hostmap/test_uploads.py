import io
import tempfile
import unittest
import threading
from pathlib import Path
import core
import uploads


class UploadTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.store = core.Store(self.root/'state.db',['HostMap1'])
        (self.root/'incoming').mkdir()

    def test_stream_size_and_filename_checked_before_publication(self):
        for index,(filename,size,data) in enumerate([('../evil.w3x',4,b'HM3W'),('x.exe',4,b'HM3W'),
                                   ('x.w3x',100,b'HM3W'),('x.w3x',0,b''),
                                   ('x.w3x',32*1024*1024+1,b'')]):
            now = 1000+index*100
            token = self.store.issue_upload('uPlay',now=now)
            with self.assertRaises(core.Rejected):
                uploads.receive(self.store,token,filename,size,io.BytesIO(data),self.root/'incoming',now=now)
            self.assertEqual(list((self.root/'incoming').iterdir()),[])

    def test_upload_is_quarantined_not_added_directly_to_catalog(self):
        token = self.store.issue_upload('uPlay',now=1000)
        job = uploads.receive(self.store,token,'my map.w3x',8,io.BytesIO(b'HM3Wtest'),self.root/'incoming',now=1000)
        self.assertEqual(self.store.maps(),[])
        self.assertEqual(uploads.job_status(self.store,job)['state'],'pending')
        self.assertEqual(len(list((self.root/'incoming').iterdir())),1)
        with self.assertRaises(core.Rejected):
            uploads.receive(self.store,token,'my map.w3x',8,io.BytesIO(b'HM3Wtest'),self.root/'incoming',now=1000)

    def test_in_progress_upload_already_reserves_disk_quota(self):
        with self.store.db() as db:
            db.execute("INSERT INTO jobs (id,bytes,state) VALUES ('existing',?,'ready')",(1024**3-8,))
        entered=threading.Event(); release=threading.Event(); failures=[]
        class Slow(io.BytesIO):
            def read(self,n=-1):
                entered.set()
                if not release.wait(4): raise RuntimeError('Test receiver timed out')
                return super().read(n)
        token1=self.store.issue_upload('uPlay',now=1000)
        token2=self.store.issue_upload('Player2',now=1000)
        def first():
            try: uploads.receive(self.store,token1,'one.w3x',8,Slow(b'HM3Wtest'),self.root/'incoming',now=1000)
            except Exception as error: failures.append(error)
        thread=threading.Thread(target=first);thread.start()
        try:
            self.assertTrue(entered.wait(3))
            with self.assertRaisesRegex(core.Rejected,'storage is full'):
                uploads.receive(self.store,token2,'two.w3x',8,io.BytesIO(b'HM3Wtest'),self.root/'incoming',now=1000)
        finally:
            release.set();thread.join(5)
        self.assertEqual(failures,[])


if __name__ == '__main__':
    unittest.main()
