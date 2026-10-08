# ABOUTME: Tests native PULSE requests against actual authenticated Hermes HTTP routes.
# ABOUTME: Uses separate localhost listeners and disposable native memory profiles.
import json
import os
from pathlib import Path
import select
import socket
import subprocess
import threading
import time
import unittest

import httpx
import uvicorn

import test_memory_pulse_auth as auth_fixture
from test_memory_native import OWNER


class MemoryPulseRelayTests(unittest.TestCase):
    def setUp(self):
        self.fixture = self.create_fixture()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.listener = socket.socket()
        self.listener.bind(('127.0.0.1', 0))
        self.dashboard = f'http://127.0.0.1:{self.listener.getsockname()[1]}'
        self.server = uvicorn.Server(uvicorn.Config(self.fixture.app, log_level='error', lifespan='off'))
        self.thread = threading.Thread(target=self.server.run, kwargs={'sockets': [self.listener]}, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop_dashboard)
        deadline = time.monotonic() + 10
        while not self.server.started:
            if not self.thread.is_alive() or time.monotonic() > deadline:
                self.fail('The disposable authenticated dashboard did not start')
            time.sleep(0.01)
        self.fixture.configuration.update(lambda config:config.update(pulse_http={'dashboard_base_url':self.dashboard,'dashboard_browser_url':self.dashboard}))
        self.root = self.fixture.fixture.root
        connector=self.root/'LIFEOS/USER/CONFIG/memory-access.json'
        configuration=json.loads(connector.read_text())
        configuration['command'][-1]=str(self.fixture.configuration.path)
        connector.write_text(json.dumps(configuration))
        self.marker = self.root / 'LIFEOS/USER/CONFIG/memory-http.json'
        self.marker.write_text(json.dumps({'version':1,'managed':True}))
        self.marker.chmod(0o600)
        directory = 'Observability' if self.native_module_name() == 'observability.ts' else 'modules'
        module = self.root/'LIFEOS/PULSE'/directory/getattr(self, 'native_module', 'memory.ts')
        program = self.fixture.home/'pulse-relay.ts'
        exports, handler, start = {
            'wiki.ts': ('startWiki,stopWiki,handleWikiRequest', 'handleWikiRequest', 'startWiki();\n'),
            'observability.ts': ('startObservability,handleObservabilityRequest', 'handleObservabilityRequest',
                                 'startObservability({enabled:true});\n'),
            'memory.ts': ('handleRequest', 'handleRequest', ''),
            'hypotheses.ts': ('handleRequest', 'handleRequest', ''),
            'upgrades.ts': ('handleRequest', 'handleRequest', ''),
            'hermes.ts': ('handleRequest', 'handleRequest', ''),
        }[self.native_module_name()]
        program.write_text('import {'+exports+'} from '+json.dumps(str(module))+';\n'+start+
            'const server=Bun.serve({hostname:"127.0.0.1",port:0,async fetch(request){\n'
            'return await '+handler+'(request,new URL(request.url).pathname) ?? new Response("not found",{status:404});}});\n'
            'console.log(server.port);\n')
        environment = dict(os.environ, HOME=str(self.fixture.home), BUN_CONFIG_NO_AUTO_INSTALL='1',
                           LIFEOS_MEMORY_INTERNAL='1', LIFEOS_MEMORY_CONTEXT=json.dumps({'author':'100','principal':'owner'}))
        self.process = subprocess.Popen(['bun','--no-install',str(program)],env=environment,
                                        stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        self.addCleanup(self.stop_pulse)
        self.assertTrue(select.select([self.process.stdout],[],[],10)[0], 'Native listener did not start')
        self.native = f'http://127.0.0.1:{int(self.process.stdout.readline())}'

    def native_module_name(self):
        return getattr(self, 'native_module', 'memory.ts')

    def create_fixture(self):
        return auth_fixture.MemoryPulseAuthTests()

    def stop_dashboard(self):
        self.server.should_exit = True
        self.thread.join(timeout=10)
        self.listener.close()
        self.assertFalse(self.thread.is_alive(), 'Disposable dashboard did not stop')

    def stop_pulse(self):
        self.process.terminate()
        _, error = self.process.communicate(timeout=10)
        self.assertEqual(error, '', error)

    def login(self, client):
        result = client.post(self.dashboard+'/auth/password-login',json={'provider':'basic',
            'username':'synthetic-owner','password':'synthetic-password'})
        self.assertEqual(result.status_code,200,result.text)

    def test_ambient_owner_and_internal_flags_cannot_authorize_native_http(self):
        for path in ('','/state','/health','/runs'):
            with self.subTest(path=path):
                response=httpx.get(self.native+'/api/memory'+path,headers={'X-LifeOS-Owner':'owner'})
                self.assertEqual(response.status_code,401,response.text)
                self.assertEqual(response.headers.get('cache-control'),'no-store')
                self.assertNotIn('Synthetic authenticated PULSE fact',response.text)

    def test_request_cookies_preserve_governed_owner_views_and_current_revocation(self):
        with httpx.Client() as client:
            self.login(client)
            for path in ('','/state','/health','/runs'):
                with self.subTest(path=path):
                    response=client.get(self.native+'/api/memory'+path)
                    self.assertEqual(response.status_code,200,response.text)
                    self.assertEqual(response.headers.get('cache-control'),'no-store')
                    self.assertNotIn('etag',response.headers)
            snapshot=client.get(self.native+'/api/memory').json()
            self.assertEqual(snapshot['principalMemory']['entries'],['RULE: Synthetic authenticated PULSE fact'])
            memory=self.fixture.fixture.fixture.fixture.fixture.memory
            reference=memory.recall(OWNER,'Synthetic authenticated PULSE fact')[0]['reference']
            self.assertEqual(memory.forget(OWNER,reference,'relay-forget')['status'],'committed')
            self.assertEqual(client.get(self.native+'/api/memory').json()['principalMemory']['entries'],[])
            self.fixture.configuration.update(lambda config:config['accounts'].pop('dashboard:basic:synthetic-owner'))
            response=client.get(self.native+'/api/memory')
            self.assertEqual(response.status_code,403,response.text)

    def test_missing_connector_stays_managed_and_never_reads_raw_memory(self):
        with httpx.Client() as client:
            self.login(client)
            (self.root/'LIFEOS/USER/CONFIG/memory-access.json').unlink()
            response=client.get(self.native+'/api/memory')
            self.assertEqual(response.status_code,503,response.text)
            self.assertNotIn('Synthetic authenticated PULSE fact',response.text)

    def test_nonread_query_and_unsupported_native_memory_routes_refuse(self):
        with httpx.Client() as client:
            self.login(client)
            for method,path,status in [('POST','/api/memory',405),('GET','/api/memory?owner=other',400),
                                       ('GET','/api/memory/unsupported',404)]:
                with self.subTest(method=method,path=path):
                    response=client.request(method,self.native+path)
                    self.assertEqual(response.status_code,status,response.text)
                    self.assertEqual(response.headers.get('cache-control'),'no-store')
                    self.assertNotIn('Synthetic authenticated PULSE fact',response.text)

    def test_invalid_bearer_does_not_borrow_valid_cookies_and_logout_stops_reads(self):
        with httpx.Client() as client:
            self.login(client)
            response=client.get(self.native+'/api/memory',headers={'Authorization':'Bearer invalid-synthetic-token'})
            self.assertEqual(response.status_code,401,response.text)
            self.assertNotIn('Synthetic authenticated PULSE fact',response.text)
            self.assertEqual(client.get(self.native+'/api/memory').status_code,200)
            client.post(self.dashboard+'/auth/logout',follow_redirects=False)
            self.assertEqual(client.get(self.native+'/api/memory').status_code,401)

    def test_cross_origin_read_and_unavailable_configuration_refuse(self):
        with httpx.Client() as client:
            self.login(client)
            response=client.get(self.native+'/api/memory',headers={'Origin':'https://untrusted.invalid'})
            self.assertEqual(response.status_code,403,response.text)
            self.fixture.configuration.path.chmod(0o644)
            response=client.get(self.native+'/api/memory')
            self.assertEqual(response.status_code,503,response.text)
            self.assertNotIn('Synthetic authenticated PULSE fact',response.text)

    def test_invalid_view_and_missing_configuration_return_sanitized_http_envelopes(self):
        from lifeos_hook_bridge.memory_http import relay
        for view in ([],{},None,4):
            with self.subTest(view=view):
                result=relay(self.fixture.configuration,{'view':view,'authorization':'','cookie':''})
                self.assertEqual(result['status'],400)
        self.fixture.configuration.path.unlink()
        result=relay(self.fixture.configuration,{'view':'state','authorization':'Bearer synthetic','cookie':''})
        self.assertEqual(result['status'],503)
        self.assertNotIn(str(self.fixture.home),result['body'])

    def test_changed_installation_binding_refuses_on_the_existing_connection(self):
        with httpx.Client() as client:
            self.login(client)
            self.assertEqual(client.get(self.native+'/api/memory').status_code,200)
            self.fixture.configuration.update(lambda config:config.update(root=str(self.fixture.home/'other-root')))
            response=client.get(self.native+'/api/memory')
            self.assertEqual(response.status_code,503,response.text)
            self.assertNotIn('Synthetic authenticated PULSE fact',response.text)

    def test_owner_and_anonymous_requests_do_not_share_authority(self):
        from concurrent.futures import ThreadPoolExecutor
        with httpx.Client() as owner,httpx.Client() as anonymous,ThreadPoolExecutor(max_workers=2) as pool:
            self.login(owner)
            results=list(pool.map(lambda client:client.get(self.native+'/api/memory'),[owner,anonymous]))
            self.assertEqual([response.status_code for response in results],[200,401])
            self.assertNotIn('Synthetic authenticated PULSE fact',results[1].text)

    def test_backend_shutdown_never_selects_raw_reader(self):
        with httpx.Client() as client:
            self.login(client)
            self.server.should_exit=True
            self.thread.join(timeout=10)
            response=client.get(self.native+'/api/memory')
            self.assertEqual(response.status_code,503,response.text)
            self.assertNotIn('Synthetic authenticated PULSE fact',response.text)

    def test_managed_marker_survives_restart_after_connector_loss(self):
        import subprocess
        (self.root/'LIFEOS/USER/CONFIG/memory-access.json').unlink()
        program='import {handleRequest} from '+json.dumps(str(self.root/'LIFEOS/PULSE/modules/memory.ts'))+';\n' \
            +'const response=await handleRequest(new Request("http://localhost/api/memory"),"/api/memory");\n' \
            +'console.log(JSON.stringify({status:response?.status,body:await response?.text()}));'
        process=subprocess.run(['bun','--no-install','-e',program],env=dict(os.environ,HOME=str(self.fixture.home)),
                               capture_output=True,text=True,timeout=10)
        self.assertEqual(process.returncode,0,process.stderr)
        self.assertEqual(process.stderr,'')
        result=json.loads(process.stdout)
        self.assertEqual(result['status'],503,result)
        self.assertNotIn('Synthetic authenticated PULSE fact',result['body'])

    def test_unmanaged_native_http_preserves_snapshot_fields(self):
        (self.root/'LIFEOS/USER/CONFIG/memory-access.json').unlink()
        self.marker.unlink()
        program='import {handleRequest,readMemoryView} from '+json.dumps(str(self.root/'LIFEOS/PULSE/modules/memory.ts'))+';\n' \
            +'const response=await handleRequest(new Request("http://localhost/api/memory"),"/api/memory");\n' \
            +'const http=await response?.json(),native=readMemoryView("snapshot"); delete http.ts; delete native.ts;\n' \
            +'console.log(JSON.stringify({status:response?.status,http,native}));'
        process=subprocess.run(['bun','--no-install','-e',program],env=dict(os.environ,HOME=str(self.fixture.home)),
                               capture_output=True,text=True,timeout=10)
        self.assertEqual(process.returncode,0,process.stderr)
        self.assertEqual(process.stderr,'')
        result=json.loads(process.stdout)
        self.assertEqual(result['status'],200,result)
        self.assertEqual(result['http'],result['native'])
        self.assertEqual(result['http']['principalMemory']['entries'],['RULE: Synthetic authenticated PULSE fact'])


if __name__ == '__main__':
    unittest.main()
