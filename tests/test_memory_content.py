# ABOUTME: Characterizes the native Conveyor board fold and content stream on real HTTP handlers.
# ABOUTME: Requires current owner admission before full ledger reads and manual writer actions.
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import select
import subprocess
import sys
import unittest

import httpx
import test_memory_pulse_relay as relay_fixture
from test_memory_native import OWNER

EVENTS = 'LIFEOS/MEMORY/STATE/content-pipeline/events.jsonl'


class MemoryContentTests(unittest.TestCase):
    native_module = 'content.ts'
    create_fixture = relay_fixture.MemoryPulseRelayTests.create_fixture
    stop_dashboard = relay_fixture.MemoryPulseRelayTests.stop_dashboard
    stop_pulse = relay_fixture.MemoryPulseRelayTests.stop_pulse
    login = relay_fixture.MemoryPulseRelayTests.login
    setUp = relay_fixture.MemoryPulseRelayTests.setUp

    def native_module_name(self): return 'memory.ts'

    def seed(self, marker='SyntheticContentCurrent', count=2):
        path = self.root / EVENTS
        path.parent.mkdir(parents=True, exist_ok=True)
        rows = []
        for index in range(count):
            rows.append({'v': 1, 'ts': datetime.now(timezone.utc).isoformat(), 'id': 'synthetic' + str(index),
                'op': 'upsert', 'src': 'synthetic', 'fields': {'id': 'synthetic' + str(index), 'title': marker + str(index),
                'path': '/synthetic/source-' + str(index), 'created': '2026-10-09T12:00:' + str(index % 60).zfill(2) + 'Z',
                'stage': 'review' if index == 1 else 'inbox', 'stage_status': 'pending', 'requested_run': None}})
        path.write_text('\n'.join(json.dumps(row) for row in rows) + '\n')
        return path, rows

    def original(self, target='/api/content', *, method='GET'):
        source = Path(os.environ['LIFEOS_HARVEST_CONTROL_SOURCE'])
        script = ('import {handleRequest} from ' + json.dumps(str(source / 'LIFEOS/PULSE/modules/content.ts'))
            + ';const request=new Request(' + json.dumps('http://localhost' + target) + ',{method:' + json.dumps(method) + '});'
            + 'const response=await handleRequest(request,new URL(request.url).pathname);console.log(await response.text());')
        result = subprocess.run(['bun', '--no-install', '-e', script], capture_output=True, text=True, timeout=30,
            env=dict(os.environ, HOME=str(self.fixture.home), CLAUDE_CONFIG_DIR=str(self.root), LIFEOS_DIR=str(self.root / 'LIFEOS')))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        return json.loads(result.stdout)

    @staticmethod
    def stable(body): return {key: value for key, value in body.items() if key != 'generatedAt'}

    def test_original_native_fold_order_delete_unset_and_torn_tail(self):
        path, rows = self.seed()
        rows += [{'v': 1, 'ts': '2000-01-01T00:00:00Z', 'id': 'synthetic0', 'op': 'upsert',
            'fields': {'title': 'SyntheticContentLaterInFile'}, 'unset': ['requested_run'], 'src': 'synthetic'},
            {'v': 1, 'ts': '2000-01-01T00:00:00Z', 'id': 'synthetic1', 'op': 'delete', 'src': 'synthetic'}]
        path.write_text('\n'.join(json.dumps(row) for row in rows) + '\ncorrupt middle\n{')
        original = self.original()
        self.assertEqual(original['columns'], ['inbox', 'prep', 'produce', 'review', 'publishing', 'done'])
        self.assertEqual(original['legs'], ['youtube', 'shorts', 'social', 'omny', 'discord'])
        self.assertEqual(len(original['items']), 1)
        self.assertEqual(original['items'][0]['title'], 'SyntheticContentLaterInFile')
        self.assertNotIn('requested_run', original['items'][0])
        self.assertEqual(original['counts']['inbox'], 1)
        self.assertEqual(original['counts']['review'], 0)
        self.assertEqual(self.original('/api/content/status')['details']['items'], 1)

    def test_anonymous_board_status_and_stream_refuse_before_personal_reads(self):
        path, _ = self.seed()
        os.utime(path, (1, 1))
        for target in ('', '/status', '/stream'):
            with self.subTest(target=target):
                with httpx.stream('GET', self.native + '/api/content' + target, timeout=20) as response:
                    self.assertEqual(response.status_code, 401)
                    self.assertEqual(response.headers.get('cache-control'), 'no-store')
                    self.assertNotIn('SyntheticContentCurrent', response.read().decode())
        self.assertEqual(path.stat().st_atime_ns, 1000000000)

    def test_owner_complete_board_and_status_match_actual_native_fold(self):
        self.seed()
        with httpx.Client(timeout=30) as client:
            self.login(client)
            for target in ('', '/', '/status'):
                response = client.get(self.native + '/api/content' + target)
                self.assertEqual(response.status_code, 200, response.text[:250])
                self.assertEqual(response.headers.get('cache-control'), 'no-store')
                self.assertEqual(self.stable(response.json()), self.stable(self.original('/api/content' + target)))

    def test_complete_history_exceeds_one_mib_without_losing_first_items(self):
        path, _ = self.seed(count=4001)
        self.assertGreater(path.stat().st_size, 1024 * 1024)
        with httpx.Client(timeout=60) as client:
            self.login(client)
            response = client.get(self.native + '/api/content')
            self.assertEqual(response.status_code, 200, response.text[:250])
            self.assertEqual(len(response.json()['items']), 4001)
            self.assertEqual(self.stable(response.json()), self.stable(self.original()))

    def test_excluded_later_event_refuses_whole_fold_instead_of_resurrecting_older_item(self):
        path, rows = self.seed()
        rows.append({'v': 1, 'ts': datetime.now(timezone.utc).isoformat(), 'id': 'synthetic0', 'op': 'upsert',
            'src': 'synthetic', 'fields': {'title': '<private>SyntheticContentHidden</private>'}})
        path.write_text('\n'.join(json.dumps(row) for row in rows) + '\n')
        with httpx.Client(timeout=30) as client:
            self.login(client)
            for target in ('', '/status'):
                response = client.get(self.native + '/api/content' + target)
                self.assertEqual(response.status_code, 503, response.text[:250])
                self.assertNotIn('SyntheticContent', response.text)

    def test_current_authority_origin_bearer_and_connector_govern_delivery(self):
        self.seed()
        with httpx.Client(timeout=30) as client:
            self.login(client)
            self.assertEqual(client.get(self.native + '/api/content').status_code, 200)
            self.assertEqual(client.get(self.native + '/api/content', headers={'Origin': 'https://untrusted.invalid'}).status_code, 403)
            self.assertEqual(client.get(self.native + '/api/content', headers={'Authorization': 'Bearer invalid'}).status_code, 401)
            self.fixture.configuration.update(lambda value: value['accounts'].clear())
            self.assertEqual(client.get(self.native + '/api/content').status_code, 403)
            (self.root / 'LIFEOS/USER/CONFIG/memory-access.json').unlink()
            self.assertEqual(client.get(self.native + '/api/content').status_code, 503)

    def test_manual_actions_authenticate_before_publication_or_disposal(self):
        path, _ = self.seed()
        before = path.read_bytes()
        with httpx.Client(timeout=30) as client:
            # Owner admission precedes run publication and source disposal.
            self.assertEqual(client.get(self.native + '/api/content/status').status_code, 401)
            for method, target in (('DELETE', '/api/content/synthetic0'), ('POST', '/api/content/synthetic0/run')):
                self.assertEqual(client.request(method, self.native + target).status_code, 401)
            self.login(client)
            for method, target, code in (('DELETE', '/api/content/synthetic0', 503), ('POST', '/api/content/synthetic0/run', 200)):
                response = client.request(method, self.native + target)
                self.assertEqual(response.status_code, code, response.text[:250])
                self.assertEqual(response.headers.get('cache-control'), 'no-store')
                if method == 'DELETE': self.assertEqual(path.read_bytes(), before)
            for method, target, code in (('POST', '/api/content', 405), ('GET', '/api/content?root=other', 400),
                    ('GET', '/api/content/unsupported/path', 404)):
                self.assertEqual(client.request(method, self.native + target).status_code, code)
        self.assertTrue(path.read_bytes().startswith(before))

    def test_stream_current_owner_frames_recheck_private_updates_and_revocation(self):
        path, _ = self.seed()
        with httpx.Client(timeout=20) as client:
            self.login(client)
            for mode in ('private', 'authority'):
                self.seed()
                with client.stream('GET', self.native + '/api/content/stream') as response:
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response.headers.get('cache-control'), 'no-store')
                    frames = response.iter_lines()
                    line = next(line for line in frames if line.startswith('data: '))
                    initial = json.loads(line[6:])
                    self.assertEqual(self.stable(initial), self.stable(self.original()))
                    if mode == 'private': self.seed('<private>SyntheticContentStreamHidden</private>')
                    else: self.fixture.configuration.update(lambda value: value['accounts'].clear())
                    remaining = list(frames)
                    self.assertNotIn('SyntheticContentStreamHidden', '\n'.join(remaining))
                    self.assertFalse(any(line.startswith('data: ') for line in remaining))

    def test_actual_render_rechecks_source_inode_creation_descriptor_and_authority(self):
        configuration = self.fixture.configuration.path.read_bytes()
        for mode in ('source', 'metadata', 'created', 'descriptor', 'authority'):
            with self.subTest(mode=mode):
                self.fixture.configuration.path.write_bytes(configuration)
                path, _ = self.seed()
                if mode == 'created': path.unlink()
                result = subprocess.run([sys.executable, str(Path(__file__).with_name('memory_content_process.py')),
                    str(self.fixture.configuration.path), mode], capture_output=True, text=True, timeout=30)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stderr, '')
                self.assertEqual(json.loads(result.stdout), {'rendered': True, 'withheld': True})

    def test_native_missing_corrupt_and_unterminated_valid_records_keep_original_semantics(self):
        with httpx.Client(timeout=30) as client:
            self.login(client)
            for mode in ('missing', 'corrupt', 'unterminated'):
                with self.subTest(mode=mode):
                    path, rows = self.seed()
                    if mode == 'missing': path.unlink()
                    elif mode == 'corrupt': path.write_text(json.dumps(rows[0]) + '\ncorrupt middle\n{')
                    else: path.write_text(json.dumps(rows[0]))
                    response = client.get(self.native + '/api/content')
                    self.assertEqual(response.status_code, 200, response.text[:250])
                    self.assertEqual(self.stable(response.json()), self.stable(self.original()))

    def test_redirected_excessive_event_and_invalid_utf8_refuse(self):
        with httpx.Client(timeout=30) as client:
            self.login(client)
            for mode in ('symlink', 'hardlink', 'event_limit', 'utf8'):
                with self.subTest(mode=mode):
                    path = self.root / EVENTS
                    path.unlink(missing_ok=True)
                    path, _ = self.seed()
                    if mode in ('symlink', 'hardlink'):
                        outside = self.fixture.home / 'synthetic-content-outside'
                        outside.write_bytes(path.read_bytes())
                        path.unlink()
                        if mode == 'symlink': path.symlink_to(outside)
                        else: os.link(outside, path)
                    elif mode == 'event_limit': path.write_bytes(b'x' * (256 * 1024 + 1) + b'\n')
                    else: path.write_bytes(b'\xff\n')
                    self.assertEqual(client.get(self.native + '/api/content').status_code, 503)

    def test_retired_update_refuses_incomplete_fold_and_exact_review_preserves_safe_log(self):
        from lifeos_hook_bridge.memory_source_review import preview, approve
        memory = self.fixture.fixture.fixture.fixture.fixture.memory
        path, _ = self.seed('SyntheticContentRetired')
        saved = memory.remember(OWNER, category='principal', content='RULE: SyntheticContentRetired', title='', project='', request_id='content-retired-save')
        memory.forget(OWNER, saved['reference'], 'content-retired-forget')
        with httpx.Client(timeout=30) as client:
            self.login(client)
            response = client.get(self.native + '/api/content')
            self.assertEqual(response.status_code, 503, response.text[:250])
            self.assertNotIn('SyntheticContent', response.text)
            path, _ = self.seed('SyntheticContentReviewed')
            os.utime(path, (1, 1))
            # Event timestamps and the source file both predate retirement for this review case.
            rows = [json.loads(line) for line in path.read_text().splitlines()]
            for row in rows: row['ts'] = '2000-01-01T00:00:00Z'
            path.write_text('\n'.join(json.dumps(row) for row in rows) + '\n')
            os.utime(path, (1, 1))
            before = (path.read_bytes(), path.stat().st_mtime_ns)
            self.assertEqual(client.get(self.native + '/api/content').status_code, 503)
            selected = preview(memory, OWNER, [EVENTS])
            self.assertTrue(selected['sources'][0]['accepted'], selected)
            self.assertEqual(approve(memory, OWNER, [EVENTS], selected['signature'])['status'], 'committed')
            response = client.get(self.native + '/api/content')
            self.assertEqual(response.status_code, 200, response.text[:250])
            self.assertIn('SyntheticContentReviewed', response.text)
            self.assertEqual((path.read_bytes(), path.stat().st_mtime_ns), before)

    def test_managed_direct_health_does_not_read_or_cache_personal_counts(self):
        path, _ = self.seed('<private>SyntheticContentHealthHidden</private>')
        os.utime(path, (1, 1))
        program = ('import {health} from ' + json.dumps(str(self.root / 'LIFEOS/PULSE/modules/content.ts'))
            + ';console.log(JSON.stringify(health()));')
        result = subprocess.run(['bun', '--no-install', '-e', program], capture_output=True, text=True, timeout=30,
            env=dict(os.environ, HOME=str(self.fixture.home), CLAUDE_CONFIG_DIR=str(self.root), LIFEOS_DIR=str(self.root / 'LIFEOS')))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        self.assertEqual(json.loads(result.stdout)['details']['items'], 0)
        self.assertEqual(path.stat().st_atime_ns, 1000000000)

    def test_original_native_run_and_delete_effect_characterization(self):
        path, rows = self.seed()
        source = self.root / 'LIFEOS/USER/CONTENT/synthetic.txt'
        source.parent.mkdir()
        source.write_text('Synthetic content source')
        sidecar = Path(str(source) + '.md')
        sidecar.write_text('Synthetic content sidecar')
        rows[0]['fields']['path'] = str(source)
        path.write_text('\n'.join(json.dumps(row) for row in rows) + '\n')
        artifacts = path.parent / 'artifacts/synthetic0'
        artifacts.mkdir(parents=True)
        (artifacts / 'synthetic.wav').write_bytes(b'Synthetic derivative')
        first = self.original('/api/content/synthetic0/run', method='POST')
        self.assertEqual(first, {'ok': True, 'id': 'synthetic0', 'requested_run': 'regular'})
        again = self.original('/api/content/synthetic0/run', method='POST')
        self.assertEqual(again, {'ok': True, 'id': 'synthetic0', 'already': True})
        item = next(item for item in self.original()['items'] if item['id'] == 'synthetic0')
        self.assertEqual(item['requested_run'], 'regular')
        self.assertIn('requested_at', item)
        deleted = self.original('/api/content/synthetic0', method='DELETE')
        self.assertEqual(deleted, {'ok': True, 'id': 'synthetic0', 'trashed': 2, 'artifactsRemoved': True, 'runnerKicked': False})
        self.assertFalse(source.exists())
        self.assertFalse(sidecar.exists())
        self.assertFalse(artifacts.exists())
        self.assertTrue((source.parent / '.trash/synthetic.txt').is_file())
        self.assertTrue((source.parent / '.trash/synthetic.txt.md').is_file())
        self.assertFalse(any(item['id'] == 'synthetic0' for item in self.original()['items']))
        self.assertEqual(self.original('/api/content/missing/run', method='POST'), {'error': 'no item missing'})

    def test_unprojectable_or_nested_private_update_cannot_leave_an_older_item(self):
        with httpx.Client(timeout=30) as client:
            self.login(client)
            for mode in ('field_limit', 'nested_private'):
                with self.subTest(mode=mode):
                    path, rows = self.seed()
                    fields = {str(index): '' for index in range(10001)} if mode == 'field_limit' else {
                        'title': json.dumps({'nested': '<private>SyntheticContentNestedHidden</private>'})}
                    rows.append({'v': 1, 'ts': datetime.now(timezone.utc).isoformat(), 'id': 'synthetic0',
                        'op': 'upsert', 'fields': fields, 'src': 'synthetic'})
                    path.write_text('\n'.join(json.dumps(row) for row in rows) + '\n')
                    response = client.get(self.native + '/api/content')
                    self.assertEqual(response.status_code, 503, response.text[:250])
                    self.assertNotIn('SyntheticContent', response.text)


if __name__ == '__main__': unittest.main()
