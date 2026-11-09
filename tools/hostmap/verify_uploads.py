"""Run the dedicated upload probe and record live checks without restarting games."""
import json

from deploy import ROOT, PROJECT, inspect, python_in_image, run, same_before
from enable_uploads import DOMAIN


def main():
    same_before()
    before = json.loads((ROOT/'uploads-workers-before.json').read_text())
    result = json.loads(python_in_image('probe_upload.py',
        credentials=ROOT/'config/probe.json', uid=10003, gid=10005))
    result['broker_active'] = run('systemctl', 'is-active', 'warcraft-iii-hostmap-maps.service') == 'active'
    result['renewal_timer_active'] = run('systemctl', 'is-active', 'certbot.timer') == 'active'
    renewal = (__import__('pathlib').Path('/etc/letsencrypt/renewal')/(DOMAIN+'.conf')).read_text()
    if 'authenticator = webroot' not in renewal or '/usr/bin/systemctl reload nginx' not in renewal:
        raise RuntimeError('Certificate renewal settings are incomplete')
    result['renewal_webroot_and_reload'] = True
    run('nginx', '-t')
    for name, expected in before.items():
        value = inspect(PROJECT+'-'+name+'-1')
        observed = dict(id=value['Id'], pid=value['State']['Pid'], started=value['State']['StartedAt'])
        if observed != expected:
            raise RuntimeError('A game worker changed during upload checks')
    same_before()
    result['game_worker_restarts'] = 0
    result['permanent_services_unchanged'] = True
    if not result['broker_active'] or not result['renewal_timer_active']:
        raise RuntimeError('Upload or renewal service is not active')
    (ROOT/'upload-probe-verified.json').write_text(json.dumps(result, indent=2)+'\n')
    print('HOSTMAP_UPLOAD_END_TO_END_VERIFIED '+json.dumps(result))


if __name__ == '__main__':
    main()
