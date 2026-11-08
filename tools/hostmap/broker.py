"""Private host-side broker. Uploaders never supply Docker flags, paths, or configuration."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
from core import Store

ROOT=Path('/opt/warcraft-iii-online/hostmap')


def process(store, job, validator):
    if not re.fullmatch('[a-f0-9]{32}',job['id']) or not re.fullmatch('[a-f0-9]{64}',job['digest']) or job['ext'] not in ('w3x','w3m'):
        raise ValueError('Invalid quarantine job')
    path=ROOT/'incoming'/(job['id']+'.upload')
    if path.is_symlink() or path.stat().st_size != job['bytes'] or path.stat().st_size>32*1024*1024:
        raise ValueError('Invalid quarantine file')
    # Copy into a private root-owned directory before invoking native parsers.
    # Upload receiver cannot mutate this copy during inspection/publication.
    frozen=ROOT/'validation'/(job['id']+'.map')
    with path.open('rb') as source, frozen.open('xb') as destination:
        shutil.copyfileobj(source,destination,65536)
    frozen.chmod(0o444)
    try:
        with frozen.open('rb') as stream:
            digest=hashlib.sha256()
            for block in iter(lambda:stream.read(65536),b''): digest.update(block)
            if digest.hexdigest()!=job['digest']:
                raise ValueError('Quarantine checksum mismatch')
        if not validator(frozen):
            raise ValueError('Map inspection rejected')
        publish(store,job,frozen)
    finally:
        frozen.unlink(missing_ok=True)
    path.unlink()


def publish(store,job,path):
    name=job['digest']+'.'+job['ext']
    target=ROOT/'assets/maps'/name
    if target.is_symlink():
        raise ValueError('Unexpected map path')
    if not target.exists():
        with path.open('rb') as source, target.open('xb') as destination:
            shutil.copyfileobj(source,destination,65536)
        target.chmod(0o444)
    elif hashlib.sha256(target.read_bytes()).hexdigest()!=job['digest']:
        raise ValueError('Existing map checksum mismatch')
    code=store.add_map(job['digest'],job['ext'],job['title'])
    config=ROOT/'assets/mapcfgs'/(code+'.cfg')
    contents='map_path = Maps\\Download\\'+code+'.'+job['ext']+'\nmap_localpath = '+name+'\nmap_type = \nmap_observers = 4\nmap_maxslots = 24\n'
    if config.exists() and config.read_text()!=contents:
        raise ValueError('Existing map config mismatch')
    if not config.exists():
        with config.open('x') as file:
            file.write(contents)
        config.chmod(0o444)
    with store.db() as db:
        db.execute("UPDATE jobs SET state='ready',code=? WHERE id=?",(code,job['id']))


def isolated_validate(path):
    name='wc3-mapcheck-'+path.stem
    try:
        result=subprocess.run(['docker','run','--name',name,'--rm','--network','none','--read-only','--cap-drop','ALL',
        '--security-opt','no-new-privileges:true','--memory','128m','--cpus','0.4','--pids-limit','32',
        '--tmpfs','/tmp:rw,noexec,nosuid,size=16m,mode=1777',
        '--user','10002:10002','-v',str(path)+':/candidate:ro',
        '-v',str(ROOT/'assets/mapcfgs')+':/scripts:ro',
        '-v',str(ROOT/'inspect_map.py')+':/inspect_map.py:ro','--entrypoint','/usr/bin/timeout',
        'warcraft-iii-hostmap:trial','--kill-after=2','25','python3','/inspect_map.py','/candidate'],capture_output=True,timeout=35)
        if result.returncode!=0 or len(result.stdout)>1000:
            return False
        return json.loads(result.stdout).get('valid') is True
    finally:
        subprocess.run(['docker','rm','-f',name],capture_output=True,timeout=15)


def main():
    os.umask(0o077)
    store=Store(ROOT/'controller/hostmap.db',['HostMap1','HostMap2'])
    while True:
        with store.db() as db:
            abandoned=db.execute("SELECT id FROM jobs WHERE state='receiving' AND created<?",(int(time.time())-600,)).fetchall()
            for item in abandoned:
                if re.fullmatch('[a-f0-9]{32}',item['id']):
                    (ROOT/'incoming'/(item['id']+'.upload')).unlink(missing_ok=True)
                db.execute("UPDATE jobs SET state='rejected' WHERE id=?",(item['id'],))
            row=db.execute("SELECT * FROM jobs WHERE state='pending' LIMIT 1").fetchone()
        if row:
            try:
                process(store,dict(row),isolated_validate)
            except Exception as error:
                print('HOSTMAP_MAP_REJECTED',type(error).__name__,flush=True)
                with store.db() as db:
                    db.execute("UPDATE jobs SET state='rejected' WHERE id=?",(row['id'],))
                if re.fullmatch('[a-f0-9]{32}',row['id']):
                    (ROOT/'incoming'/(row['id']+'.upload')).unlink(missing_ok=True)
        time.sleep(1)


if __name__=='__main__': main()
