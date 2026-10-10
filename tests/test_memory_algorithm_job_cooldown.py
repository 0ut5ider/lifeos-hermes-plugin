# ABOUTME: Exercises Algorithm failure cooldown against a real refusing inference listener.
# ABOUTME: Confirms unchanged-source backoff, explicit retries, and changed-source retries without fabricated model output.
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import threading
import shutil
import time
import unittest
import httpx
from lifeos_hook_bridge.memory_context import route_identity
import test_memory_algorithm_jobs as fixture


class MemoryAlgorithmCooldownTests(unittest.TestCase):
    native_module = 'algorithm-tab.ts'
    status_route = '/api/algorithm-tab'
    module_configuration_name = 'algorithm'
    create_fixture = fixture.MemoryAlgorithmJobRelayTests.create_fixture
    native_module_name = fixture.MemoryAlgorithmJobRelayTests.native_module_name
    stop_dashboard = fixture.MemoryAlgorithmJobRelayTests.stop_dashboard
    stop_pulse = fixture.MemoryAlgorithmJobRelayTests.stop_pulse
    login = fixture.MemoryAlgorithmJobRelayTests.login
    launch_lifetime_process = fixture.MemoryAlgorithmJobRelayTests.launch_lifetime_process

    def setUp(self):
        fixture.MemoryAlgorithmJobRelayTests.setUp(self)
        # This fixture deliberately contains a small synthetic chain.
        for path in (self.root / 'hooks').iterdir():
            if path.is_file(): path.unlink()
        (self.root / 'hooks/LoadMemory.hook.ts').write_text('// ABOUTME: Synthetic test source.\n// ABOUTME: Supplies a bounded Algorithm fixture.\nexport {};\n')
        self.requests = []
        requests = self.requests
        class RefusingGateway(BaseHTTPRequestHandler):
            def do_POST(self):
                requests.append(json.loads(self.rfile.read(int(self.headers['Content-Length']))))
                self.send_response(401)
                self.send_header('Content-Length', '0')
                self.end_headers()
            def log_message(self, *_): pass
        gateway = ThreadingHTTPServer(('127.0.0.1', 0), RefusingGateway)
        threading.Thread(target=gateway.serve_forever, daemon=True).start()
        self.addCleanup(gateway.server_close)
        self.addCleanup(gateway.shutdown)
        route = {'provider':'lifeos-local-gateway','model':'synthetic-flashnext',
            'base_url':f'http://127.0.0.1:{gateway.server_port}', 'api_mode':'anthropic'}
        self.fixture.configuration.update(lambda value: value['destinations']['terminal:' + str(self.fixture.profile)]['model_routes'].append(route_identity(**route)))
        environment = self.fixture.home / 'algorithm-refusing-model.env'
        environment.write_text('ANTHROPIC_BASE_URL=' + route['base_url'] + '\nANTHROPIC_AUTH_TOKEN=synthetic-token\nLIFEOS_CHILD_INFERENCE_DIRECT=1\n'
            + "LIFEOS_MODEL_TIER_MAP='" + json.dumps({'pin':'none','haiku':{'model':route['model'],'effort':'low'},'opus':{'model':route['model'],'effort':'xhigh'}}) + "'\n")
        environment.chmod(0o600)
        self.launch_lifetime_process(environment, daemon=False)

    def settled(self, client):
        deadline = time.monotonic() + 150
        while time.monotonic() < deadline:
            result = client.get(self.native + '/api/algorithm-tab')
            self.assertEqual(result.status_code, 200, result.text)
            if not result.json()['generating']: return result
            time.sleep(0.2)
        self.fail('The actual refused Algorithm job does not settle')

    def test_failed_native_hash_backs_off_force_retries_and_source_change_retries(self):
        with httpx.Client(timeout=45) as client:
            self.login(client)
            started = client.get(self.native + '/api/algorithm-tab')
            self.assertEqual(started.status_code, 200, started.text)
            self.assertTrue(started.json()['generating'])
            self.settled(client)
            first = len(self.requests)
            self.assertGreater(first, 1)
            for _ in range(2):
                result = client.get(self.native + '/api/algorithm-tab')
                self.assertEqual(result.status_code, 200, result.text)
                self.assertFalse(result.json()['generating'])
            self.assertEqual(len(self.requests), first)
            forced = client.post(self.native + '/api/algorithm-tab/summary/regenerate')
            self.assertEqual((forced.status_code, forced.json()), (202, {'ok':True,'started':True}))
            self.settled(client)
            self.assertEqual(len(self.requests), 2 * first)
            source = self.root / 'LIFEOS/ALGORITHM/v3.2.1.md'
            source.write_text(source.read_text() + '\nSynthetic changed source.\n')
            changed = client.get(self.native + '/api/algorithm-tab')
            self.assertEqual(changed.status_code, 200, changed.text)
            self.assertTrue(changed.json()['generating'])
            self.settled(client)
            self.assertEqual(len(self.requests), 3 * first)
        self.assertFalse((self.root / 'LIFEOS/MEMORY/STATE/algorithm-tab-summary.json').exists())

    def test_real_completed_cache_skips_model_requests_and_preserves_bytes(self):
        source = Path(os.environ['LIFEOS_MEMORY_SOURCE'])
        shutil.copytree(source / 'hooks', self.root / 'hooks', dirs_exist_ok=True)
        record = json.loads((Path(__file__).parents[1] / 'docs/verification/2026-10-08-remaining-reader-audit/algorithm-job-private-model.json').read_text())
        self.assertEqual(record['status'], 'PASS')
        cache = self.root / 'LIFEOS/MEMORY/STATE/algorithm-tab-summary.json'
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps({'files':record['cards'], 'overview':record['overview']}))
        cache.chmod(0o600)
        before = (cache.read_bytes(), cache.stat().st_ino, cache.stat().st_mtime_ns)
        profile = self.fixture.profile
        receipt = profile / 'actual-summary-cache-reuse.json'
        with (profile / 'plugins/lifeos-hook-bridge/memory_owner_jobs.py').open('a') as stream:
            stream.write('\n_original_run=OwnerJobs.run\ndef _observed_run(*args,**kwargs):\n'
                '    result=_original_run(*args,**kwargs)\n'
                '    Path(' + repr(str(receipt)) + ').write_text(json.dumps(result))\n'
                '    return result\nOwnerJobs.run=_observed_run\n')
        with httpx.Client(timeout=45) as client:
            self.login(client)
            plan = client.post(self.dashboard + '/api/plugins/lifeos-hook-bridge/memory/algorithm_job')
            self.assertEqual(plan.status_code, 200, plan.text)
            self.assertEqual(plan.json()['chain_hash'], record['overview']['chain_hash'])
            started = client.get(self.native + '/api/algorithm-tab')
            self.assertEqual(started.status_code, 200, started.text)
            deadline = time.monotonic() + 90
            while not receipt.exists() and time.monotonic() < deadline: time.sleep(0.1)
        self.assertTrue(receipt.exists(), 'The real selected cache-reuse job does not finish')
        outcome = json.loads(receipt.read_text())
        self.assertEqual(outcome['status'], 'completed', outcome)
        result = json.loads(outcome['output'].strip())
        self.assertEqual(result, {'hash':record['overview']['chain_hash'], 'generated':0, 'failed':False})
        self.assertEqual(self.requests, [])
        self.assertEqual((cache.read_bytes(),cache.stat().st_ino,cache.stat().st_mtime_ns), before)
