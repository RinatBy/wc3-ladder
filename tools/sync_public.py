"""Publish only the allowlisted public snapshot using a repository-scoped SSH key."""
import fcntl
import json
import os
from pathlib import Path
import re
import subprocess

from export_public import export, MAPS, load_display_names

ROOT=Path('/opt/warcraft-iii-online/ladder')
REPOSITORY='git@github.com:RinatBy/wc3-ladder.git'


def main():
    env=dict(os.environ, GIT_TERMINAL_PROMPT='0', GIT_SSH_COMMAND=(
        'ssh -i /opt/warcraft-iii-online/ladder/keys/github '
        '-o IdentitiesOnly=yes -o BatchMode=yes -o StrictHostKeyChecking=yes '
        '-o UserKnownHostsFile=/opt/warcraft-iii-online/ladder/keys/known_hosts '
        '-o HostKeyAlgorithms=ssh-ed25519 -o ConnectTimeout=15'))
    checkout=ROOT/'checkout'
    with (ROOT/'sync.lock').open('a') as lock:
        try: fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError: return
        def git(*args):
            return subprocess.run(['git','-C',str(checkout),*args],check=True,env=env,text=True,capture_output=True,timeout=90)
        if not checkout.exists():
            subprocess.run(['git','clone','--branch','main',REPOSITORY,str(checkout)],check=True,env=env,timeout=90)
        if git('remote','get-url','origin').stdout.strip()!=REPOSITORY:
            raise RuntimeError('Unexpected synchronization repository')
        # This checkout is disposable generated publishing state, never a human worktree.
        # Regenerate from the latest remote head after interrupted pushes or concurrent edits.
        git('fetch','origin','main')
        git('reset','--hard','origin/main')
        userdir=Path('/var/lib/docker/volumes/warcraft-iii-online_pvpgn-test-state/_data/pvpgn/users')
        catalog_path=ROOT/'hero_names.json'
        catalog=json.loads(catalog_path.read_text(encoding='utf-8')) if catalog_path.exists() else {}
        result=export({key:ROOT.parent/'hostbot/dota-profiles'/key/'ghost.dbs' for key in MAPS},load_display_names(userdir),catalog)
        public=checkout/'docs/data/rankings.json'
        if not public.parent.is_dir(): raise RuntimeError('Public site is not ready')
        public.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        embedded=json.dumps(result,ensure_ascii=False).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
        files=['docs/data/rankings.json']
        for name in ('index.html','about.html'):
            path=checkout/'docs'/name
            before=path.read_text(encoding='utf-8')
            after,n=re.subn(r'(<script type="application/json" id="rankings-data">).*?(</script>)',lambda m:m[1]+embedded+m[2],before,flags=re.S)
            if n!=1: raise RuntimeError('Unexpected page template')
            path.write_text(after,encoding='utf-8')
            files.append('docs/'+name)
        git('add','--',*files)
        if not git('diff','--cached','--name-only').stdout.strip():
            print('PUBLIC_STATS_UNCHANGED');return
        git('-c','user.name=Warcraft statistics','-c','user.email=wc3-stats@users.noreply.github.com','commit','-m','Update public player statistics')
        git('push','origin','HEAD:main')
        print('PUBLIC_STATS_PUBLISHED', {key:len(pool['players']) for key,pool in result['pools'].items()})


if __name__=='__main__': main()
