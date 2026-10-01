# ABOUTME: Tests fixed memory relay transport with real local HTTP responses.
# ABOUTME: Checks response limits, refused redirects, and credential forwarding boundaries.
import http.server
import json
import threading
import unittest

import test_memory_service as service_fixture
from lifeos_hook_bridge.memory_service import MemoryConfiguration
from lifeos_hook_bridge.memory_http import RESPONSE_LIMIT, dashboard_base, installation_binding, relay


class MemoryHTTPTests(unittest.TestCase):
    def setUp(self):
        self.fixture=service_fixture.MemoryServiceTests();self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.configuration=MemoryConfiguration(self.fixture.config)
        self.seen=[]
        self.write_disconnects=[]
        self.extra_length=0
        self.status,self.payload,self.kind,self.headers=200,b'{}','application/json',{
            'X-LifeOS-Memory-Installation':installation_binding(self.configuration.load(),self.configuration.path)}
        test=self
        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                test.seen.append({'path':self.path,'authorization':self.headers.get('Authorization'),
                                  'cookie':self.headers.get('Cookie')})
                self.send_response(test.status)
                self.send_header('Content-Type',test.kind)
                for key,value in test.headers.items():self.send_header(key,value)
                self.send_header('Content-Length',str(len(test.payload)+test.extra_length))
                self.end_headers()
                try:
                    self.wfile.write(test.payload)
                except (ConnectionResetError, BrokenPipeError) as error:
                    test.write_disconnects.append({'error': type(error).__name__, 'bytes': len(test.payload)})
            def log_message(self,*args):pass
        self.server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.addCleanup(self.stop)
        self.base=f'http://127.0.0.1:{self.server.server_port}'
        self.configuration.update(lambda config:config.update(pulse_http={'dashboard_base_url':self.base+'/hermes'}))

    def stop(self):
        self.server.shutdown();self.server.server_close();self.thread.join(timeout=5)
        self.assertFalse(self.thread.is_alive())
        for disconnect in self.write_disconnects:
            self.assertGreater(disconnect['bytes'], RESPONSE_LIMIT, disconnect)
            self.assertIn(disconnect['error'], ('ConnectionResetError', 'BrokenPipeError'))

    def call(self,**kwargs):
        return relay(self.configuration,dict(view='state',authorization='Bearer synthetic',cookie='',**kwargs))

    def test_fixed_prefix_and_supported_session_credentials_only(self):
        result=relay(self.configuration,{'view':'state','authorization':'Bearer synthetic',
            'cookie':'unrelated=private; hermes_session_at=synthetic-at; __Secure-hermes_session_rt=synthetic-rt'})
        self.assertEqual(result['status'],200)
        self.assertEqual(self.seen,[{'path':'/hermes/api/plugins/lifeos-hook-bridge/memory/pulse/state',
            'authorization':'Bearer synthetic','cookie':'hermes_session_at=synthetic-at; __Secure-hermes_session_rt=synthetic-rt'}])
        self.assertEqual(dict(result['headers'])['cache-control'],'no-store')

    def test_knowledge_reads_use_the_fixed_local_route_and_current_binding_for_not_found(self):
        arguments = {'view':'knowledge', 'authorization':'Bearer synthetic', 'cookie':'',
                     'target':'/api/knowledge/Research/synthetic-note'}
        self.assertEqual(relay(self.configuration, arguments)['status'], 200)
        self.assertEqual(self.seen[-1]['path'],
            '/hermes/api/plugins/lifeos-hook-bridge/memory/knowledge?target=%2Fapi%2Fknowledge%2Fresearch%2Fsynthetic-note')
        self.status = 404
        self.assertEqual(relay(self.configuration, arguments)['status'], 404)
        self.headers['X-LifeOS-Memory-Installation'] = 'foreign-installation'
        self.assertEqual(relay(self.configuration, arguments)['status'], 503)

    def test_redirect_does_not_receive_forwarded_credentials(self):
        self.status=302;self.headers={'Location':self.base+'/unexpected'}
        self.assertEqual(self.call()['status'],503)
        self.assertEqual(len(self.seen),1)

    def test_invalid_content_and_oversized_response_refuse(self):
        for kind,payload in [('text/html',b'<html>private</html>'),('application/json',b'not-json'),
                             ('application/json',b'"unexpected scalar"'),
                             ('application/json',b' '*(RESPONSE_LIMIT+1))]:
            with self.subTest(kind=kind,size=len(payload)):
                self.kind,self.payload=kind,payload
                self.assertEqual(self.call()['status'],503)

    def test_no_credentials_or_invalid_arguments_never_contact_backend(self):
        for arguments in ({'view':'state','authorization':'','cookie':'unrelated=private'},
                          {'view':'state','authorization':'Bearer synthetic\r\nX-owner:yes','cookie':''},
                          {'view':'state','authorization':'Bearer synthetic','cookie':'','url':self.base}):
            with self.subTest(keys=sorted(arguments)):
                self.assertIn(relay(self.configuration,arguments)['status'],(400,401))
        self.assertEqual(self.seen,[])

    def test_destination_is_literal_loopback_and_has_no_redirect_inputs(self):
        for url in ('http://localhost:80','https://public.invalid:443','http://192.168.8.212:8080',
                    'http://127.0.0.1','http://user@127.0.0.1:80','http://127.0.0.1:80?next=other',
                    'http://127.0.0.1:80#private','http://127.0.0.1:80/../other'):
            with self.subTest(url=url),self.assertRaises(ValueError):dashboard_base(url)
        self.assertEqual(dashboard_base('http://[::1]:8080/hermes/'),'http://[::1]:8080/hermes')

    def test_upstream_server_failures_are_sanitized(self):
        for status in (404,500,503):
            with self.subTest(status=status):
                self.status=status;self.payload=json.dumps({'error':str(self.fixture.fixture.home)}).encode()
                result=self.call();self.assertEqual(result['status'],503)
                self.assertNotIn(str(self.fixture.fixture.home),result['body'])

    def test_wrong_local_installation_cannot_supply_a_successful_snapshot(self):
        self.headers['X-LifeOS-Memory-Installation']='other-installation'
        self.assertEqual(self.call()['status'],503)

    def test_incomplete_http_body_returns_unavailable(self):
        self.extra_length=100
        self.assertEqual(self.call()['status'],503)

    def test_login_link_uses_configured_browser_address_instead_of_loopback(self):
        self.configuration.update(lambda config:config['pulse_http'].update(
            dashboard_browser_url='https://hermes.example.test/hermes'))
        self.status=401;self.payload=b'{"login_url":"https://untrusted.invalid/login"}'
        result=self.call()
        self.assertEqual(result['status'],401)
        self.assertEqual(json.loads(result['body'])['login_url'],'https://hermes.example.test/hermes/login')

    def test_wiki_reads_use_the_fixed_local_route_with_one_encoded_target(self):
        result = relay(self.configuration, {'view': 'wiki', 'target': '/api/wiki/search?q=synthetic+words&limit=5',
            'authorization': 'Bearer synthetic', 'cookie': ''})
        self.assertEqual(result['status'], 200)
        self.assertEqual(self.seen[0]['path'], '/hermes/api/plugins/lifeos-hook-bridge/memory/wiki?'
            'target=%2Fapi%2Fwiki%2Fsearch%3Fq%3Dsynthetic%2Bwords%26limit%3D5')

    def test_invalid_wiki_targets_never_receive_forwarded_credentials(self):
        for target, status in [('https://other.invalid/api/wiki', 400), ('//other.invalid/api/wiki', 400),
                ('/api/wiki/reindex', 404), ('/api/wiki/skills', 404),
                ('/api/wiki/doc/%2e%2e', 400), ('/api/wiki/doc/name%2Fother', 400),
                ('/api/wiki/doc/name%252Fother', 400), ('/api/wiki/doc/%FF', 400),
                ('/api/wiki/doc/%00', 400), ('/api/wiki?owner=other', 400),
                ('/api/wiki/search?q=one&q=two', 400), ('/api/wiki/search?q=one&root=other', 400),
                ('/api/wiki/search?q=one&limit=0', 400), ('/api/wiki/search?q=' + 'x' * 1025, 400)]:
            with self.subTest(target=target[:80]):
                result = relay(self.configuration, {'view': 'wiki', 'target': target,
                    'authorization': 'Bearer synthetic', 'cookie': ''})
                self.assertEqual(result['status'], status)
        self.assertEqual(self.seen, [])

    def test_wiki_not_found_responses_require_the_current_installation_binding(self):
        self.status = 404
        self.payload = b'{"error":"Native page not found"}'
        arguments = {'view': 'wiki', 'target': '/api/wiki/doc/missing',
            'authorization': 'Bearer synthetic', 'cookie': ''}
        self.assertEqual(relay(self.configuration, arguments)['status'], 404)
        self.headers['X-LifeOS-Memory-Installation'] = 'another-installation'
        self.assertEqual(relay(self.configuration, arguments)['status'], 503)


if __name__=='__main__':unittest.main()
