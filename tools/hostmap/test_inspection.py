import struct
import unittest
from inspect_map import validate_info


class MapInfoTests(unittest.TestCase):
    def test_four_byte_format_is_not_a_valid_map_header(self):
        with self.assertRaises(ValueError): validate_info(struct.pack('<I',25))

    def test_unterminated_or_excessive_player_data_rejected(self):
        for body in (struct.pack('<III',25,0,0)+b'X'*100,
                     struct.pack('<III',99,0,0)+b'\0'*100):
            with self.assertRaises(ValueError): validate_info(body)


if __name__=='__main__': unittest.main()
