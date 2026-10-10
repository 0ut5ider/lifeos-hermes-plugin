# ABOUTME: Checks actual native Performance HTTP aggregates under current owner authority.
# ABOUTME: Preserves complete permitted log counts while excluding private and retired event text.
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import select
import subprocess
import sys
import time
import unittest

import httpx
import test_memory_pulse_relay as relay_fixture
from test_memory_native import OWNER


ROUTES = ('/api/performance/cost', '/api/performance/failures', '/api/performance/summary',
          '/api/performance/anthropic-cost')
PREFIX = 'LIFEOS/MEMORY/OBSERVABILITY/'


class MemoryPerformanceTests(unittest.TestCase):
    create_fixture = relay_fixture.MemoryPulseRelayTests.create_fixture
    native_module_name = relay_fixture.MemoryPulseRelayTests.native_module_name
    stop_dashboard = relay_fixture.MemoryPulseRelayTests.stop_dashboard
    stop_pulse = relay_fixture.MemoryPulseRelayTests.stop_pulse
    login = relay_fixture.MemoryPulseRelayTests.login

    def setUp(self):
        relay_fixture.MemoryPulseRelayTests.setUp(self)
        self.stop_pulse()
        module = self.root / 'LIFEOS/PULSE/Performance/module.ts'
        program = self.fixture.home / 'performance-relay.ts'
        program.write_text('import {startPerformance,handlePerformanceRequest} from ' + json.dumps(str(module)) + ';\n'
            'import {memoryHTTPServerOptions} from ' + json.dumps(str(self.root / 'LIFEOS/TOOLS/lib/MemoryAccess.ts')) + ';\n'
            'startPerformance({enabled:true});\nconst server=Bun.serve({hostname:"127.0.0.1",port:0,...memoryHTTPServerOptions(),async fetch(request){\n'
            'return await handlePerformanceRequest(request) ?? new Response("not found",{status:404});}});\nconsole.log(server.port);\n')
        self.process = subprocess.Popen(['bun', '--no-install', str(program)], stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, env=dict(os.environ, HOME=str(self.fixture.home),
                LIFEOS_MEMORY_INTERNAL='1', LIFEOS_MEMORY_CONTEXT=json.dumps({'author': '100', 'principal': 'owner'})))
        self.assertTrue(select.select([self.process.stdout], [], [], 10)[0])
        self.native = f'http://127.0.0.1:{int(self.process.stdout.readline())}'

    def seed(self, marker='SyntheticPerformanceCurrent', *, count=1):
        timestamp = (datetime.now(timezone.utc) - timedelta(minutes=2)).isoformat()
        session = {'sessionId': 'synthetic-session', 'project': marker, 'primaryModel': 'SyntheticFlashNext',
            'messageCount': 2, 'costTotal': 1.25, 'totalTokens': 100, 'firstTimestamp': timestamp,
            'lastTimestamp': timestamp, 'costInput': 0.5, 'costOutput': 0.75, 'costCacheWrite': 0, 'costCacheRead': 0}
        sources = {'session-costs.jsonl': ''.join(json.dumps(dict(session, sessionId='synthetic-' + str(i))) + '\n'
            for i in range(count)),
            'tool-failures.jsonl': json.dumps({'timestamp': timestamp, 'tool_name': marker, 'detail': marker}) + '\n',
            'tool-activity.jsonl': json.dumps({'timestamp': timestamp, 'tool_name': marker, 'tool_input_preview': marker}) + '\n'}
        for name, text in sources.items():
            path = self.root / PREFIX / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
        return sources

    def original(self, target):
        control = Path(os.environ['LIFEOS_HARVEST_CONTROL_SOURCE'])
        script = ('import {startPerformance,handlePerformanceRequest} from '
            + json.dumps(str(control / 'LIFEOS/PULSE/Performance/module.ts'))
            + ';startPerformance({enabled:true});const response=await handlePerformanceRequest(new Request("http://localhost"+'
            + json.dumps(target) + '));console.log(await response.text());')
        result = subprocess.run(['bun', '--no-install', '-e', script], capture_output=True, text=True,
            timeout=30, env=dict(os.environ, HOME=str(self.fixture.home)))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        return json.loads(result.stdout)

    def test_original_native_fields_and_absent_logs_characterization(self):
        self.seed()
        self.assertEqual(self.original(ROUTES[0])['totalSessions'], 1)
        self.assertEqual(self.original(ROUTES[0])['totalCost'], 1.25)
        self.assertEqual(self.original(ROUTES[1])['totalFailures'], 1)
        self.assertEqual(self.original(ROUTES[2])['totalSessions'], 1)
        self.assertEqual(self.original(ROUTES[3]), {'current': None, 'history': [], 'total_entries': 0,
            'sites': [], 'baseline_updated': None})
        for name in self.seed(): (self.root / PREFIX / name).unlink()
        self.assertEqual(self.original(ROUTES[0])['totalSessions'], 0)
        self.assertEqual(self.original(ROUTES[1])['totalFailures'], 0)
        self.assertEqual(self.original(ROUTES[2])['totalSessions'], 0)

    def test_native_non_object_log_rows_characterization(self):
        # The native summary counts truthy scalar and array rows as sessions, even without session fields.
        self.seed()
        path = self.root / PREFIX / 'session-costs.jsonl'
        with path.open('a') as stream:
            for value in (True, [], 'synthetic scalar', 0, None, False, ''):
                stream.write(json.dumps(value) + '\n')
        self.assertEqual(self.original(ROUTES[0])['totalSessions'], 1)
        self.assertEqual(self.original(ROUTES[2])['totalSessions'], 4)

    def test_admitted_non_object_rows_preserve_native_summary_behavior(self):
        self.seed()
        path = self.root / PREFIX / 'session-costs.jsonl'
        with path.open('a') as stream:
            for value in (True, [], 'synthetic scalar', 0, None, False, ''):
                stream.write(json.dumps(value) + '\n')
        with httpx.Client(timeout=30) as client:
            self.login(client)
            response = client.get(self.native + ROUTES[2])
            self.assertEqual(response.status_code, 200, response.text[:300])
            self.assertEqual(response.json(), self.original(ROUTES[2]))
            self.assertEqual(response.headers.get('cache-control'), 'no-store')

    def test_anonymous_and_ambient_flags_cannot_read_counts_or_labels(self):
        self.seed()
        for route in ROUTES:
            with self.subTest(route=route):
                response = httpx.get(self.native + route, headers={'X-LifeOS-Owner': 'owner'})
                self.assertEqual(response.status_code, 401, response.text[:300])
                self.assertEqual(response.headers.get('cache-control'), 'no-store')
                self.assertNotIn('SyntheticPerformanceCurrent', response.text)

    def test_owner_fields_and_day_selectors_match_actual_native_aggregates(self):
        sources = self.seed()
        before = [(self.root / PREFIX / name).read_bytes() for name in sources]
        with httpx.Client(timeout=30) as client:
            self.login(client)
            for route in (*ROUTES, *(ROUTES[0] + '?days=' + str(days) for days in (7, 30, 90))):
                with self.subTest(route=route):
                    response = client.get(self.native + route)
                    self.assertEqual(response.status_code, 200, response.text[:300])
                    self.assertEqual(response.json(), self.original(route))
                    self.assertEqual(response.headers.get('cache-control'), 'no-store')
        self.assertEqual([(self.root / PREFIX / name).read_bytes() for name in sources], before)

    def test_private_and_retired_events_do_not_contribute_counts_or_labels(self):
        with httpx.Client(timeout=30) as client:
            self.login(client)
            self.seed('<private>SyntheticPerformanceHidden</private>')
            for route in ROUTES:
                response = client.get(self.native + route)
                self.assertEqual(response.status_code, 200, response.text[:300])
                self.assertNotIn('SyntheticPerformanceHidden', response.text)
            self.assertEqual(client.get(self.native + ROUTES[0]).json()['totalSessions'], 0)
            self.seed()
            memory = self.fixture.fixture.fixture.fixture.fixture.memory
            saved = memory.remember(OWNER, category='principal', content='RULE: SyntheticPerformanceCurrent',
                title='', project='', request_id='performance-save')
            memory.forget(OWNER, saved['reference'], 'performance-forget')
            for route in ROUTES:
                response = client.get(self.native + route)
                self.assertEqual(response.status_code, 200, response.text[:300])
                self.assertNotIn('SyntheticPerformanceCurrent', response.text)
            self.assertEqual(client.get(self.native + ROUTES[0]).json()['totalSessions'], 0)

    def test_current_account_origin_bearer_and_connector_govern_delivery(self):
        self.seed()
        with httpx.Client(timeout=30) as client:
            self.login(client)
            self.assertEqual(client.get(self.native + ROUTES[0]).status_code, 200)
            self.assertEqual(client.get(self.native + ROUTES[0], headers={'Origin': 'https://untrusted.invalid'}).status_code, 403)
            self.assertEqual(client.get(self.native + ROUTES[0], headers={'Authorization': 'Bearer invalid'}).status_code, 401)
            self.fixture.configuration.update(lambda config: config['accounts'].clear())
            self.assertEqual(client.get(self.native + ROUTES[0]).status_code, 403)
            (self.root / 'LIFEOS/USER/CONFIG/memory-access.json').unlink()
            self.assertEqual(client.get(self.native + ROUTES[0]).status_code, 503)

    def test_methods_and_non_declared_selectors_refuse(self):
        self.seed()
        with httpx.Client(timeout=30) as client:
            self.login(client)
            for method, target, status in (('POST', ROUTES[0], 405), ('GET', ROUTES[0] + '?owner=other', 400),
                    ('GET', ROUTES[0] + '?days=0', 400), ('GET', ROUTES[1] + '?days=7', 400),
                    ('GET', '/api/performance/unsupported', 404)):
                with self.subTest(target=target):
                    response = client.request(method, self.native + target)
                    self.assertEqual(response.status_code, status, response.text[:300])
                    self.assertEqual(response.headers.get('cache-control'), 'no-store')

    def test_day_window_boundaries_and_encoded_or_duplicate_selectors_refuse(self):
        self.seed()
        with httpx.Client(timeout=30) as client:
            self.login(client)
            for days in (1, 3660):
                target = ROUTES[0] + '?days=' + str(days)
                response = client.get(self.native + target)
                self.assertEqual(response.status_code, 200, response.text[:300])
                self.assertEqual(response.json(), self.original(target))
            for query in ('days=3661', 'days=99999', 'days=-1', 'days=01', 'days=1.5', 'days=7&days=30',
                    'days=%37', 'days=7&owner=other', 'days=7junk'):
                with self.subTest(query=query):
                    response = client.get(self.native + ROUTES[0] + '?' + query)
                    self.assertEqual(response.status_code, 400, response.text[:300])
                    self.assertEqual(response.headers.get('cache-control'), 'no-store')

    def test_present_optional_quota_history_and_call_sites_preserve_native_fields(self):
        ledger = self.root / PREFIX / 'anthropic-cost.jsonl'
        ledger.parent.mkdir(parents=True, exist_ok=True)
        ledger.write_text(''.join(json.dumps({'ts': '2026-10-09T00:00:00Z',
            'subscription': {'five_hour_pct': i, 'seven_day_pct': 50},
            'api_spend': {'month_used_usd': 1.25, 'source': 'synthetic'},
            'call_sites': {'total': 1, 'bypass': 0, 'legit': 1, 'new_since_baseline': []},
            'alerts': ['SyntheticQuota' + str(i)]}) + '\n' for i in range(27)))
        sites = self.root / PREFIX / 'anthropic-call-sites.json'
        sites.write_text(json.dumps({'updated': '2026-10-09T00:00:00Z', 'sites': [
            {'file': 'SyntheticQuotaTool.ts', 'line': 3, 'classification': 'legit', 'reason': 'synthetic'}]}))
        before = [(p.read_bytes(), p.stat().st_mtime_ns) for p in (ledger, sites)]
        original = self.original(ROUTES[3])
        self.assertEqual(original['total_entries'], 27)
        self.assertEqual(len(original['history']), 24)
        with httpx.Client(timeout=30) as client:
            self.login(client)
            response = client.get(self.native + ROUTES[3])
            self.assertEqual(response.status_code, 200, response.text[:300])
            self.assertEqual(response.json(), original)
            self.assertEqual(response.headers.get('cache-control'), 'no-store')
        self.assertEqual([(p.read_bytes(), p.stat().st_mtime_ns) for p in (ledger, sites)], before)

    def test_decoded_private_optional_quota_records_do_not_contribute_counts(self):
        path = self.root / PREFIX / 'anthropic-cost.jsonl'
        path.parent.mkdir(parents=True, exist_ok=True)
        text = json.dumps({'alerts': [json.dumps({'label': '<private>SyntheticQuotaHidden</private>'})]})
        path.write_text(text.replace('<', '\\u003c').replace('>', '\\u003e') + '\n')
        with httpx.Client(timeout=30) as client:
            self.login(client)
            response = client.get(self.native + ROUTES[3])
            self.assertEqual(response.status_code, 200, response.text[:300])
            self.assertEqual(response.json()['total_entries'], 0)
            self.assertNotIn('SyntheticQuotaHidden', response.text)
            sites = self.root / PREFIX / 'anthropic-call-sites.json'
            sites.write_text(json.dumps({'sites': [{'file': '<private>SyntheticQuotaHidden</private>'}]}))
            response = client.get(self.native + ROUTES[3])
            self.assertEqual(response.status_code, 503, response.text[:300])
            self.assertNotIn('SyntheticQuotaHidden', response.text)

    def test_complete_large_cost_history_preserves_native_counts(self):
        self.seed(count=4001)
        self.assertGreater((self.root / PREFIX / 'session-costs.jsonl').stat().st_size, 1024 * 1024)
        with httpx.Client(timeout=40) as client:
            self.login(client)
            for route in (ROUTES[0], ROUTES[2]):
                response = client.get(self.native + route)
                self.assertEqual(response.status_code, 200, response.text[:300])
                self.assertEqual(response.json(), self.original(route))
                self.assertEqual(response.json()['totalSessions'], 4001)

    def test_complete_terminal_record_without_newline_is_included(self):
        self.seed()
        path = self.root / PREFIX / 'session-costs.jsonl'
        path.write_text(path.read_text().rstrip('\n'))
        with httpx.Client(timeout=30) as client:
            self.login(client)
            response = client.get(self.native + ROUTES[0])
            self.assertEqual(response.status_code, 200, response.text[:300])
            self.assertEqual(response.json(), self.original(ROUTES[0]))
            self.assertEqual(response.json()['totalSessions'], 1)
            self.assertEqual(response.headers.get('cache-control'), 'no-store')

    def test_native_listener_keeps_slow_admitted_response_until_relay_delivery(self):
        self.seed()
        with httpx.Client(timeout=50) as client:
            self.login(client)
            self.assertEqual(client.get(self.native + ROUTES[0]).status_code, 200)
            memory_class = sys.modules['lifeos_memory_settings.memory_access'].NativeMemory
            original = memory_class._native

            def observe(memory, action, **arguments):
                result = original(memory, action, **arguments)
                if action == 'performance_view': time.sleep(22)
                return result

            memory_class._native = observe
            self.addCleanup(setattr, memory_class, '_native', original)
            started = time.monotonic()
            response = client.get(self.native + ROUTES[0])
            elapsed = time.monotonic() - started
            self.assertGreaterEqual(elapsed, 22)
            self.assertEqual(response.status_code, 200, response.text[:300])
            self.assertEqual(response.json(), self.original(ROUTES[0]))
            self.assertEqual(response.headers.get('cache-control'), 'no-store')
            print('Actual delayed native Performance delivery seconds:', round(elapsed, 6))

    def test_exact_source_review_restores_permitted_old_log_records(self):
        from lifeos_hook_bridge.memory_source_review import preview, approve
        sources = self.seed()
        memory = self.fixture.fixture.fixture.fixture.fixture.memory
        saved = memory.remember(OWNER, category='principal', content='RULE: Synthetic unrelated Performance retirement',
            title='', project='', request_id='performance-review-save')
        memory.forget(OWNER, saved['reference'], 'performance-review-forget')
        relatives = [PREFIX + name for name in sources]
        before = [((self.root / relative).read_bytes(), (self.root / relative).stat().st_mtime_ns) for relative in relatives]
        with httpx.Client(timeout=30) as client:
            self.login(client)
            self.assertEqual(client.get(self.native + ROUTES[0]).json()['totalSessions'], 0)
            selected = preview(memory, OWNER, relatives)
            self.assertTrue(all(row['accepted'] for row in selected['sources']), selected)
            self.assertEqual(approve(memory, OWNER, relatives, selected['signature'])['status'], 'committed')
            self.assertEqual(client.get(self.native + ROUTES[0]).json()['totalSessions'], 1)
        self.assertEqual([((self.root / relative).read_bytes(), (self.root / relative).stat().st_mtime_ns) for relative in relatives], before)

    def test_actual_native_render_rechecks_logs_authority_and_admitted_descriptor(self):
        configuration = self.fixture.configuration.path.read_bytes()
        for mode in ('source', 'metadata', 'created', 'authority', 'descriptor'):
            with self.subTest(mode=mode):
                self.fixture.configuration.path.write_bytes(configuration)
                self.seed()
                if mode == 'created': (self.root / PREFIX / 'session-costs.jsonl').unlink()
                result = subprocess.run([sys.executable, str(Path(__file__).with_name('memory_performance_process.py')),
                    str(self.fixture.configuration.path), mode], capture_output=True, text=True, timeout=30,
                    env=dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1])))
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stderr, '')
                self.assertEqual(json.loads(result.stdout), {'rendered': True, 'withheld': True})

    def test_actual_native_quota_render_rechecks_call_site_bytes_inode_and_creation(self):
        path = self.root / PREFIX / 'anthropic-call-sites.json'
        for mode in ('source', 'metadata', 'created'):
            with self.subTest(mode=mode):
                self.seed()
                path.write_text(json.dumps({'sites': [{'file': 'SyntheticPerformanceCurrent'}]}))
                if mode == 'created': path.unlink()
                result = subprocess.run([sys.executable, str(Path(__file__).with_name('memory_performance_process.py')),
                    str(self.fixture.configuration.path), 'sites-' + mode], capture_output=True, text=True, timeout=30,
                    env=dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1])))
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stderr, '')
                self.assertEqual(json.loads(result.stdout), {'rendered': True, 'withheld': True})

    def test_redirected_and_invalid_utf8_log_refuses(self):
        with httpx.Client(timeout=30) as client:
            self.login(client)
            for mode in ('symlink', 'hardlink', 'utf8', 'utf8-terminal'):
                with self.subTest(mode=mode):
                    path = self.root / PREFIX / 'session-costs.jsonl'
                    if path.exists() or path.is_symlink(): path.unlink()
                    self.seed()
                    if mode in ('symlink', 'hardlink'):
                        outside = self.fixture.home / 'synthetic-performance-outside'
                        outside.write_bytes(path.read_bytes())
                        path.unlink()
                        if mode == 'symlink': path.symlink_to(outside)
                        else: os.link(outside, path)
                    elif mode == 'utf8-terminal': path.write_bytes(b'\xe2\x82')
                    else: path.write_bytes(b'\xff\n')
                    response = client.get(self.native + ROUTES[0])
                    self.assertEqual(response.status_code, 503, response.text[:300])


if __name__ == '__main__': unittest.main()
