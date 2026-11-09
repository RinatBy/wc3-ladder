"""Run ONLY in the disposable no-network map-inspection container."""
import ctypes as c
import json
import os
from pathlib import Path
import struct
import re
import shutil
import subprocess
import sys


def validate_info(data):
    offset=0
    def take(size):
        nonlocal offset
        if size<0 or offset+size>len(data): raise ValueError('Truncated W3I')
        value=data[offset:offset+size];offset+=size
        return value
    def number(): return struct.unpack('<I',take(4))[0]
    def string():
        nonlocal offset
        end=data.find(b'\0',offset)
        if end<0 or end-offset>65536: raise ValueError('Invalid W3I string')
        offset=end+1
    version=number()
    if version not in (18,25): raise ValueError('Unsupported W3I version')
    take(8)
    for _ in range(4): string()
    take(48)
    width,height=number(),number()
    if not 1<=width<=1024 or not 1<=height<=1024: raise ValueError('Invalid map dimensions')
    take(5)
    take(4)
    if version==25: string()
    for _ in range(3): string()
    take(4)
    if version==25: string()
    for _ in range(3): string()
    if version==25:
        take(24);string();take(5)
    count=number()
    if not 1<=count<=24: raise ValueError('Invalid player count')
    for _ in range(count):
        colour=number();status=number();number();number();string();take(16)
        if colour>=24 or status>4: raise ValueError('Invalid player slot')
    teams=number()
    if not 1<=teams<=24: raise ValueError('Invalid team count')
    for _ in range(teams): take(8);string()
    return version


def inspect(path, library='/opt/ghost/lib/libstorm.so', native=False):
    path=Path(path)
    if path.is_symlink() or not 4 <= path.stat().st_size <= 32*1024*1024:
        raise ValueError('Map size or type rejected')
    if os.name!='nt':
        # This pinned StormLib is built with USE_WITH_CASC: shared hash helpers
        # live in CascLib, which GHost links globally as well.
        c.CDLL('/opt/ghost/lib/libcasc.so',mode=c.RTLD_GLOBAL)
    lib=(c.WinDLL if os.name=='nt' else c.CDLL)(str(library))
    path_type=c.c_wchar_p if os.name=='nt' else c.c_char_p
    lib.SFileOpenArchive.argtypes=[path_type,c.c_uint32,c.c_uint32,c.POINTER(c.c_void_p)]
    lib.SFileOpenFileEx.argtypes=[c.c_void_p,c.c_char_p,c.c_uint32,c.POINTER(c.c_void_p)]
    lib.SFileGetFileSize.argtypes=[c.c_void_p,c.POINTER(c.c_uint32)]
    lib.SFileGetFileSize.restype=c.c_uint32
    lib.SFileReadFile.argtypes=[c.c_void_p,c.c_void_p,c.c_uint32,c.POINTER(c.c_uint32),c.c_void_p]
    lib.SFileCloseFile.argtypes=[c.c_void_p]
    lib.SFileCloseArchive.argtypes=[c.c_void_p]
    archive=c.c_void_p()
    native_path=str(path.resolve()) if os.name=='nt' else os.fsencode(path)
    if not lib.SFileOpenArchive(native_path,0,0x100,c.byref(archive)):
        raise ValueError('Invalid MPQ archive')
    def read(name, maximum, optional=False):
        member=c.c_void_p()
        if not lib.SFileOpenFileEx(archive,name.encode(),0,c.byref(member)):
            if optional: return b''
            raise ValueError('Missing map member')
        try:
            high=c.c_uint32()
            size=lib.SFileGetFileSize(member,c.byref(high))
            if optional and size in (0,0xffffffff) and not high.value: return b''
            if high.value or not 0<size<=maximum:
                raise ValueError('Map member size rejected: '+name)
            buffer=c.create_string_buffer(size)
            got=c.c_uint32()
            if not lib.SFileReadFile(member,buffer,size,c.byref(got),None) or got.value!=size:
                raise ValueError('Map member cannot be read')
            return buffer.raw
        finally:
            lib.SFileCloseFile(member)
    try:
        info=read('war3map.w3i',512*1024)
        version=validate_info(info)
        terrain=read('war3map.w3e',16*1024*1024)
        if not terrain.startswith(b'W3E!'):
            raise ValueError('Invalid terrain')
        script=read('war3map.j',8*1024*1024,optional=True)
        if not script:
            script=read('Scripts\\war3map.j',8*1024*1024)
        if b'function main' not in script:
            raise ValueError('Missing map entry point')
        total=len(info)+len(terrain)+len(script)
        for name in ('Scripts\\common.j','Scripts\\blizzard.j','war3map.wpm','war3map.doo',
                     'war3map.w3u','war3map.w3b','war3map.w3d','war3map.w3a','war3map.w3q'):
            total+=len(read(name,16*1024*1024,optional=True))
            if total>48*1024*1024: raise ValueError('Excessive expanded map size')
        result=dict(valid=True,format=version)
        if native:
            result.update(validate_native())
        return result
    finally:
        lib.SFileCloseArchive(archive)


def validate_native():
    root=Path('/tmp/hostmap-check')
    root.mkdir()
    for name in ('common.j','blizzard.j'):
        shutil.copyfile(Path('/scripts')/name,root/name)
    (root/'candidate.cfg').write_text('map_path = Maps\\Download\\candidate.w3x\nmap_localpath = candidate\nmap_observers = 4\n')
    config=dict(hostmap_validate='1',bot_mapcfgpath=str(root)+'/',bot_mappath='/',
        bot_defaultmap='candidate.cfg',bot_war3path='/tmp/no-auth/',bnet_server='',
        bot_log=str(root/'native.log'),db_type='sqlite3',db_sqlite3_file=str(root/'native.db'),
        bot_ipblacklistfile='',bot_hostport='0',bot_bindaddress='127.0.0.1',admingame_create='0')
    cfg=root/'ghost.cfg'
    cfg.write_text(''.join(k+' = '+v+'\n' for k,v in config.items()))
    with (root/'console.log').open('w+') as log:
        result=subprocess.run(['/opt/ghost/ghost++',str(cfg)],stdout=log,stderr=log,timeout=20)
        log.seek(0)
        output=log.read(1024*1024)
    if result.returncode!=0 or 'HOSTMAP_NATIVE_MAP_VALID' not in output.splitlines()[-10:]:
        # Console lines can have timestamps; the marker is generated by our patched constructor.
        if result.returncode!=0 or not any(line.endswith('HOSTMAP_NATIVE_MAP_VALID') for line in output.splitlines()):
            print('NATIVE_CHECK_DIAGNOSTIC',result.returncode,output[-2000:],file=sys.stderr)
            raise ValueError('Native GHost map validation failed')
    added=re.findall(r'\[MAP\] adding (\d+) observer slots',output)
    return dict(observer_slots_added=int(added[-1])) if added else {}


if __name__=='__main__':
    try:
        result=inspect(sys.argv[1],native=True)
    except Exception as error:
        print('MAP_CHECK_FAILED',type(error).__name__,str(error),file=sys.stderr)
        result=dict(valid=False)
    print(json.dumps(result))
    raise SystemExit(0 if result['valid'] else 1)
