"""Smoke test remoto sem credenciais AWS; usa apenas GET no portal do grupo."""
import argparse
import json
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import urlopen

parser = argparse.ArgumentParser()
parser.add_argument('url')
parser.add_argument('--admin-status', type=int, choices=[200,403], default=200)
args = parser.parse_args()
base = args.url.rstrip('/')
if urlsplit(base).scheme not in ('http','https'):
    parser.error('Informe URL HTTP(S) completa do seu portal.')
def get(path):
    try:
        with urlopen(base+path, timeout=15) as response:
            return response.status, response.read()
    except HTTPError as error:
        return error.code, error.read()
status, body = get('/health')
assert status == 200 and json.loads(body)['status'] == 'ok', (status, body)
status, body = get('/api/eventos')
assert status == 200 and len(json.loads(body)['events']) == 3, (status,body)
servers = set()
for _ in range(8):
    status, body = get('/api/status')
    assert status == 200, (status, body)
    servers.add(json.loads(body)['server'])
status, body = get('/admin')
assert status == args.admin_status, f'/admin retornou {status}; esperado {args.admin_status}'
print('OK: saúde, eventos e /admin. Servidores observados:', ', '.join(sorted(servers)))
print('Observar apenas um servidor não prova falha do outro; confira o target group.')
