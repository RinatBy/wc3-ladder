import importlib.util
import io
from pathlib import Path
import struct
import socket
import tempfile
import unittest
import core
import uploads


class GuestTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.find_spec('guest')
        self.assertIsNotNone(spec, 'Guest website state has not been implemented')
        from guest import Guest
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name); (self.root/'incoming').mkdir()
        self.store = core.Store(self.root/'state.db', ['HostMap1','HostMap2'])
        self.guest = Guest(self.store, secret=b'x'*32)
        self.token, self.state = self.guest.session(None, '192.0.2.1', now=1000)
        self.other, _ = self.guest.session(None, '192.0.2.2', now=1000)
        self.statuses = {w:dict(time=1001,busy=False) for w in self.store.workers}

    def ready_map(self, token=None, ip='192.0.2.1', now=1000):
        token = token or self.token
        ticket = self.guest.upload_ticket(token, ip, now=now)
        job = uploads.receive(self.store, ticket, 'Test.w3x', 8, io.BytesIO(b'HM3Wtest'), self.root/'incoming', now=now)
        self.store.add_map('a'*64,'w3x','Test')
        with self.store.db() as db:
            db.execute("UPDATE jobs SET state='ready',code=? WHERE id=?", ('a'*12, job))
        return job

    def test_session_secrets_are_hashed_expire_and_restore_owned_state(self):
        self.assertNotIn(self.token.encode(), self.store.path.read_bytes())
        token, state = self.guest.session(self.token, '192.0.2.1', now=1001)
        self.assertEqual(token,self.token); self.assertEqual(state['csrf'],self.state['csrf'])
        with self.assertRaises(core.Rejected): self.guest.state(self.token, now=87401)

    def test_renamed_script_rejected_before_publication(self):
        ticket = self.guest.upload_ticket(self.token,'192.0.2.1',now=1000)
        data = b'print("not a Warcraft map")'
        with self.assertRaisesRegex(core.Rejected,'not a Warcraft map'):
            uploads.receive(self.store,ticket,'script.py.w3x',len(data),io.BytesIO(data),self.root/'incoming',now=1000)
        self.assertEqual(self.store.maps(),[]); self.assertEqual(list((self.root/'incoming').iterdir()),[])

    def test_ip_quota_survives_new_browser_sessions(self):
        for i in range(5):
            token,_ = self.guest.session(None,'192.0.2.9',now=1000+i*61)
            self.guest.upload_ticket(token,'192.0.2.9',now=1000+i*61)
        token,_ = self.guest.session(None,'192.0.2.9',now=1400)
        with self.assertRaises(core.Rejected): self.guest.upload_ticket(token,'192.0.2.9',now=1400)

    def test_pending_file_blocks_second_upload_and_foreign_job_is_hidden(self):
        ticket = self.guest.upload_ticket(self.token,'192.0.2.1',now=1000)
        job = uploads.receive(self.store,ticket,'Test.w3x',8,io.BytesIO(b'HM3Wtest'),self.root/'incoming',now=1000)
        with self.assertRaises(core.Rejected): self.guest.upload_ticket(self.token,'192.0.2.1',now=1061)
        with self.assertRaises(core.Rejected): self.guest.job(self.other,job,now=1001)
        with self.assertRaises(core.Rejected): self.guest.create(self.other,'b'*32,job,'Room','192.0.2.2',now=1001)

    def test_duplicate_request_one_lease_no_claimed_player_privileges(self):
        job = self.ready_map()
        a = self.guest.create(self.token,'b'*32,job,'Guest Room','192.0.2.1',now=1001)
        b = self.guest.create(self.token,'b'*32,job,'Guest Room','192.0.2.1',now=1001)
        self.assertEqual(a,b)
        dispatch = self.guest.dispatch(self.statuses, now=1001)
        self.assertEqual(dispatch['command'],'!hmhost 1001 aaaaaaaaaaaa HostMap Guest Room')
        self.assertIsNone(self.guest.dispatch(self.statuses, now=1002))
        with self.store.db() as db: self.assertEqual(db.execute('SELECT count(*) FROM leases').fetchone()[0],1)
        with self.assertRaises(core.Rejected): self.guest.create(self.token,'c'*32,job,'Other','192.0.2.1',now=1002)
        with self.assertRaises(core.Rejected): self.guest.request(self.other,'b'*32,now=1002)

    def test_advertisement_requires_exact_room_endpoint_and_fresh_worker(self):
        job=self.ready_map(); self.guest.create(self.token,'b'*32,job,'Guest Room','192.0.2.1',now=1001)
        dispatch=self.guest.dispatch(self.statuses,now=1001)
        body=struct.pack('<I',1)+b'\0'*10+struct.pack('>H',6117)+socket.inet_aton('176.124.218.23')+b'Guest Room\0'
        self.assertFalse(self.guest.confirm(body,self.statuses,now=1002))
        self.statuses[dispatch['worker']]=dict(time=1002,busy=True)
        self.assertFalse(self.guest.confirm(body.replace(b'Guest Room',b'Other Room'),self.statuses,now=1002))
        self.assertTrue(self.guest.confirm(body,self.statuses,now=1002))
        self.assertEqual(self.guest.request(self.token,'b'*32,now=1002)['state'],'advertised')

    def test_lost_dispatch_is_not_replayed_and_busy_is_retryable(self):
        job=self.ready_map(); self.guest.create(self.token,'b'*32,job,'Guest Room','192.0.2.1',now=1001)
        self.guest.dispatch(self.statuses,now=1001)
        self.assertIsNone(self.guest.dispatch(self.statuses,now=1002))
        self.guest.dispatch({},now=1050)
        self.assertEqual(self.guest.request(self.token,'b'*32,now=1050)['state'],'failed')
        # The sixty-second lease guard outlives the worker's thirty-second command validity.
        statuses={w:dict(time=1063,busy=True) for w in self.store.workers}
        statuses['HostMap1']['busy']=False
        self.guest.create(self.token,'c'*32,job,'Retry Room','192.0.2.1',now=1063)
        self.assertEqual(self.guest.dispatch(statuses,now=1063)['worker'],'HostMap1')


if __name__=='__main__': unittest.main()
