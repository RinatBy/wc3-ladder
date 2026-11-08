import io
import tempfile
import unittest
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


if __name__ == '__main__':
    unittest.main()
