import hashlib
import io
from pathlib import Path
import tempfile
import unittest
from core import Store, Rejected
from guest import Guest
import uploads


class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);(self.root/'incoming').mkdir()
        self.store=Store(self.root/'state.db',['HostMap1','HostMap2'])
        self.guest=Guest(self.store,secret=b'x'*32)
        self.token,_=self.guest.session(None,'192.0.2.1',now=1000)
        self.data=b'HM3Wtest';self.digest=hashlib.sha256(self.data).hexdigest()
        self.code=self.store.add_map(self.digest,'w3x','Spec Arena.w3x')

    def test_catalog_only_contains_validated_maps_and_public_fields(self):
        with self.store.db() as db:
            db.execute("INSERT INTO jobs (id,title,state) VALUES ('quarantine','Unverified','pending')")
        result=self.guest.catalog(self.token,now=1001)
        self.assertEqual([m['code'] for m in result['maps']],[self.code])
        self.assertEqual(set(result['maps'][0]),{'code','title','ext','digest'})
        self.assertEqual(self.guest.catalog(self.token,query='ARENA',now=1001)['maps'],result['maps'])
        self.assertEqual(self.guest.catalog(self.token,digest='f'*64,now=1001)['maps'],[])
        with self.assertRaises(Rejected):self.guest.catalog(None,now=1001)

    def test_catalog_is_bounded_and_selection_does_not_create_uploads(self):
        for n in range(105):self.store.add_map(hashlib.sha256(str(n).encode()).hexdigest(),'w3x','Map '+str(n))
        self.assertEqual(len(self.guest.catalog(self.token,now=1001)['maps']),100)
        self.assertTrue(self.guest.catalog(self.token,now=1001)['more'])
        selected=self.guest.select(self.token,self.code,now=1001)
        self.assertEqual(selected['job']['id'],'map:'+self.code)
        self.assertEqual(self.guest.state(self.token,now=1002)['job'],selected['job'])
        with self.store.db() as db:self.assertEqual(db.execute('SELECT count(*) FROM jobs').fetchone()[0],0)
        result=self.guest.create(self.token,'b'*32,selected['job']['id'],'Catalog Room','192.0.2.1',now=1002)
        self.assertEqual(result['state'],'queued')
        with self.assertRaises(Rejected):self.guest.select(self.token,'../../etc/passwd',now=1002)
        with self.assertRaises(Rejected):self.guest.select(self.token,'f'*12,now=1002)

    def test_duplicate_bytes_reuse_map_without_quarantine_or_extra_quota(self):
        ticket=self.guest.upload_ticket(self.token,'192.0.2.1',now=1001)
        job=uploads.receive(self.store,ticket,'renamed.w3m',len(self.data),io.BytesIO(self.data),self.root/'incoming',now=1001)
        result=self.guest.job(self.token,job,now=1002)
        self.assertEqual(result['state'],'ready');self.assertEqual(result['code'],self.code)
        self.assertEqual(list((self.root/'incoming').iterdir()),[])
        with self.store.db() as db:self.assertEqual(db.execute('SELECT count(*) FROM maps').fetchone()[0],1)

    def test_duplicate_ready_jobs_do_not_exhaust_storage_quota(self):
        with self.store.db() as db:
            for n in range(34):
                db.execute("INSERT INTO jobs (id,digest,bytes,state) VALUES (?,?,?,'ready')",(str(n),self.digest,32*1024*1024))
        ticket=self.guest.upload_ticket(self.token,'192.0.2.1',now=1001)
        job=uploads.receive(self.store,ticket,'Spec Arena.w3x',8,io.BytesIO(b'HM3Wdiff'),self.root/'incoming',now=1001)
        self.assertEqual(self.guest.job(self.token,job,now=1002)['state'],'pending')
        self.assertEqual(len(list((self.root/'incoming').iterdir())),1)


if __name__=='__main__':unittest.main()
