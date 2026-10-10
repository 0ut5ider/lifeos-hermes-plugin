# ABOUTME: Verifies native all-time climb behavior after operational log growth.
# ABOUTME: Uses actual owner services and independent native controls with disposable large histories.
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

import httpx
import test_memory_operational_views as operational_fixture
from test_memory_native import OWNER
from lifeos_hook_bridge.memory_access import MemoryUnavailable


class MemoryOperationalHistoryTests(unittest.TestCase):
    native_module = 'observability.ts'
    setUp = operational_fixture.MemoryOperationalViewsTests.setUp
    create_fixture = operational_fixture.MemoryOperationalViewsTests.create_fixture
    native_module_name = operational_fixture.MemoryOperationalViewsTests.native_module_name
    stop_dashboard = operational_fixture.MemoryOperationalViewsTests.stop_dashboard
    stop_pulse = operational_fixture.MemoryOperationalViewsTests.stop_pulse
    login = operational_fixture.MemoryOperationalViewsTests.login
    original = operational_fixture.MemoryOperationalViewsTests.original
    seed = operational_fixture.MemoryOperationalViewsTests.seed

    def history(self, count, padding=0):
        self.seed()
        early = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        now = (datetime.now(timezone.utc) - timedelta(minutes=2)).isoformat()
        current = json.dumps({'ts': now, 'op': 'upsert', 'slug': 'synthetic-run',
            'fields': {'progress': '1/2'}, 'note': 'SyntheticQuietOperationalCurve'})
        rows = [current]
        for index in range(count):
            rows.append(json.dumps({'ts': early, 'op': 'upsert', 'slug': 'synthetic-previous-run',
                'fields': {'progress': f'{index % 2}/2'}, 'note': 'SyntheticPreviousOperational' + 'x' * padding}))
        path = self.root / 'LIFEOS/MEMORY/STATE/work-events.jsonl'
        path.write_text('\n'.join(rows) + '\n')
        return path

    def test_more_than_2048_records_preserve_native_climb_for_quiet_current_run(self):
        path = self.history(2050)
        self.assertLess(path.stat().st_size, 1024 * 1024)
        expected = self.original('/api/algorithm')
        self.assertEqual(len(expected['algorithms'][0]['climb']), 1)
        with httpx.Client(timeout=30) as client:
            self.login(client)
            response = client.get(self.native + '/api/algorithm')
            print('Record-growth observation:', json.dumps({'bytes': path.stat().st_size,
                'records': 2051, 'native_climb_points': len(expected['algorithms'][0]['climb']),
                'managed_status': response.status_code}))
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json(), expected)

    def test_dense_activity_tail_preserves_native_folding_above_record_cap(self):
        self.seed()
        path = self.root / 'LIFEOS/MEMORY/OBSERVABILITY/tool-activity.jsonl'
        row = path.read_text()
        path.write_text(row * 2100)
        self.assertLess(path.stat().st_size, 512 * 1024)
        with httpx.Client(timeout=30) as client:
            self.login(client)
            response = client.get(self.native + '/api/algorithm')
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json(), self.original('/api/algorithm'))

    def test_large_history_retains_native_movement_deduplication_and_series_eviction(self):
        path = self.history(5000)
        now = (datetime.now(timezone.utc) - timedelta(minutes=2)).isoformat()
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        for index in range(510):
            rows.append({'ts': now, 'op': 'upsert', 'slug': 'synthetic-unused-' + str(index),
                'fields': {'progress': '1/2'}})
        rows.extend([{'ts': now, 'op': 'upsert', 'slug': 'synthetic-run',
            'fields': {'progress': '2/2'}}] * 1000)
        path.write_text('\n'.join(json.dumps(row) for row in rows) + '\n')
        with httpx.Client(timeout=30) as client:
            self.login(client)
            started = time.monotonic()
            response = client.get(self.native + '/api/algorithm')
            elapsed = time.monotonic() - started
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json(), self.original('/api/algorithm'))
            self.assertEqual(len(response.json()['algorithms'][0]['climb']), 2)
            print('Streamed large-history response seconds:', round(elapsed, 6))

    def test_private_and_retired_records_do_not_change_large_history_progress(self):
        memory = self.fixture.fixture.fixture.fixture.fixture.memory
        saved = memory.remember(OWNER, category='principal', content='RULE: SyntheticRetiredMovement',
            title='', project='', request_id='history-retained')
        memory.forget(OWNER, saved['reference'], 'history-forget')
        path = self.history(5000)
        now = datetime.now(timezone.utc).isoformat()
        rows = [
            {'ts': now, 'op': 'upsert', 'slug': 'synthetic-run', 'fields': {'progress': '1/2'}},
            {'ts': now, 'op': 'upsert', 'slug': 'synthetic-run', 'fields': {'progress': '99/99'},
             'note': '{"text":"\\u003cprivate\\u003eSyntheticPrivateMovement\\u003c/private\\u003e"}'},
            {'ts': now, 'op': 'upsert', 'slug': 'synthetic-run', 'fields': {'progress': '98/98'},
             'note': 'SyntheticRetiredMovement'},
            {'ts': now, 'op': 'upsert', 'slug': 'synthetic-run', 'fields': {'progress': '2/2'}},
        ]
        with path.open('a') as stream: stream.write('\n'.join(json.dumps(row) for row in rows) + '\n')
        original = path.read_bytes()
        with httpx.Client(timeout=30) as client:
            self.login(client)
            response = client.get(self.native + '/api/algorithm')
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual([(point['done'], point['total']) for point in response.json()['algorithms'][0]['climb']], [(1, 2), (2, 2)])
            self.assertNotIn('SyntheticPrivateMovement', response.text)
            self.assertNotIn('SyntheticRetiredMovement', response.text)
        self.assertEqual(path.read_bytes(), original)

    def test_torn_utf8_activity_waits_until_its_writer_completes_the_record(self):
        self.seed()
        path = self.root / 'LIFEOS/MEMORY/OBSERVABILITY/tool-activity.jsonl'
        row = json.loads(path.read_text())
        row['tool_name'] = 'Agent'
        row['note'] = 'Synthetic café'
        complete = (json.dumps(row, ensure_ascii=False) + '\n').encode()
        cut = complete.index(b'\xc3') + 1
        with path.open('ab') as stream: stream.write(complete[:cut])
        observed = subprocess.run([sys.executable, str(Path(__file__).with_name('memory_operational_history_process.py')),
            str(self.fixture.configuration.path), 'decode'], capture_output=True, text=True, timeout=30,
            env=dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1])))
        self.assertEqual(observed.returncode, 0, observed.stderr)
        self.assertEqual(observed.stderr, '')
        print('Torn UTF-8 source observation:', observed.stdout.strip())
        with httpx.Client(timeout=30) as client:
            self.login(client)
            response = client.get(self.native + '/api/algorithm')
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json(), self.original('/api/algorithm'))
            self.assertEqual(response.json()['algorithms'][0]['activity']['lastTool'], 'Write')
            with path.open('ab') as stream: stream.write(complete[cut:])
            response = client.get(self.native + '/api/algorithm')
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()['algorithms'][0]['activity']['lastTool'], 'Agent')

    def test_snapshot_descriptor_is_read_only_and_tampering_withholds_response(self):
        self.seed()
        result = subprocess.run([sys.executable, str(Path(__file__).with_name('memory_operational_history_process.py')),
            str(self.fixture.configuration.path), 'tamper'], capture_output=True, text=True, timeout=30,
            env=dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1])))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        self.assertEqual(json.loads(result.stdout), {'rendered': True, 'anonymous': True, 'readonly': True, 'withheld': True})

    def test_process_death_leaves_original_logs_and_no_named_snapshot(self):
        self.seed()
        path = self.root / 'LIFEOS/MEMORY/STATE/work-events.jsonl'
        before = path.read_bytes(), path.stat().st_mtime_ns
        result = subprocess.run([sys.executable, str(Path(__file__).with_name('memory_operational_history_process.py')),
            str(self.fixture.configuration.path), 'exit'], capture_output=True, text=True, timeout=30,
            env=dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1])))
        self.assertEqual(result.returncode, 86, result.stderr)
        self.assertEqual(result.stderr, '')
        self.assertEqual(json.loads(result.stdout), {'rendered': True, 'anonymous': True, 'readonly': True})
        self.assertEqual((path.read_bytes(), path.stat().st_mtime_ns), before)
        with httpx.Client(timeout=30) as client:
            self.login(client)
            response = client.get(self.native + '/api/algorithm')
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json(), self.original('/api/algorithm'))

    def test_history_changes_and_revocation_during_batch_admission_withhold_result(self):
        for mode in ('batch', 'metadata', 'authority'):
            with self.subTest(mode=mode):
                self.history(5000)
                result = subprocess.run([sys.executable, str(Path(__file__).with_name('memory_operational_history_process.py')),
                    str(self.fixture.configuration.path), mode], capture_output=True, text=True, timeout=30,
                    env=dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1])))
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stderr, '')
                self.assertEqual(json.loads(result.stdout), {'validated': True, 'withheld': True})

    def test_named_pipe_or_public_native_snapshot_descriptors_refuse(self):
        memory = self.fixture.fixture.fixture.fixture.fixture.memory
        named = self.fixture.home / 'named-snapshot.jsonl'
        named.write_text('Synthetic named snapshot')
        named.chmod(0o600)
        with named.open('rb') as stream:
            with self.assertRaisesRegex(MemoryUnavailable, 'anonymous private owner snapshot'):
                memory._native('operational_view', sources=[], target='/api/algorithm',
                    history_descriptor=stream.fileno(), source_descriptors=(stream.fileno(),))
        read, write = os.pipe()
        try:
            with self.assertRaisesRegex(MemoryUnavailable, 'anonymous private owner snapshot'):
                memory._native('operational_view', sources=[], target='/api/algorithm',
                    history_descriptor=read, source_descriptors=(read,))
        finally:
            os.close(read)
            os.close(write)
        with tempfile.TemporaryFile('w+b') as stream:
            os.fchmod(stream.fileno(), 0o644)
            with self.assertRaisesRegex(MemoryUnavailable, 'anonymous private owner snapshot'):
                memory._native('operational_view', sources=[], target='/api/algorithm',
                    history_descriptor=stream.fileno(), source_descriptors=(stream.fileno(),))

    def test_crlf_history_review_preserves_native_fields_and_original_bytes(self):
        self.seed()
        path = self.root / 'LIFEOS/MEMORY/STATE/work-events.jsonl'
        path.write_bytes(path.read_bytes().replace(b'\n', b'\r\n'))
        before = path.read_bytes()
        with httpx.Client(timeout=30) as client:
            self.login(client)
            response = client.get(self.native + '/api/algorithm')
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json(), self.original('/api/algorithm'))
        self.assertEqual(path.read_bytes(), before)

    def test_native_history_keeps_inherited_snapshot_live_until_response(self):
        sources = self.seed()
        memory = self.fixture.fixture.fixture.fixture.fixture.memory
        frame = json.dumps({'relative': 'LIFEOS/MEMORY/STATE/work-events.jsonl',
            'content': sources['STATE/work-events.jsonl'].strip()}) + '\n'
        with tempfile.TemporaryFile('w+b') as output:
            output.write(frame.encode() * 5000)
            output.flush()
            with os.fdopen(os.open(f'/proc/self/fd/{output.fileno()}', os.O_RDONLY), 'rb') as reader:
                for index in range(40):
                    with self.subTest(iteration=index):
                        result = memory._native('operational_view', target='/api/algorithm',
                            sources=[{'relative': 'LIFEOS/MEMORY/STATE/work.json', 'content': sources['STATE/work.json']}],
                            history_descriptor=reader.fileno(), source_descriptors=(reader.fileno(),))
                        self.assertEqual(result['status'], 200)
                        self.assertEqual(len(result['body']['algorithms'][0]['climb']), 1)
                        self.assertEqual(os.fstat(reader.fileno()).st_nlink, 0)

    def test_native_renderer_preserves_borrowed_descriptor_after_stream_cleanup(self):
        self.seed()
        module = self.root / 'LIFEOS/PULSE/Observability/observability.ts'
        program = self.fixture.home / 'history-descriptor.ts'
        program.write_text('import {renderOperationalHistory} from ' + json.dumps(str(module)) + ';\n'
            'import {fstatSync} from "node:fs";\n'
            'const descriptor=Number(process.argv[2]);let rendered=false;\n'
            'try{const response=await renderOperationalHistory([],descriptor);rendered=response.status===200;}catch{}\n'
            'await new Promise<void>(resolve=>setImmediate(resolve));\n'
            'let alive=true;try{fstatSync(descriptor);}catch{alive=false;}\n'
            'console.log(JSON.stringify({rendered,alive}));\n')
        frame = json.dumps({'relative': 'LIFEOS/MEMORY/STATE/work-events.jsonl',
            'content': '{"op":"upsert","slug":"synthetic","ts":"2026-10-08T00:00:00Z","fields":{"progress":"1/2"}}'}) + '\n'
        with tempfile.TemporaryFile('w+b') as output:
            output.write(frame.encode() * 5000)
            output.flush()
            with os.fdopen(os.open(f'/proc/self/fd/{output.fileno()}', os.O_RDONLY), 'rb') as reader:
                for index in range(12):
                    with self.subTest(iteration=index):
                        result = subprocess.run(['bun', '--no-install', str(program), str(reader.fileno())],
                            capture_output=True, text=True, timeout=30, pass_fds=(reader.fileno(),),
                            env=dict(os.environ, HOME=str(self.fixture.home), LIFEOS_MEMORY_INTERNAL='1'))
                        self.assertEqual(result.returncode, 0, result.stderr)
                        self.assertEqual(result.stderr, '')
                        self.assertEqual(json.loads(result.stdout), {'rendered': True, 'alive': True})

    def test_multi_megabyte_history_preserves_native_climb_before_any_tail_window(self):
        path = self.history(5000, padding=100)
        self.assertGreater(path.stat().st_size, 1024 * 1024)
        expected = self.original('/api/algorithm')
        self.assertEqual(len(expected['algorithms'][0]['climb']), 1)
        with httpx.Client(timeout=30) as client:
            self.login(client)
            response = client.get(self.native + '/api/algorithm')
            print('Byte-growth observation:', json.dumps({'bytes': path.stat().st_size,
                'records': 5001, 'native_climb_points': len(expected['algorithms'][0]['climb']),
                'managed_status': response.status_code}))
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json(), expected)


if __name__ == '__main__':
    unittest.main()
