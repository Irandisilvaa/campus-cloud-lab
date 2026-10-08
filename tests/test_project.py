import base64
import importlib.util
import io
import json
from pathlib import Path
import tarfile
import threading
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import urlopen, Request
import yaml

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('portal', ROOT/'app/server.py')
portal = importlib.util.module_from_spec(spec); spec.loader.exec_module(portal)

class PortalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = portal.ThreadingHTTPServer(('127.0.0.1', 0), portal.Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start(); cls.url = f'http://127.0.0.1:{cls.server.server_port}'
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close(); cls.thread.join()
    def get(self, path):
        try:
            with urlopen(self.url+path, timeout=5) as response:
                return response.status, response.read(), response.headers
        except HTTPError as e: return e.code, e.read(), e.headers
    def test_health_contract(self):
        code, body, headers = self.get('/health')
        self.assertEqual(code,200); self.assertEqual(json.loads(body)['status'],'ok')
        self.assertEqual(headers['Cache-Control'],'no-store')
    def test_events_and_status(self):
        self.assertEqual(len(json.loads(self.get('/api/eventos')[1])['events']),3)
        self.assertIn('server',json.loads(self.get('/api/status')[1]))
    def test_assets(self):
        for path in ['/','/app.js','/style.css']:
            self.assertEqual(self.get(path)[0],200)
    def test_admin_is_inert_before_waf(self):
        self.assertEqual(self.get('/admin')[0],200)
    def test_no_arbitrary_file_serving(self):
        for path in ['/server.py','/../README.md','/.env','/%2e%2e/README.md']:
            self.assertEqual(self.get(path)[0],404)
    def test_dns_success_and_failure(self):
        original = portal.socket.getaddrinfo
        def resolve(host, *args, **kwargs):
            if host == portal.PRIVATE_NAME:
                return [(2,1,6,'',('10.0.11.10',8080))]
            return original(host, *args, **kwargs)
        with patch.object(portal.socket,'getaddrinfo',side_effect=resolve) as mock:
            code,body,_ = self.get('/api/dns?host=untrusted.example')
            self.assertEqual(code,200)
            self.assertEqual(json.loads(body)['addresses'],['10.0.11.10'])
            self.assertTrue(any(call.args[0] == 'app.campus.internal' for call in mock.call_args_list))
        def fail_private(host, *args, **kwargs):
            if host == portal.PRIVATE_NAME: raise portal.socket.gaierror()
            return original(host, *args, **kwargs)
        with patch.object(portal.socket,'getaddrinfo',side_effect=fail_private):
            self.assertEqual(self.get('/api/dns')[0],503)
    def test_head_and_post(self):
        with urlopen(Request(self.url+'/health',method='HEAD'),timeout=5) as response:
            self.assertEqual(response.read(),b''); self.assertGreater(int(response.headers['Content-Length']),0)
        with self.assertRaises(HTTPError) as error:
            urlopen(Request(self.url+'/admin',data=b'test',method='POST'),timeout=5)
        self.assertEqual(error.exception.code,501)

class InfrastructureTests(unittest.TestCase):
    def setUp(self):
        self.base = yaml.safe_load((ROOT/'infra/01-base.yaml').read_text())
        self.resources = self.base['Resources']
    def test_offline_payload_matches_source(self):
        for name, label in [('ServerA','A'),('ServerB','B')]:
            script = self.resources[name]['Properties']['UserData']['Fn::Base64']
            self.assertLessEqual(len(script.encode()),16384)
            self.assertIn(f'Environment="NODE_NAME=Servidor {label}"',script)
            encoded = script.split("| tar -xz -C /opt/campus\n")[1].split('\nCAMPUS_ARCHIVE')[0]
            with tarfile.open(fileobj=io.BytesIO(base64.b64decode(encoded)),mode='r:gz') as archive:
                self.assertEqual(sorted(archive.getnames()),['app.js','index.html','server.py','style.css'])
                for member in archive.getmembers():
                    self.assertEqual(archive.extractfile(member).read(),(ROOT/'app'/member.name).read_bytes())
    def test_private_network_invariants(self):
        kinds = [r['Type'] for r in self.resources.values()]
        self.assertNotIn('AWS::EC2::NatGateway',kinds)
        self.assertFalse(any(kind.startswith('AWS::IAM::') for kind in kinds))
        for name in ['PrivateA','PrivateB']:
            self.assertFalse(self.resources[name]['Properties']['MapPublicIpOnLaunch'])
            self.assertEqual(self.resources[name+'Association']['Properties']['RouteTableId'],{'Ref':'PrivateRoutes'})
        self.assertEqual(self.resources['AlbToApp']['Properties']['SourceSecurityGroupId'],{'Ref':'AlbSg'})
        self.assertEqual(self.resources['AlbToApp']['Properties']['FromPort'],8080)
    def test_templates_under_upload_limit(self):
        for path in (ROOT/'infra').glob('*.yaml'):
            self.assertLess(path.stat().st_size,51200)
            self.assertTrue(yaml.safe_load(path.read_text())['Resources'])
    def test_waf_preserves_health_check(self):
        waf = yaml.safe_load((ROOT/'infra/06-waf.yaml').read_text())
        props = waf['Resources']['WebAcl']['Properties']
        self.assertEqual(props['Scope'],'REGIONAL')
        self.assertIn('Allow',props['DefaultAction'])
        self.assertEqual(props['Rules'][0]['Statement']['ByteMatchStatement']['SearchString'],'/admin')

if __name__ == '__main__': unittest.main()
