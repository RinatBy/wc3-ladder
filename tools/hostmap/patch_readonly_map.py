from pathlib import Path
import hashlib,sys
path=Path(sys.argv[1])/'ghost/map.cpp'
raw=path.read_bytes(); assert hashlib.sha256(raw).hexdigest()=='6b9a513cac0acdbb67749ee5d4e6d9a1c0fc44c9cf34a01592325bc41f17764b'
old=b'SFileOpenArchive( MapMPQFileName.c_str( ), 0, MPQ_OPEN_FORCE_MPQ_V1, &MapMPQ )'
new=b'SFileOpenArchive( MapMPQFileName.c_str( ), 0, MPQ_OPEN_FORCE_MPQ_V1 | MPQ_OPEN_READ_ONLY, &MapMPQ )'
assert raw.count(old)==1
path.write_bytes(raw.replace(old,new))
print('MAP_READ_ONLY_PATCH_APPLIED')
