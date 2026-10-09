# ABOUTME: Checks native operational dashboard readers through actual owner HTTP services.
# ABOUTME: Uses disposable session and event files to verify authentication and source admission.
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import unittest

import httpx
import test_memory_pulse_relay as relay_fixture
from test_memory_native import OWNER


ROUTES = ('/api/algorithm', '/api/agents', '/api/events/recent',
          '/api/observability/voice-events', '/api/observability/tool-failures')


class MemoryOperationalViewsTests(unittest.TestCase):
    native_module = 'observability.ts'
    setUp = relay_fixture.MemoryPulseRelayTests.setUp
    create_fixture = relay_fixture.MemoryPulseRelayTests.create_fixture
    native_module_name = relay_fixture.MemoryPulseRelayTests.native_module_name
    stop_dashboard = relay_fixture.MemoryPulseRelayTests.stop_dashboard
    stop_pulse = relay_fixture.MemoryPulseRelayTests.stop_pulse
    login = relay_fixture.MemoryPulseRelayTests.login

    def seed(self, marker='SyntheticOperationalCurrent'):
        now = (datetime.now(timezone.utc) - timedelta(minutes=2)).isoformat()
        sources = {
            'STATE/work.json': json.dumps({'sessions': {'synthetic-run': {
                'task': marker, 'sessionName': marker, 'phase': 'execute', 'progress': '1/2',
                'started': now, 'updatedAt': now, 'lastToolActivity': now, 'sessionUUID': 'synthetic-session',
                'isa': 'synthetic-isa', 'criteria': [{'id': 'C1', 'description': marker, 'status': 'completed'}]}}}),
            'STATE/work-events.jsonl': json.dumps({'ts': now, 'op': 'upsert', 'slug': 'synthetic-run',
                'fields': {'progress': '1/2'}, 'note': marker}) + '\n',
            'OBSERVABILITY/tool-activity.jsonl': json.dumps({'timestamp': now, 'type': 'tool_use',
                'event': 'tool_use', 'session_id': 'synthetic-session', 'tool_name': 'Write',
                'tool_input_preview': json.dumps({'file': marker})}) + '\n',
            'OBSERVABILITY/subagent-events.jsonl': json.dumps({'timestamp': now, 'event': 'subagent_start',
                'type': 'subagent_start', 'task': marker, 'session_id': 'synthetic-session'}) + '\n',
            'OBSERVABILITY/tool-failures.jsonl': json.dumps({'timestamp': now, 'type': 'tool_failure',
                'detail': marker, 'session_id': 'synthetic-session'}) + '\n',
            'VOICE/voice-events.jsonl': json.dumps({'timestamp': now, 'type': 'voice', 'text': marker}) + '\n',
        }
        for relative, content in sources.items():
            path = self.root / 'LIFEOS/MEMORY' / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
        return sources

    def test_anonymous_and_ambient_owner_cannot_read_operational_routes(self):
        self.seed()
        for route in ROUTES:
            with self.subTest(route=route):
                result = httpx.get(self.native + route, headers={'X-LifeOS-Owner': 'owner'})
                self.assertEqual(result.status_code, 401, result.text)
                self.assertNotIn('SyntheticOperationalCurrent', result.text)
                self.assertEqual(result.headers.get('cache-control'), 'no-store')

    def test_private_and_encoded_private_sources_cannot_enter_operational_views(self):
        self.seed('<private>SyntheticOperationalPrivate</private>')
        with httpx.Client(timeout=30) as client:
            self.login(client)
            for route in ROUTES:
                with self.subTest(route=route):
                    result = client.get(self.native + route)
                    self.assertEqual(result.status_code, 200, result.text)
                    self.assertNotIn('SyntheticOperationalPrivate', result.text)

    def test_retired_text_cannot_return_from_original_session_or_event_files(self):
        self.seed()
        memory = self.fixture.fixture.fixture.fixture.fixture.memory
        saved = memory.remember(OWNER, category='principal', content='RULE: SyntheticOperationalCurrent',
            title='', project='', request_id='operational-retained')
        memory.forget(OWNER, saved['reference'], 'operational-forget')
        with httpx.Client(timeout=30) as client:
            self.login(client)
            for route in ROUTES:
                with self.subTest(route=route):
                    result = client.get(self.native + route)
                    self.assertEqual(result.status_code, 200, result.text)
                    self.assertNotIn('SyntheticOperationalCurrent', result.text)

    def test_revoked_account_and_missing_connector_cannot_fall_back_to_raw_sessions(self):
        self.seed()
        with httpx.Client(timeout=30) as client:
            self.login(client)
            self.fixture.configuration.update(lambda value: value['accounts'].clear())
            result = client.get(self.native + '/api/algorithm')
            self.assertEqual(result.status_code, 403, result.text)
            self.assertNotIn('SyntheticOperationalCurrent', result.text)
        (self.root / 'LIFEOS/USER/CONFIG/memory-access.json').unlink()
        result = httpx.get(self.native + '/api/algorithm')
        self.assertEqual(result.status_code, 503, result.text)

    def test_operational_routes_refuse_selectors_methods_origin_and_invalid_bearer(self):
        self.seed()
        with httpx.Client(timeout=30) as client:
            self.login(client)
            for method, target, headers, status in (
                ('POST', '/api/algorithm', {}, 405), ('GET', '/api/agents?owner=other', {}, 400),
                ('GET', '/api/algorithm', {'Origin': 'https://outside.invalid'}, 403),
                ('GET', '/api/algorithm', {'Authorization': 'Bearer synthetic-invalid'}, 401)):
                with self.subTest(method=method, target=target, headers=headers):
                    result = client.request(method, self.native + target, headers=headers)
                    self.assertEqual(result.status_code, status, result.text)
                    self.assertNotIn('SyntheticOperationalCurrent', result.text)

    def test_anonymous_stream_refuses_before_sending_initial_algorithm_state(self):
        self.seed()
        with httpx.stream('GET', self.native + '/api/algorithm/stream', timeout=15) as response:
            self.assertEqual(response.status_code, 401)
            self.assertEqual(response.headers.get('cache-control'), 'no-store')

    def test_native_stream_initial_event_matches_current_algorithm_response(self):
        self.seed()
        with httpx.Client(timeout=30) as client:
            self.login(client)
            snapshot = client.get(self.native + '/api/algorithm')
            self.assertEqual(snapshot.status_code, 200, snapshot.text)
            started = time.monotonic()
            with client.stream('GET', self.native + '/api/algorithm/stream') as response:
                self.assertEqual(response.status_code, 200)
                lines = response.iter_lines()
                self.assertEqual(next(lines), 'event: algorithm')
                frame = next(lines)
                self.assertTrue(frame.startswith('data: '), frame)
                self.assertEqual(json.loads(frame[6:]), snapshot.json())
                print('Initial operational stream seconds:', round(time.monotonic() - started, 6))

    def original(self, route):
        source = Path(os.environ['LIFEOS_HARVEST_CONTROL_SOURCE'])
        script = ('import {startObservability,handleObservabilityRequest} from ' + json.dumps(str(
            source / 'LIFEOS/PULSE/Observability/observability.ts')) + ';\n'
            'startObservability({enabled:true});\n'
            'const response=await handleObservabilityRequest(new Request("http://127.0.0.1"+' + json.dumps(route) + '));\n'
            'if(!response)throw new Error("Missing native operational response");console.log(await response.text());\n')
        result = subprocess.run(['bun', '--no-install', '-e', script], capture_output=True, text=True,
            timeout=30, env=dict(os.environ, HOME=str(self.fixture.home)))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        return json.loads(result.stdout)

    def test_admitted_operational_views_preserve_native_fields_and_folding(self):
        self.seed()
        with httpx.Client(timeout=30) as client:
            self.login(client)
            for route in ROUTES:
                with self.subTest(route=route):
                    result = client.get(self.native + route)
                    self.assertEqual(result.status_code, 200, result.text)
                    self.assertEqual(result.json(), self.original(route))

    def test_log_rotation_with_equal_bytes_cannot_reuse_prior_private_activity_cache(self):
        self.seed()
        with httpx.Client(timeout=30) as client:
            self.login(client)
            result = client.get(self.native + '/api/algorithm')
            self.assertEqual(result.status_code, 200, result.text)
            self.assertEqual(result.json()['algorithms'][0]['activity']['lastTool'], 'Write')
            path = self.root / 'LIFEOS/MEMORY/OBSERVABILITY/tool-activity.jsonl'
            before = path.read_bytes()
            old_inode = path.stat().st_ino
            replacement = path.with_suffix('.replacement')
            replacement.write_bytes(before.replace(b'"Write"', b'"Agent"'))
            self.assertEqual(replacement.stat().st_size, path.stat().st_size)
            replacement.replace(path)
            result = client.get(self.native + '/api/algorithm')
            self.assertEqual(result.status_code, 200, result.text)
            self.assertEqual(json.loads(path.read_text())['tool_name'], 'Agent')
            print('Equal-length rotation observation:', json.dumps({
                'bytes': len(before), 'prior_inode': old_inode, 'current_inode': path.stat().st_ino,
                'source_tool': 'Agent', 'displayed_tool': result.json()['algorithms'][0]['activity']['lastTool']}))
            self.assertEqual(result.json()['algorithms'][0]['activity']['lastTool'], 'Agent')

    def test_async_native_relay_preserves_owner_response_and_keeps_event_loop_running(self):
        self.seed()
        module = self.root / 'LIFEOS/TOOLS/lib/MemoryAccess.ts'
        with httpx.Client(timeout=30) as client:
            self.login(client)
            cookie = '; '.join(f'{key}={value}' for key, value in client.cookies.items())
            expected = client.get(self.native + '/api/algorithm').json()
            program = self.fixture.home / 'async-operational-relay.ts'
            program.write_text('import {memoryHTTPResponseAsync,memoryHTTPResponse} from ' + json.dumps(str(module)) + ';\n'
                'const request=new Request("http://127.0.0.1/api/algorithm",{headers:{cookie:' + json.dumps(cookie) + '}});\n'
                'let synchronousTimer=false;\n'
                'const started=performance.now();\n'
                'const syncTimer=setTimeout(()=>{synchronousTimer=true;},5);\n'
                'const sync=memoryHTTPResponse(request,"life","/api/algorithm");\n'
                'const syncSeconds=(performance.now()-started)/1000;\n'
                'const blocked=!synchronousTimer;clearTimeout(syncTimer);\n'
                'let asynchronousTimer=false;\n'
                'const asyncTimer=setTimeout(()=>{asynchronousTimer=true;},5);\n'
                'const response=await memoryHTTPResponseAsync(request,"life","/api/algorithm");\n'
                'clearTimeout(asyncTimer);\n'
                'const denied=await memoryHTTPResponseAsync(new Request("http://127.0.0.1/api/algorithm"),"life","/api/algorithm");\n'
                'console.log(JSON.stringify({status:response.status,body:await response.json(),\n'
                'denied:denied.status,blocked,asynchronousTimer,syncSeconds}));\n')
            result = subprocess.run(['bun', '--no-install', str(program)], capture_output=True, text=True,
                timeout=30, env=dict(os.environ, HOME=str(self.fixture.home)))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stderr, '')
            observed = json.loads(result.stdout)
            self.assertEqual(observed['status'], 200)
            self.assertEqual(observed['body'], expected)
            self.assertEqual(observed['denied'], 401)
            self.assertTrue(observed['blocked'])
            self.assertTrue(observed['asynchronousTimer'])
            print('Actual synchronous relay seconds:', observed['syncSeconds'])

    def test_existing_synchronous_relay_records_event_loop_blocking(self):
        self.seed()
        module = self.root / 'LIFEOS/TOOLS/lib/MemoryAccess.ts'
        with httpx.Client(timeout=30) as client:
            self.login(client)
            cookie = '; '.join(f'{key}={value}' for key, value in client.cookies.items())
            program = self.fixture.home / 'synchronous-relay-observation.ts'
            program.write_text('import {memoryHTTPResponse} from ' + json.dumps(str(module)) + ';\n'
                'const request=new Request("http://127.0.0.1/api/algorithm",{headers:{cookie:' + json.dumps(cookie) + '}});\n'
                'let timerRan=false;const timer=setTimeout(()=>{timerRan=true;},5);\n'
                'const started=performance.now();\n'
                'const response=memoryHTTPResponse(request,"life","/api/algorithm");\n'
                'console.log(JSON.stringify({status:response.status,timerRan,seconds:(performance.now()-started)/1000}));\n'
                'clearTimeout(timer);\n')
            result = subprocess.run(['bun', '--no-install', str(program)], capture_output=True, text=True,
                timeout=30, env=dict(os.environ, HOME=str(self.fixture.home)))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stderr, '')
            observed = json.loads(result.stdout)
            self.assertEqual(observed['status'], 200)
            self.assertFalse(observed['timerRan'])
            self.assertGreater(observed['seconds'], 0.005)
            print('Synchronous native relay observation:', json.dumps(observed))

    def next_frame(self, lines):
        for line in lines:
            if line.startswith('data: '): return json.loads(line[6:])
        self.fail('The native stream closes before its required current frame')

    def test_stream_updates_then_excludes_private_replacement_text(self):
        self.seed()
        with httpx.Client(timeout=15) as client:
            self.login(client)
            with client.stream('GET', self.native + '/api/algorithm/stream') as response:
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.headers.get('cache-control'), 'no-store')
                lines = response.iter_lines()
                self.assertIn('SyntheticOperationalCurrent', json.dumps(self.next_frame(lines)))
                path = self.root / 'LIFEOS/MEMORY/STATE/work.json'
                path.write_text(path.read_text().replace('SyntheticOperationalCurrent', 'SyntheticOperationalChanged'))
                started = time.monotonic()
                current = self.next_frame(lines)
                self.assertIn('SyntheticOperationalChanged', json.dumps(current))
                print('Actual operational stream update seconds:', round(time.monotonic() - started, 6))
                path.write_text(path.read_text().replace('SyntheticOperationalChanged', '<private>SyntheticPrivateReplacement</private>'))
                current = self.next_frame(lines)
                self.assertNotIn('SyntheticPrivateReplacement', json.dumps(current))
                self.assertEqual(current, {'algorithms': [], 'active': False, 'pulseStrip': []})

    def test_stream_forget_clears_retained_claims_and_revocation_closes_delivery(self):
        self.seed()
        memory = self.fixture.fixture.fixture.fixture.fixture.memory
        saved = memory.remember(OWNER, category='principal', content='RULE: SyntheticOperationalCurrent',
            title='', project='', request_id='operational-stream-retained')
        with httpx.Client(timeout=15) as client:
            self.login(client)
            with client.stream('GET', self.native + '/api/algorithm/stream') as response:
                self.assertEqual(response.status_code, 200)
                lines = response.iter_lines()
                self.assertIn('SyntheticOperationalCurrent', json.dumps(self.next_frame(lines)))
                memory.forget(OWNER, saved['reference'], 'operational-stream-forget')
                current = self.next_frame(lines)
                self.assertNotIn('SyntheticOperationalCurrent', json.dumps(current))
                self.fixture.configuration.update(lambda value: value['accounts'].clear())
                remaining = list(lines)
                print('Revoked operational stream remaining lines:', repr(remaining))
                self.assertEqual(remaining, [''])

    def test_stream_disconnect_stops_child_requests(self):
        self.seed()
        with httpx.Client(timeout=15) as client:
            self.login(client)
            with client.stream('GET', self.native + '/api/algorithm/stream') as response:
                self.assertEqual(response.status_code, 200)
                self.next_frame(response.iter_lines())
            children = Path(f'/proc/{self.process.pid}/task/{self.process.pid}/children')
            samples = []
            deadline = time.monotonic() + 3
            while children.read_text().strip() and time.monotonic() < deadline: time.sleep(0.05)
            for _ in range(8):
                samples.append(children.read_text().strip())
                time.sleep(0.05)
            self.assertEqual(samples, [''] * 8)

    def test_native_byte_tail_preserves_large_history_and_ignores_malformed_rows(self):
        self.seed()
        path = self.root / 'LIFEOS/MEMORY/OBSERVABILITY/subagent-events.jsonl'
        row = path.read_text()
        path.write_text(('invalid early row ' + 'x' * 140) * 7500 + '\nmalformed-row\n' + row)
        self.assertGreater(path.stat().st_size, 1024 * 1024)
        with httpx.Client(timeout=30) as client:
            self.login(client)
            response = client.get(self.native + '/api/agents')
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json(), self.original('/api/agents'))

    def test_nested_json_private_spans_are_decoded_before_event_delivery(self):
        self.seed()
        path = self.root / 'LIFEOS/MEMORY/OBSERVABILITY/tool-activity.jsonl'
        row = json.loads(path.read_text())
        row['tool_input_preview'] = '{"command":"\\u003cprivate\\u003eSyntheticNestedPrivate\\u003c/private\\u003e"}'
        path.write_text(json.dumps(row) + '\n')
        with httpx.Client(timeout=30) as client:
            self.login(client)
            response = client.get(self.native + '/api/events/recent')
            self.assertEqual(response.status_code, 200, response.text)
            self.assertNotIn('SyntheticNestedPrivate', response.text)

    def test_torn_activity_line_waits_until_the_original_writer_completes_it(self):
        self.seed()
        path = self.root / 'LIFEOS/MEMORY/OBSERVABILITY/tool-activity.jsonl'
        path.write_text(path.read_text().rstrip('\n'))
        with httpx.Client(timeout=30) as client:
            self.login(client)
            response = client.get(self.native + '/api/algorithm')
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json(), self.original('/api/algorithm'))
            self.assertNotIn('activity', response.json()['algorithms'][0])
            with path.open('a') as stream: stream.write('\n')
            response = client.get(self.native + '/api/algorithm')
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()['algorithms'][0]['activity']['lastTool'], 'Write')

    def test_redirected_and_hardlinked_operational_sources_refuse(self):
        self.seed()
        path = self.root / 'LIFEOS/MEMORY/STATE/work.json'
        outside = self.fixture.home / 'outside-work.json'
        outside.write_text(path.read_text())
        path.unlink()
        path.symlink_to(outside)
        with httpx.Client(timeout=30) as client:
            self.login(client)
            response = client.get(self.native + '/api/algorithm')
            self.assertEqual(response.status_code, 503, response.text)
            path.unlink()
            os.link(outside, path)
            response = client.get(self.native + '/api/algorithm')
            self.assertEqual(response.status_code, 503, response.text)

    def test_source_creation_metadata_and_authority_after_actual_render_withhold_response(self):
        for mode in ('source', 'created', 'metadata', 'authority'):
            with self.subTest(mode=mode):
                self.seed()
                (self.root / 'LIFEOS/MEMORY/STATE/work-events.jsonl').unlink()
                result = subprocess.run([sys.executable, str(Path(__file__).with_name(
                    'memory_operational_views_process.py')), str(self.fixture.configuration.path), mode],
                    capture_output=True, text=True, timeout=30,
                    env=dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1])))
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stderr, '')
                self.assertEqual(json.loads(result.stdout), {'rendered': True, 'withheld': True})

    def test_review_restores_safe_old_events_without_changing_original_sources(self):
        self.seed()
        memory = self.fixture.fixture.fixture.fixture.fixture.memory
        saved = memory.remember(OWNER, category='principal', content='RULE: SyntheticUnrelatedOperationalRetirement',
            title='', project='', request_id='operational-review-retained')
        memory.forget(OWNER, saved['reference'], 'operational-review-forget')
        paths = ['LIFEOS/MEMORY/' + name for name in self.seed().keys()]
        for relative in paths:
            path = self.root / relative
            if path.suffix == '.jsonl':
                text = path.read_text()
                row = json.loads(text)
                for key in ('ts', 'timestamp'):
                    if key in row: row[key] = '2020-01-01T00:00:00Z'
                path.write_text(json.dumps(row) + '\n')
            os.utime(path, (1_577_836_800, 1_577_836_800))
        before = {relative: ((self.root / relative).read_bytes(), (self.root / relative).stat().st_mtime_ns)
                  for relative in paths}
        endpoint = self.dashboard + '/api/plugins/lifeos-hook-bridge/memory/sources'
        with httpx.Client(timeout=30) as client:
            self.login(client)
            self.assertNotIn('SyntheticOperationalCurrent', client.get(self.native + '/api/agents').text)
            preview = client.post(endpoint + '/preview', json={'paths': paths})
            self.assertEqual(preview.status_code, 200, preview.text)
            snapshot = preview.json()
            self.assertTrue(all(source['accepted'] for source in snapshot['sources']), snapshot)
            approval = client.post(endpoint, json={'paths': paths, 'signature': snapshot['signature']})
            self.assertEqual(approval.status_code, 200, approval.text)
            self.assertEqual(approval.json()['status'], 'committed')
            for route in ROUTES:
                with self.subTest(route=route):
                    response = client.get(self.native + route)
                    self.assertEqual(response.status_code, 200, response.text)
                    self.assertEqual(response.json(), self.original(route))
        for relative, snapshot in before.items():
            self.assertEqual(((self.root / relative).read_bytes(), (self.root / relative).stat().st_mtime_ns), snapshot)

    def test_stream_selectors_methods_origin_and_connector_loss_refuse(self):
        self.seed()
        with httpx.Client(timeout=15) as client:
            self.login(client)
            for method, suffix, headers, status in (
                ('POST', '', {}, 405), ('GET', '?owner=other', {}, 400),
                ('GET', '', {'Origin': 'https://outside.invalid'}, 403),
                ('GET', '', {'Authorization': 'Bearer synthetic-invalid'}, 401)):
                with self.subTest(method=method, suffix=suffix, headers=headers):
                    response = client.request(method, self.native + '/api/algorithm/stream' + suffix, headers=headers)
                    self.assertEqual(response.status_code, status, response.text)
                    self.assertNotIn('SyntheticOperationalCurrent', response.text)
            with client.stream('GET', self.native + '/api/algorithm/stream') as response:
                self.assertEqual(response.status_code, 200)
                lines = response.iter_lines()
                self.next_frame(lines)
                (self.root / 'LIFEOS/USER/CONFIG/memory-access.json').unlink()
                self.assertEqual(list(lines), [''])

    def test_complete_history_and_event_limits_refuse_without_source_disclosure(self):
        self.seed()
        with httpx.Client(timeout=30) as client:
            self.login(client)
            for relative, content, expected in (
                ('STATE/work.json', json.dumps({'note': 'SyntheticOversizeOperational' + 'x' * (256 * 1024)}), 503),
                ('STATE/work-events.jsonl', '{"note":"SyntheticOversizeOperational"}\n' * 40000, 200),
                ('STATE/work-events.jsonl', '{"note":"SyntheticOversizeOperational"}\n' * 2049, 200),
                ('OBSERVABILITY/tool-activity.jsonl', json.dumps({'note': 'SyntheticOversizeOperational' + 'x' * (256 * 1024)}) + '\n', 503)):
                with self.subTest(relative=relative, bytes=len(content.encode())):
                    self.seed()
                    (self.root / 'LIFEOS/MEMORY' / relative).write_text(content)
                    response = client.get(self.native + '/api/algorithm')
                    self.assertEqual(response.status_code, expected, response.text)
                    if expected == 200: self.assertEqual(response.json(), self.original('/api/algorithm'))
                    self.assertNotIn('SyntheticOversizeOperational', response.text)
