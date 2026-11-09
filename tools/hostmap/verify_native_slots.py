"""VDS regression check: reproduce forced-24 slots and verify map-version-aware defaults.

Runs only native map parsing in disposable no-network containers, never an active game.
"""
import json
from pathlib import Path
import secrets
import subprocess
from core import Store
from deploy import ROOT, WORKERS, same_before


def inspect(path,script):
    name='wc3-slot-check-'+secrets.token_hex(8)
    command=['docker','run','--rm','--name',name,'--network','none','--read-only',
        '--memory','128m','--cpus','0.4','--pids-limit','32','--cap-drop','ALL',
        '--security-opt','no-new-privileges:true','--tmpfs','/tmp:rw,noexec,nosuid,size=16m,mode=1777',
        '--user','10002:10002','-v',str(path)+':/candidate:ro',
        '-v',str(ROOT/'assets/mapcfgs')+':/scripts:ro','-v',str(script)+':/inspect_map.py:ro',
        '--entrypoint','/usr/bin/timeout','warcraft-iii-hostmap:trial',
        '--kill-after=2','25','python3','/inspect_map.py','/candidate']
    try:
        result=subprocess.run(command,capture_output=True,text=True,timeout=35)
        if result.returncode!=0: raise RuntimeError(result.stderr[-2000:])
        return json.loads(result.stdout)
    finally:
        subprocess.run(['docker','rm','-f',name],capture_output=True,timeout=15)


def main():
    same_before()
    store=Store(ROOT/'controller/hostmap.db',list(WORKERS))
    item=next(x for x in store.maps('LoD') if x['title']=='DotA LoD 6.85oz')
    path=ROOT/'assets/maps'/(item['digest']+'.'+item['ext'])
    current=ROOT/'inspect_map.py'
    source=current.read_text()
    anchor='map_observers = 4\\n'
    if source.count(anchor)!=1: raise ValueError('Unexpected native validation config')
    legacy=ROOT/'validation'/('slots-forced-'+secrets.token_hex(6)+'.py')
    legacy.write_text(source.replace(anchor,anchor+'map_maxslots = 24\\n'))
    legacy.chmod(0o444)
    try:
        before=inspect(path,legacy)
        after=inspect(path,current)
    finally:
        legacy.unlink(missing_ok=True)
    assert before['valid'] and before['observer_slots_added']==14,before
    assert after['valid'] and after['observer_slots_added']==2,after
    same_before()
    report=dict(old_forced24_observers=14,version_aware_observers=2,
                map_code=item['code'],native_regression_passed=True,bot_restarts=0)
    (ROOT/'slot-fix-verified.json').write_text(json.dumps(report,indent=2)+'\n')
    print('HOSTMAP_NATIVE_SLOT_FIX_VERIFIED',json.dumps(report))


if __name__=='__main__': main()
