"""One-off operator import. Public upload limits and running games are unchanged."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import time
from urllib.parse import urlsplit
from urllib.request import build_opener, HTTPRedirectHandler
from core import Store
from deploy import ROOT
from deploy_chrome import processes
from broker import publish

CDN='b55d83c2-c25d-46dd-87f4-faa682e06a05.selcdn.net'
MAXIMUM=128*1024*1024


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs): raise ValueError('Unexpected download redirect')


def checksum(path):
    value=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(65536),b''):value.update(chunk)
    return value.hexdigest()


def manifest():
    rows=json.loads((ROOT/'operator-map-import.json').read_text())
    if len(rows)!=7 or len({r['sha256'] for r in rows})!=7:raise ValueError('Unexpected import set')
    for r in rows:
        url=urlsplit(r['url'])
        if (url.scheme!='https' or url.hostname!=CDN or url.username or url.password or
            not re.fullmatch('[a-f0-9]{64}',r['sha256']) or not 4<=r['bytes']<=MAXIMUM or
            not r['file'].endswith('.w3x') or '/' in r['file'] or '\\' in r['file']):
            raise ValueError('Invalid operator manifest')
    return rows


def download(row,target):
    if target.exists():
        if target.is_symlink() or target.stat().st_size!=row['bytes'] or checksum(target)!=row['sha256']:
            raise ValueError('Existing staged file does not match local source')
        return
    temporary=target.with_suffix('.part')
    temporary.unlink(missing_ok=True)
    try:
        with build_opener(NoRedirect()).open(row['url'],timeout=60) as response,temporary.open('xb') as out:
            left=row['bytes']
            while left:
                block=response.read(min(left,65536))
                if not block:raise ValueError('Truncated download')
                out.write(block);left-=len(block)
            if response.read(1):raise ValueError('Oversized download')
        if checksum(temporary)!=row['sha256']:raise ValueError('Download differs from local file')
        temporary.chmod(0o444);os.replace(temporary,target)
    finally:temporary.unlink(missing_ok=True)


def inspector(directory):
    # Broaden only this private, bounded checker for the two approved large files.
    # The public receiver, broker and original validator remain unchanged.
    text=(ROOT/'inspect_map.py').read_text()
    needle='<= 32*1024*1024:'
    if text.count(needle)!=1:raise RuntimeError('Unexpected size guard')
    text=text.replace(needle,'<= 128*1024*1024:')
    needle='result=dict(valid=True,format=version)'
    if text.count(needle)!=1:raise RuntimeError('Unexpected validator result')
    text=text.replace(needle,"result=dict(valid=True,format=version,map_name=info[12:info.index(b'\\0',12)].decode('utf-8','replace')[:160])")
    path=directory/'inspect_operator.py';path.write_text(text);path.chmod(0o444)
    return path


def validate(row,path,checker):
    name='wc3-operator-check-'+row['sha256'][:12]
    try:
        command=['docker','run','--name',name,'--rm','--network','none','--read-only','--cap-drop','ALL',
            '--security-opt','no-new-privileges:true','--memory','512m','--memory-swap','512m',
            '--cpus','0.5','--pids-limit','32','--tmpfs','/tmp:rw,noexec,nosuid,size=16m,mode=1777',
            '--user','10002:10002','-v',str(path)+':/candidate:ro',
            '-v',str(ROOT/'assets/mapcfgs')+':/scripts:ro','-v',str(checker)+':/inspect_map.py:ro',
            '--entrypoint','/usr/bin/timeout','warcraft-iii-hostmap:trial','--kill-after=2','75',
            'python3','/inspect_map.py','/candidate']
        result=subprocess.run(command,capture_output=True,timeout=85)
        if result.returncode or len(result.stdout)>4096:
            raise ValueError('Native check failed: '+result.stderr.decode('utf-8','replace')[-1400:])
        data=json.loads(result.stdout)
        if data.get('valid') is not True:raise ValueError('Map check rejected')
        return data
    finally:subprocess.run(['docker','rm','-f',name],capture_output=True,timeout=15)


def main(publish_maps):
    os.umask(0o077);rows=manifest();before=processes()
    if not all(v['pid'] for v in before.values()):raise RuntimeError('A service is not running')
    marker=ROOT/'controller/guest-enabled';access=marker.read_bytes()
    if access!=b'approved-public-guest-web\n':raise RuntimeError('Unexpected access state')
    if shutil.disk_usage(ROOT).free<sum(r['bytes'] for r in rows)*2+256*1024**2:
        raise RuntimeError('Insufficient disk reserve')
    directory=ROOT/'operator-import-20261110'
    if directory.is_symlink():raise RuntimeError('Unexpected import directory')
    directory.mkdir(exist_ok=True,mode=0o700)
    checker=inspector(directory);store=Store(ROOT/'controller/hostmap.db',['HostMap1','HostMap2'])
    backup=None
    if publish_maps:
        backup=ROOT/'backups'/('operator-import-'+str(int(time.time())));backup.mkdir(mode=0o700)
        with sqlite3.connect(store.path) as src,sqlite3.connect(backup/'hostmap.db') as dst:src.backup(dst)
        (backup/'hostmap.db').chmod(0o600)
    results=[]
    cache=directory/'validated.json'
    validated=json.loads(cache.read_text()) if cache.exists() else {}
    for row in rows:
        record={k:row[k] for k in ('file','title','bytes','sha256','source_id')}
        try:
            with store.db() as db:known=db.execute('SELECT code,ext FROM maps WHERE digest=?',(row['sha256'],)).fetchone()
            if known:
                existing=ROOT/'assets/maps'/(row['sha256']+'.'+known['ext'])
                if not existing.is_file() or checksum(existing)!=row['sha256']:raise ValueError('Published map mismatch')
                record.update(state='already_present',code=known['code'])
            else:
                path=directory/(row['sha256']+'.map');download(row,path)
                if row['sha256'] not in validated:
                    validated[row['sha256']]=validate(row,path,checker)
                    cache.write_text(json.dumps(validated,ensure_ascii=False,indent=2)+'\n')
                record.update(validation=validated[row['sha256']],state='validated')
                if publish_maps:
                    job_id=row['sha256'][:32]
                    with store.db() as db:
                        db.execute("INSERT OR IGNORE INTO jobs (id,owner,digest,ext,title,bytes,state,created) VALUES (?,?,?,'w3x',?,?,'importing',?)",(job_id,'uPlay',row['sha256'],row['title'],row['bytes'],int(time.time())))
                        job=db.execute('SELECT * FROM jobs WHERE id=?',(job_id,)).fetchone()
                        if job['digest']!=row['sha256']:raise ValueError('Job identity collision')
                    publish(store,dict(job),path)
                    path.unlink();record.update(state='published',code=row['sha256'][:12])
        except Exception as error:
            record.update(state='rejected',error=str(error))
        results.append(record)
        print(json.dumps(record,ensure_ascii=True),flush=True)
    report=dict(published=publish_maps,backup=str(backup) if backup else None,maps=results,
                services_unchanged=processes()==before,access_unchanged=marker.read_bytes()==access)
    (directory/('published.json' if publish_maps else 'checked.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    if not report['services_unchanged'] or not report['access_unchanged']:raise RuntimeError('Service or access state changed')
    if any(r['state']=='rejected' for r in results):raise SystemExit(2)
    print('OPERATOR_MAP_IMPORT_OK '+str(len(results)),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--publish',action='store_true');args=parser.parse_args()
    main(args.publish)
