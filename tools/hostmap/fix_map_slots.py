"""Restore GHost's map-version-aware slot defaults without restarting any bot."""
import os
from pathlib import Path
import re
import time
from core import Store
from deploy import ROOT, WORKERS, same_before


def main():
    assert os.getuid()==0
    same_before()
    store=Store(ROOT/'controller/hostmap.db',list(WORKERS))
    backup=ROOT/'backups'/('slots-auto-'+str(int(time.time())))
    backup.mkdir(parents=True,mode=0o700)
    changed=[]
    for item in store.maps():
        if not re.fullmatch('[a-f0-9]{12}',item['code']): raise ValueError('Unexpected map ID')
        path=ROOT/'assets/mapcfgs'/(item['code']+'.cfg')
        if path.is_symlink(): raise ValueError('Unexpected map config path')
        before=path.read_text()
        if 'map_maxslots' not in before: continue
        if before.count('map_maxslots = 24\n')!=1: raise ValueError('Unexpected slot override')
        (backup/path.name).write_text(before)
        temporary=path.with_suffix('.cfg.next')
        with temporary.open('x') as stream:
            stream.write(before.replace('map_maxslots = 24\n',''))
        temporary.chmod(0o444)
        os.replace(temporary,path)
        changed.append(item['code'])
    same_before()
    print('HOSTMAP_SLOT_DEFAULTS_RESTORED',changed,'BOT_RESTARTS=0','BACKUP='+str(backup))


if __name__=='__main__': main()
