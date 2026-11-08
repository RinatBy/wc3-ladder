"""Create/login only the named service accounts, never reset existing passwords."""
import json
from pathlib import Path
import sys
from realm import Realm


def main():
    path=Path(sys.argv[1])
    credentials=json.loads(path.read_text())
    if credentials['account'] not in ('HostMap','HostMap1','HostMap2','HostMapProbe'):
        raise ValueError('Unexpected service account')
    client=Realm(credentials)
    try:
        try:
            client.connect()
        except ValueError as error:
            if str(error)!='Bot login rejected': raise
            client.connect(create=True)
            client.connect()
        print('HOSTMAP_SERVICE_ACCOUNT_VERIFIED',credentials['account'])
    finally:
        client.close()


if __name__=='__main__': main()
