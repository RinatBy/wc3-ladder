import tempfile
import unittest
from pathlib import Path
from broker import freeze
from unittest.mock import patch
import hashlib
import broker
from core import Store


class FreezeTests(unittest.TestCase):
    def test_same_bytes_with_different_extension_share_one_published_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'assets/maps').mkdir(parents=True);(root/'assets/mapcfgs').mkdir()
            data=b'HM3Wtest';source=root/'source';source.write_bytes(data)
            store=Store(root/'state.db',['HostMap1']);digest=hashlib.sha256(data).hexdigest()
            with patch.object(broker,'ROOT',root):
                for ext in ('w3x','w3m'):
                    broker.publish(store,dict(id=ext,digest=digest,ext=ext,title='Map'),source)
            self.assertEqual(len(list((root/'assets/maps').iterdir())),1)
            self.assertEqual(len(store.maps()),1)

    def test_only_expected_regular_file_is_copied(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'source';source.write_bytes(b'HM3Wtest')
            freeze(source,root/'frozen',8)
            self.assertEqual((root/'frozen').read_bytes(),b'HM3Wtest')
            with self.assertRaises(ValueError): freeze(source,root/'wrong',4)
            self.assertFalse((root/'wrong').exists())

    def test_directory_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            with self.assertRaises((ValueError,OSError)): freeze(root,root/'wrong',8)


if __name__=='__main__': unittest.main()
