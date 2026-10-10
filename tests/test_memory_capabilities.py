# ABOUTME: Checks current capability telemetry through authenticated native HTTP requests.
# ABOUTME: Compares original aggregation and byte windows while refusing excluded event text.
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import unittest

import httpx
import test_memory_operational_views as operational_fixture
from test_memory_native import OWNER


class MemoryCapabilitiesTests(unittest.TestCase):
    native_module = 'observability.ts'
    setUp = operational_fixture.MemoryOperationalViewsTests.setUp
    create_fixture = operational_fixture.MemoryOperationalViewsTests.create_fixture
    native_module_name = operational_fixture.MemoryOperationalViewsTests.native_module_name
    stop_dashboard = operational_fixture.MemoryOperationalViewsTests.stop_dashboard
    stop_pulse = operational_fixture.MemoryOperationalViewsTests.stop_pulse
    login = operational_fixture.MemoryOperationalViewsTests.login
    original = operational_fixture.MemoryOperationalViewsTests.original

    def seed(self, marker='SyntheticCapabilityCurrent', copies=1):
        now = datetime.now(timezone.utc) - timedelta(minutes=3)
        tools = ['Skill', 'Agent', 'Agent', 'Workflow', 'SendMessage', 'ToolSearch', 'WebSearch',
                 'WebFetch', 'mcp__synthetic__lookup', 'Write']
        events = [{'event': 'tool_use', 'tool_name': name, 'timestamp': now.isoformat(),
            'session_id': 'synthetic-session', 'tool_input_preview': json.dumps({'skill': marker})}
            for name in tools]
        events += [{'event': 'tool_use', 'tool_name': 'Skill', 'timestamp':
                    (now - timedelta(hours=2)).isoformat(), 'session_id': 'synthetic-earlier',
                    'tool_input_preview': json.dumps({'skill': 'SyntheticEarlierCapability'})},
                   {'event': 'other', 'tool_name': marker, 'timestamp': now.isoformat()}]
        activity = self.root / 'LIFEOS/MEMORY/OBSERVABILITY/tool-activity.jsonl'
        activity.parent.mkdir(parents=True, exist_ok=True)
        activity.write_text(''.join(json.dumps(row) + '\n' for row in events) * copies)
        subagents = activity.with_name('subagent-events.jsonl')
        subagents.write_text(json.dumps({'event': 'subagent_start', 'timestamp': now.isoformat(),
            'subagent_model': 'synthetic-model', 'subagent_type': marker}) + '\n')
        return activity, subagents

    def comparable(self, response):
        self.assertIn('generated_at', response)
        self.assertIsNotNone(datetime.fromisoformat(response['generated_at'].replace('Z', '+00:00')).tzinfo)
        return {key: value for key, value in response.items() if key != 'generated_at'}

    def test_anonymous_request_cannot_read_capability_labels(self):
        self.seed()
        response = httpx.get(self.native + '/api/capabilities')
        self.assertEqual(response.status_code, 401, response.text[:300])
        self.assertEqual(response.headers.get('cache-control'), 'no-store')
        self.assertNotIn('SyntheticCapabilityCurrent', response.text)

    def test_current_owner_preserves_all_native_windows_and_aggregation(self):
        paths = self.seed()
        before = [(path.read_bytes(), path.stat().st_mtime_ns) for path in paths]
        with httpx.Client(timeout=40) as client:
            self.login(client)
            for suffix in ('', '?window=60', '?window=360', '?window=1440'):
                with self.subTest(suffix=suffix):
                    route = '/api/capabilities' + suffix
                    response = client.get(self.native + route)
                    self.assertEqual(response.status_code, 200, response.text[:300])
                    self.assertEqual(self.comparable(response.json()), self.comparable(self.original(route)))
                    self.assertEqual(response.headers.get('cache-control'), 'no-store')
        self.assertEqual([(path.read_bytes(), path.stat().st_mtime_ns) for path in paths], before)

    def test_dense_activity_preserves_counts_above_record_and_transport_caps(self):
        activity, _ = self.seed(copies=1500)
        self.assertGreater(activity.stat().st_size, 3 * 1024 * 1024)
        with httpx.Client(timeout=40) as client:
            self.login(client)
            for window in (60, 360, 1440):
                with self.subTest(window=window):
                    route = '/api/capabilities?window=' + str(window)
                    response = client.get(self.native + route)
                    self.assertEqual(response.status_code, 200, response.text[:300])
                    self.assertEqual(self.comparable(response.json()), self.comparable(self.original(route)))

    def test_private_and_retired_labels_do_not_change_native_counts(self):
        self.seed('<private>SyntheticCapabilityPrivate</private>')
        # All current rows include the excluded preview, including rows whose tool names are public.
        with httpx.Client(timeout=40) as client:
            self.login(client)
            for marker in ('<private>SyntheticCapabilityPrivate</private>', 'SyntheticCapabilityRetired'):
                with self.subTest(marker=marker):
                    if marker == 'SyntheticCapabilityRetired':
                        memory = self.fixture.fixture.fixture.fixture.fixture.memory
                        saved = memory.remember(OWNER, category='principal', content='RULE: SyntheticCapabilityRetired',
                            title='', project='', request_id='capabilities-retained')
                        memory.forget(OWNER, saved['reference'], 'capabilities-forget')
                    self.seed(marker)
                    response = client.get(self.native + '/api/capabilities')
                    self.assertEqual(response.status_code, 200, response.text[:300])
                    self.assertEqual(response.json()['totals']['tool_calls'], 0)
                    self.assertEqual(response.json()['skills'], [])
                    self.assertNotIn(marker, response.text)

    def test_revocation_connector_loss_and_redirected_sources_refuse(self):
        activity, _ = self.seed()
        outside = self.fixture.home / 'synthetic-capabilities-outside.jsonl'
        outside.write_bytes(activity.read_bytes())
        with httpx.Client(timeout=40) as client:
            self.login(client)
            for mode in ('symlink', 'hardlink', 'revoked', 'missing'):
                with self.subTest(mode=mode):
                    if mode in ('symlink', 'hardlink'):
                        activity.unlink()
                        if mode == 'symlink': activity.symlink_to(outside)
                        else: os.link(outside, activity)
                        expected = 503
                    elif mode == 'revoked':
                        activity.unlink()
                        self.seed()
                        self.fixture.configuration.update(lambda value: value['accounts'].clear())
                        expected = 403
                    else:
                        (self.root / 'LIFEOS/USER/CONFIG/memory-access.json').unlink()
                        expected = 503
                    response = client.get(self.native + '/api/capabilities')
                    self.assertEqual(response.status_code, expected, response.text[:300])
                    self.assertNotIn('SyntheticCapabilityCurrent', response.text)

    def test_methods_unknown_selectors_origin_and_invalid_credentials_refuse(self):
        self.seed()
        with httpx.Client(timeout=40) as client:
            self.login(client)
            for method, target, headers, status in (
                    ('POST', '/api/capabilities', {}, 405),
                    ('GET', '/api/capabilities?owner=other', {}, 400),
                    ('GET', '/api/capabilities?window=360&owner=other', {}, 400),
                    ('GET', '/api/capabilities?window=360&window=60', {}, 400),
                    ('GET', '/api/capabilities', {'Origin': 'https://outside.invalid'}, 403),
                    ('GET', '/api/capabilities', {'Authorization': 'Bearer synthetic-invalid'}, 401)):
                with self.subTest(method=method, target=target):
                    response = client.request(method, self.native + target, headers=headers)
                    self.assertEqual(response.status_code, status, response.text[:300])
                    self.assertNotIn('SyntheticCapabilityCurrent', response.text)

    def test_complete_final_rows_without_newline_preserve_native_counts(self):
        paths = self.seed()
        for path in paths: path.write_bytes(path.read_bytes().rstrip(b'\n'))
        with httpx.Client(timeout=40) as client:
            self.login(client)
            response = client.get(self.native + '/api/capabilities')
            self.assertEqual(response.status_code, 200, response.text[:300])
            original = self.original('/api/capabilities')
            print('Final-record telemetry observation:', json.dumps({'managed_agents': response.json()['agents'],
                'native_agents': original['agents'], 'terminal_newlines': [path.read_bytes().endswith(b'\n') for path in paths]}))
            self.assertEqual(self.comparable(response.json()), self.comparable(original))

    def test_unfinished_utf8_tail_waits_without_stopping_current_telemetry(self):
        activity, _ = self.seed()
        row = {'event': 'tool_use', 'tool_name': 'Skill', 'session_id': 'synthetic-completed',
               'timestamp': (datetime.now(timezone.utc) - timedelta(minutes=3)).isoformat(),
               'tool_input_preview': json.dumps({'skill': 'SyntheticCapabilityCaf\u00e9'}, ensure_ascii=False)}
        encoded = (json.dumps(row, ensure_ascii=False) + '\n').encode()
        position = encoded.index('é'.encode()) + 1
        with activity.open('ab') as stream: stream.write(encoded[:position])
        with httpx.Client(timeout=40) as client:
            self.login(client)
            response = client.get(self.native + '/api/capabilities')
            self.assertEqual(response.status_code, 200, response.text[:300])
            self.assertEqual(self.comparable(response.json()), self.comparable(self.original('/api/capabilities')))
            with activity.open('ab') as stream: stream.write(encoded[position:])
            response = client.get(self.native + '/api/capabilities')
            self.assertEqual(response.status_code, 200, response.text[:300])
            self.assertEqual(self.comparable(response.json()), self.comparable(self.original('/api/capabilities')))
            self.assertIn('SyntheticCapabilityCafé', [item['name'] for item in response.json()['skills']])

    def test_twenty_megabyte_tail_keeps_each_native_window(self):
        activity, _ = self.seed(copies=11000)
        self.assertGreater(activity.stat().st_size, 20_000_000)
        with httpx.Client(timeout=60) as client:
            self.login(client)
            for window in (60, 360, 1440):
                with self.subTest(window=window):
                    route = '/api/capabilities?window=' + str(window)
                    started = time.monotonic()
                    response = client.get(self.native + route)
                    print('Large capability window observation:', json.dumps({'source_bytes': activity.stat().st_size,
                        'window_minutes': window, 'status': response.status_code,
                        'seconds': round(time.monotonic() - started, 6)}))
                    self.assertEqual(response.status_code, 200, response.text[:300])
                    self.assertEqual(self.comparable(response.json()), self.comparable(self.original(route)))

    def test_actual_aggregation_rechecks_bytes_creation_inode_and_authority(self):
        for mode in ('source', 'created', 'metadata', 'authority'):
            with self.subTest(mode=mode):
                _, subagents = self.seed()
                if mode == 'created': subagents.unlink()
                result = subprocess.run([sys.executable, str(Path(__file__).with_name(
                    'memory_capabilities_process.py')), str(self.fixture.configuration.path), mode],
                    capture_output=True, text=True, timeout=30,
                    env=dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1])))
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stderr, '')
                self.assertEqual(json.loads(result.stdout), {'rendered': True, 'withheld': True})

    def test_long_window_leaves_other_native_requests_responsive(self):
        self.seed(copies=11000)
        with httpx.Client(timeout=60) as owner, ThreadPoolExecutor(max_workers=1) as pool:
            self.login(owner)
            pending = pool.submit(owner.get, self.native + '/api/capabilities?window=1440')
            children = Path(f'/proc/{self.process.pid}/task/{self.process.pid}/children')
            deadline = time.monotonic() + 10
            while not children.read_text().strip() and time.monotonic() < deadline: time.sleep(0.01)
            self.assertTrue(children.read_text().strip(), 'The native telemetry request does not start its actual child')
            started = time.monotonic()
            anonymous = httpx.get(self.native + '/api/novelty', timeout=30)
            seconds = time.monotonic() - started
            result = pending.result(timeout=60)
            print('Concurrent native telemetry observation:', json.dumps({'other_status': anonymous.status_code,
                'other_seconds': round(seconds, 6), 'telemetry_status': result.status_code}))
            self.assertEqual(anonymous.status_code, 401, anonymous.text[:300])
            self.assertLess(seconds, 2)
            self.assertEqual(result.status_code, 200, result.text[:300])
