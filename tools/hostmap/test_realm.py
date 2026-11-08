import socket
import struct
import unittest
import realm


class ProtocolTests(unittest.TestCase):
    def test_fragmented_packets_and_ping_do_not_corrupt_chat(self):
        parser = realm.Frames()
        wire = b'\xff\x25\x08\x00abcd\xff\x0f\x07\x00xyz'
        packets = []
        for byte in wire:
            packets.extend(parser.feed(bytes([byte])))
        self.assertEqual(packets, [(0x25, b'abcd'), (0x0f, b'xyz')])

    def test_invalid_frame_length_and_marker_rejected(self):
        for data in (b'\x00\x0f\x04\x00', b'\xff\x0f\x03\x00'):
            with self.assertRaises(ValueError):
                realm.Frames().feed(data)

    def test_chat_identity_comes_from_envelope_not_message(self):
        body = struct.pack('<6I', 4, 0, 0, 0, 0, 0) + b'Player2\0uPlay: !host x\0'
        self.assertEqual(realm.chat_event(body), (4, 'Player2', 'uPlay: !host x'))
        self.assertIsNone(realm.chat_event(b'bad'))


if __name__ == '__main__':
    unittest.main()
