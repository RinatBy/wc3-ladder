import tempfile
import unittest
from pathlib import Path
from broker import freeze


class FreezeTests(unittest.TestCase):
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
