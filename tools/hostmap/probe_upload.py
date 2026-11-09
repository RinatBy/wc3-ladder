"""Exercise the live upload path with our dedicated ordinary account, never user secrets."""
import json
from pathlib import Path
import re
import socket
import time
from urllib.error import HTTPError
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen

from realm import Realm, chat_event

ORIGIN = 'https://maps.wc3.uplay2.ru/'


def post_map(token, path):
    request = Request(ORIGIN+'upload', data=path.read_bytes(), method='POST', headers={
        'Authorization': 'Bearer '+token,
        'X-Map-Name': quote('Echo Isles upload check.w3x'),
        'Content-Type': 'application/octet-stream'})
    with urlopen(request, timeout=45) as response:
        if response.status != 202:
            raise RuntimeError('Upload was not accepted')
        result = json.load(response)
    if not re.fullmatch('[a-f0-9]{32}', result.get('id', '')):
        raise RuntimeError('Invalid job identity')
    return result['id']


def main():
    paths = list(Path('/assets/maps').glob('7235147e923f*.w3x'))
    if len(paths) != 1:
        raise RuntimeError('Expected the already approved Echo Isles fixture')
    client = Realm(json.loads(Path('/credentials.json').read_text()))
    try:
        client.connect()
        client.whisper('HostMap', '!upload')
        token = None
        deadline = time.monotonic()+25
        while time.monotonic() < deadline:
            try:
                kind, body = client.receive()
            except socket.timeout:
                continue
            if kind == 0x25:
                client.send(kind, body)
            event = chat_event(body) if kind == 0x0f else None
            if event and event[0] == 4 and event[1].lower() == 'hostmap':
                value = urlsplit(event[2])
                if value.scheme == 'https' and value.netloc == 'maps.wc3.uplay2.ru' and value.path == '/' and not value.query and re.fullmatch('[A-Za-z0-9_-]{43}', value.fragment):
                    token = value.fragment
                    break
        if not token:
            raise RuntimeError('Ordinary account did not receive a valid personal link')
        job = post_map(token, paths[0])
        for invalid in (token, 'invalid'):
            try:
                post_map(invalid, paths[0])
            except HTTPError as error:
                status = error.code
                error.close()
                if status != 400:
                    raise RuntimeError('Unexpected invalid-token response')
            else:
                raise RuntimeError('An invalid or reused token was accepted')
        deadline = time.monotonic()+55
        while time.monotonic() < deadline:
            with urlopen(ORIGIN+'status?id='+job, timeout=5) as response:
                state = json.load(response)
            if state['state'] == 'ready':
                if state['code'] != '7235147e923f':
                    raise RuntimeError('Uploaded map identity changed')
                print(json.dumps(dict(ordinary_account=True, private_link=True,
                    https_verified=True, quarantine_to_native_validation=True,
                    published=True, code=state['code'], replay_rejected=True,
                    invalid_token_rejected=True)))
                return
            if state['state'] == 'rejected':
                raise RuntimeError('Known valid map was rejected by the validation queue')
            time.sleep(1)
        raise RuntimeError('Validation queue did not finish in time')
    finally:
        client.close()


if __name__ == '__main__':
    main()
