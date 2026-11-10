"""Update only owned public HTML/CSS/images and nginx's static-file allowlist."""
import json
import os
from pathlib import Path
import re
import shutil
import time
from deploy import ROOT,PROJECT,PERMANENT,inspect
from enable_uploads import SITE,MARKER,write_owned,nginx_check_reload
from ui_assets import WEB_FILES


def processes():
    names=PERMANENT+[PROJECT+'-'+name+'-1' for name in ('hostmap1','hostmap2','controller','uploads')]
    return {name:dict(id=v['Id'],pid=v['State']['Pid'],started=v['State']['StartedAt']) for name in names for v in [inspect(name)]}


def main():
    before=processes()
    if not all(v['pid'] for v in before.values()): raise RuntimeError('A service is not running; inspect before styling')
    public=Path('/var/www/wc3-hostmap')
    if public.is_symlink() or (public/'.hostmap-owned').read_text()!='HostMap static frontend only\n':
        raise RuntimeError('Unexpected public webroot')
    marker=ROOT/'controller/guest-enabled';access=marker.read_bytes()
    if access!=b'approved-public-guest-web\n': raise RuntimeError('Unexpected access marker')
    backup=ROOT/'backups'/('chrome-'+str(int(time.time())))
    backup.mkdir(parents=True,mode=0o700)
    current=SITE.read_text()
    if not current.startswith(MARKER): raise RuntimeError('Foreign nginx site')
    (backup/'nginx.conf').write_text(current)
    for name in WEB_FILES:
        source=ROOT/'web'/name
        if source.is_symlink() or not source.is_file(): raise RuntimeError('Missing public asset: '+name)
        old=public/name
        if old.exists(): shutil.copyfile(old,backup/name)
        temporary=public/(name+'.chrome-next')
        shutil.copyfile(source,temporary);temporary.chmod(0o644);os.replace(temporary,old)
    allowed='|'.join(re.escape(n) for n in WEB_FILES if n!='index.html')
    updated,count=re.subn(r'location ~ \^/web/\([^\n]+\)\$ \{',lambda _:'location ~ ^/web/('+allowed+')$ {',current)
    if count!=1: raise RuntimeError('Expected exactly one owned static allowlist')
    write_owned(SITE,updated,nginx_check_reload)
    if processes()!=before or marker.read_bytes()!=access: raise RuntimeError('A process or access setting changed')
    result=dict(public_files=len(WEB_FILES),service_restarts=0,guest_access_unchanged=True,backup=str(backup))
    (ROOT/'chrome-verified.json').write_text(json.dumps(result,indent=2)+'\n')
    print('SHARED_SITE_CHROME_DEPLOYED '+json.dumps(result))


if __name__=='__main__': main()
