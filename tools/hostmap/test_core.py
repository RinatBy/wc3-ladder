import hashlib
import io
import tempfile
import unittest
from pathlib import Path

import core


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.store = core.Store(self.root / 'state.db', ['HostMap1', 'HostMap2'])
        self.store.add_map('a' * 64, 'w3x', 'Echo Isles')
        self.statuses = {w: dict(time=1000, busy=False) for w in ['HostMap1', 'HostMap2']}

    def test_parallel_reservations_never_share_worker(self):
        a = self.store.host('uPlay', 'a' * 12, 'Room One', self.statuses, now=1000)
        b = self.store.host('Player2', 'a' * 12, 'Room Two', self.statuses, now=1000)
        self.assertNotEqual(a['worker'], b['worker'])
        with self.assertRaises(core.Rejected):
            self.store.host('Player3', 'a' * 12, 'Room Three', self.statuses, now=1000)

    def test_one_room_per_case_insensitive_account(self):
        self.store.host('uPlay', 'a' * 12, 'Room', self.statuses, now=1000)
        with self.assertRaises(core.Rejected):
            self.store.host('UPLAY', 'a' * 12, 'Another', self.statuses, now=1000)

    def test_stale_missing_or_busy_workers_are_not_free(self):
        for statuses in ({}, {'HostMap1': dict(time=900, busy=False)},
                         {'HostMap1': dict(time=1000, busy=True)}):
            with self.assertRaises(core.Rejected):
                self.store.host('uPlay', 'a' * 12, 'Room', statuses, now=1000)

    def test_active_room_released_only_after_fresh_idle(self):
        a = self.store.host('uPlay', 'a' * 12, 'Room', self.statuses, now=1000)
        self.store.reconcile({a['worker']: dict(time=1001, busy=True)}, now=1001)
        self.store.reconcile({a['worker']: dict(time=1002, busy=False)}, now=1002)
        self.statuses[a['worker']]['time'] = 1002
        self.assertEqual(self.store.host('uPlay', 'a' * 12, 'Again', self.statuses, now=1002)['worker'], a['worker'])

    def test_pending_room_is_not_released_by_early_idle_snapshot(self):
        a = self.store.host('uPlay', 'a' * 12, 'Room', self.statuses, now=1000)
        self.store.reconcile(self.statuses, now=1001)
        with self.assertRaises(core.Rejected):
            self.store.host('uPlay', 'a' * 12, 'Again', self.statuses, now=1001)

    def test_rejects_command_injection_and_paths(self):
        for owner, code, room in [('uPlay\n/w x', 'a'*12, 'Room'), ('uPlay', '../a', 'Room'),
                                  ('uPlay', 'a'*12, 'Room\n!quit'), ('uPlay', 'a'*12, '/w root')]:
            with self.assertRaises(core.Rejected):
                self.store.host(owner, code, room, self.statuses, now=1000)

    def test_upload_token_one_use_expiry_and_rate_limit(self):
        token = self.store.issue_upload('uPlay', now=1000)
        self.assertNotIn(token, (self.root/'state.db').read_bytes().decode('latin1'))
        with self.assertRaises(core.Rejected):
            self.store.issue_upload('uPlay', now=1001)
        self.assertEqual(self.store.claim_upload(token, now=1002), 'uPlay')
        with self.assertRaises(core.Rejected):
            self.store.claim_upload(token, now=1003)
        token2 = self.store.issue_upload('Player2', now=1000)
        with self.assertRaises(core.Rejected):
            self.store.claim_upload(token2, now=2000)

    def test_unknown_maps_and_duplicate_names_rejected(self):
        with self.assertRaises(core.Rejected):
            self.store.host('uPlay', 'b'*12, 'Room', self.statuses, now=1000)
        self.store.host('uPlay', 'a'*12, 'Room', self.statuses, now=1000)
        with self.assertRaises(core.Rejected):
            self.store.host('Player2', 'a'*12, 'room', self.statuses, now=1000)

    def test_short_code_collision_is_not_silently_accepted(self):
        with self.assertRaises(core.Rejected):
            self.store.add_map('a'*12+'b'*52,'w3x','Other map')


if __name__ == '__main__':
    unittest.main()
