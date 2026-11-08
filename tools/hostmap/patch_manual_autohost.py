from pathlib import Path
import hashlib
import sys

path = Path(sys.argv[1]) / 'ghost' / 'ghost.cpp'
raw = path.read_bytes()
assert hashlib.sha256(raw).hexdigest() == '033440dba8a8946775987e5bbf6f23a870294b7d9fcbc52f146b3ecd236e5bc9'
old = b' && m_AutoHostAutoStartPlayers != 0 && GetTime( ) - m_LastAutoHostTime >= 30'
new = b' && GetTime( ) - m_LastAutoHostTime >= 30'
assert raw.count(old) == 1
path.write_bytes(raw.replace(old, new))
print('MANUAL_AUTOHOST_PATCH_APPLIED; MATCH_AUTOSTART_ZERO_PRESERVED')
