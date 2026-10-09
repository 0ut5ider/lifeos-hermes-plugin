# ABOUTME: Characterizes actual LocalIntelligence digest selection and history aggregation.
# ABOUTME: Requires authenticated current owner reads without refresh execution or raw startup reads.
from datetime import datetime, timedelta, timezone
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

PRIMARY = 'LIFEOS/USER/CUSTOMIZATIONS/SKILLS/LocalIntelligence/latest.json'
HISTORY = 'LIFEOS/MEMORY/DATA/LocalIntelligence'
FALLBACK = HISTORY + '/latest.json'


class MemoryLocalIntelligenceTests(unittest.TestCase):
    native_module = 'local-intelligence.ts'
    create_fixture = relay_fixture.MemoryPulseRelayTests.create_fixture
    stop_dashboard = relay_fixture.MemoryPulseRelayTests.stop_dashboard
    stop_pulse = relay_fixture.MemoryPulseRelayTests.stop_pulse
    login = relay_fixture.MemoryPulseRelayTests.login
    setUp = relay_fixture.MemoryPulseRelayTests.setUp

    def native_module_name(self): return 'memory.ts'

    def digest(self, marker='SyntheticLocalCurrent'):
        return {'meta': {'generated_at': datetime.now(timezone.utc).isoformat(),
            'sources_used': ['synthetic-a', 'synthetic-b'], 'sources_failed': ['synthetic-c'],
            'city': marker, 'state': 'SyntheticState'},
            'news': {'items': [{'title': marker, 'source': 'synthetic', 'url': 'https://synthetic.invalid/story',
                'date': datetime.now(timezone.utc).date().isoformat(), 'summary': marker}]}}

    def write(self, relative, value):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value) if not isinstance(value, str) else value)
        return path

    def original(self, target, *, start=False):
        source = Path(os.environ['LIFEOS_HARVEST_CONTROL_SOURCE'])
        script = ('import {handleRequest,start} from ' + json.dumps(str(source / 'LIFEOS/PULSE/modules/local-intelligence.ts'))
            + ';' + ('await start();' if start else '')
            + 'const request=new Request(' + json.dumps('http://localhost' + target) + ');'
            + 'const response=await handleRequest(request,new URL(request.url).pathname);'
            + 'console.log(JSON.stringify({status:response?.status,body:response?await response.text():null}));')
        result = subprocess.run(['bun', '--no-install', '-e', script], capture_output=True, text=True, timeout=30,
            env=dict(os.environ, HOME=str(self.fixture.home), CLAUDE_CONFIG_DIR=str(self.root)))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        lines = result.stdout.splitlines()
        if start: self.assertEqual(lines[:-1], ['[local-intelligence] started'])
        else: self.assertEqual(len(lines), 1)
        return json.loads(lines[-1])

    def test_original_primary_fallback_empty_and_status_characterization(self):
        fallback = self.write(FALLBACK, self.digest('SyntheticLocalFallback'))
        actual = self.original('/api/local-intelligence')
        self.assertEqual(json.loads(actual['body'])['meta']['city'], 'SyntheticLocalFallback')
        primary = self.write(PRIMARY, self.digest())
        actual = self.original('/api/local-intelligence')
        self.assertEqual(json.loads(actual['body'])['meta']['city'], 'SyntheticLocalCurrent')
        status = json.loads(self.original('/api/local-intelligence/status', start=True)['body'])
        self.assertTrue(status['running'])
        self.assertEqual((status['sourcesOk'], status['sourcesFailed'], status['lastRefreshOk']), (2, 1, True))
        primary.write_text('')
        self.assertEqual(self.original('/api/local-intelligence')['status'], 404)
        primary.unlink()
        fallback.unlink()
        self.assertEqual(self.original('/api/local-intelligence')['status'], 404)

    def seed_history(self):
        today = datetime.now(timezone.utc).date()
        for age, marker in ((0, 'SyntheticLocalNewest'), (1, 'SyntheticLocalOlder'), (7, 'SyntheticLocalOutsideWeek')):
            value = self.digest(marker)
            if age == 1:
                value['news']['items'].append({**value['news']['items'][0], 'title': 'SyntheticLocalNewest'})
                value['officials'] = {'items': [{**value['news']['items'][0], 'title': 'SyntheticLocalNewest'}]}
            self.write(HISTORY + '/' + (today - timedelta(days=age)).isoformat() + '_synthetic_digest.json', value)
        self.write(HISTORY + '/' + today.isoformat() + '_malformed_digest.json', '{')
        self.write(HISTORY + '/not-a-digest.json', self.digest('SyntheticLocalUnselected'))

    def test_original_native_history_windows_order_dedupe_and_bad_range(self):
        self.seed_history()
        week = json.loads(self.original('/api/local-intelligence/history')['body'])
        self.assertEqual(week['days_covered'], 2)
        self.assertEqual([item['title'] for item in week['sections']['news']['items']],
            ['SyntheticLocalNewest', 'SyntheticLocalOlder'])
        self.assertEqual(len(week['sections']['officials']['items']), 1)
        self.assertEqual(week['sections']['news']['days_with_data'], 2)
        month = json.loads(self.original('/api/local-intelligence/history?range=month')['body'])
        self.assertEqual(month['days_covered'], 3)
        self.assertEqual(self.original('/api/local-intelligence/history?range=invalid')['status'], 400)

    def test_anonymous_reads_refuse_personal_digest_and_history(self):
        self.write(PRIMARY, self.digest())
        self.seed_history()
        for target in ('', '/history', '/status'):
            with self.subTest(target=target):
                response = httpx.get(self.native + '/api/local-intelligence' + target)
                self.assertEqual(response.status_code, 401, response.text[:250])
                self.assertEqual(response.headers.get('cache-control'), 'no-store')
                self.assertNotIn('SyntheticLocal', response.text)

    def test_owner_latest_and_complete_history_preserve_native_fields(self):
        self.write(PRIMARY, self.digest())
        self.seed_history()
        # Native history ignores a malformed selected digest. Managed reads refuse incomplete JSON.
        for path in (self.root / HISTORY).glob('*malformed_digest.json'): path.unlink()
        with httpx.Client(timeout=30) as client:
            self.login(client)
            for target in ('', '/history', '/history?range=week', '/history?range=month', '/history?range=year'):
                with self.subTest(target=target):
                    response = client.get(self.native + '/api/local-intelligence' + target)
                    self.assertEqual(response.status_code, 200, response.text[:250])
                    self.assertEqual(response.headers.get('cache-control'), 'no-store')
                    original = self.original('/api/local-intelligence' + target)
                    self.assertEqual(response.json(), json.loads(original['body']))

    def test_excluded_primary_cannot_fall_back_and_private_history_refuses(self):
        primary = self.write(PRIMARY, self.digest('<private>SyntheticLocalHidden</private>'))
        self.write(FALLBACK, self.digest('SyntheticLocalFallback'))
        with httpx.Client(timeout=30) as client:
            self.login(client)
            response = client.get(self.native + '/api/local-intelligence')
            self.assertEqual(response.status_code, 503, response.text[:250])
            self.assertNotIn('SyntheticLocal', response.text)
            primary.unlink()
            self.assertEqual(client.get(self.native + '/api/local-intelligence').json()['meta']['city'], 'SyntheticLocalFallback')
            self.seed_history()
            for path in (self.root / HISTORY).glob('*malformed_digest.json'): path.unlink()
            today = datetime.now(timezone.utc).date().isoformat()
            self.write(HISTORY + '/' + today + '_private_digest.json', self.digest('<private>SyntheticLocalHidden</private>'))
            response = client.get(self.native + '/api/local-intelligence/history')
            self.assertEqual(response.status_code, 503, response.text[:250])
            self.assertNotIn('SyntheticLocalHidden', response.text)

    def test_current_authority_origin_bearer_and_connector_govern_delivery(self):
        self.write(PRIMARY, self.digest())
        with httpx.Client(timeout=30) as client:
            self.login(client)
            self.assertEqual(client.get(self.native + '/api/local-intelligence').status_code, 200)
            self.assertEqual(client.get(self.native + '/api/local-intelligence', headers={'Origin': 'https://untrusted.invalid'}).status_code, 403)
            self.assertEqual(client.get(self.native + '/api/local-intelligence', headers={'Authorization': 'Bearer invalid'}).status_code, 401)
            self.fixture.configuration.update(lambda value: value['accounts'].clear())
            self.assertEqual(client.get(self.native + '/api/local-intelligence').status_code, 403)
            (self.root / 'LIFEOS/USER/CONFIG/memory-access.json').unlink()
            self.assertEqual(client.get(self.native + '/api/local-intelligence').status_code, 503)

    def test_methods_selectors_and_refresh_refuse_before_job_execution(self):
        runs = self.root / PRIMARY
        runs = runs.parent / 'runs'
        with httpx.Client(timeout=30) as client:
            # The baseline fails on a read before it can execute the native refresh action.
            self.assertEqual(client.get(self.native + '/api/local-intelligence/status').status_code, 401)
            response = client.post(self.native + '/api/local-intelligence/refresh')
            self.assertEqual(response.status_code, 401, response.text[:250])
            self.login(client)
            for method, target, code in [('POST', '/api/local-intelligence', 405),
                    ('GET', '/api/local-intelligence?source=other', 400),
                    ('GET', '/api/local-intelligence/history?range=invalid', 400),
                    ('GET', '/api/local-intelligence/status?running=1', 400),
                    ('GET', '/api/local-intelligence/unsupported', 404)]:
                response = client.request(method, self.native + target)
                self.assertEqual(response.status_code, code, response.text[:250])
                self.assertEqual(response.headers.get('cache-control'), 'no-store')
            response = client.post(self.native + '/api/local-intelligence/refresh')
            self.assertEqual(response.status_code, 503, response.text[:250])
        self.assertFalse(runs.exists())


    def test_missing_fallback_and_primary_status_match_native_absence(self):
        with httpx.Client(timeout=30) as client:
            self.login(client)
            for value in (None, 'SyntheticLocalFallback', 'SyntheticLocalPrimary'):
                if value is not None: self.write(FALLBACK if value.endswith('Fallback') else PRIMARY, self.digest(value))
                response = client.get(self.native + '/api/local-intelligence')
                original = self.original('/api/local-intelligence')
                self.assertEqual(response.status_code, original['status'], response.text[:250])
                self.assertEqual(response.json(), json.loads(original['body']))
                self.assertEqual(response.headers.get('cache-control'), 'no-store')
                status = client.get(self.native + '/api/local-intelligence/status')
                self.assertEqual(status.status_code, 200, status.text[:250])
                # The listener is stopped until native module start is called.
                expected = json.loads(self.original('/api/local-intelligence/status')['body'])
                self.assertEqual(status.json()['latest_exists'], expected['latest_exists'])
                self.assertEqual(status.json()['latest_mtime'], expected['latest_mtime'])
                self.assertFalse(status.json()['running'])

    def test_managed_start_reads_no_digest_and_creates_no_output_directories(self):
        path = self.write(PRIMARY, self.digest('<private>SyntheticLocalStartupHidden</private>'))
        os.utime(path, (1, 1))
        runs = path.parent / 'runs'
        program = ('import {start,health} from ' + json.dumps(str(self.root / 'LIFEOS/PULSE/modules/local-intelligence.ts'))
            + ';await start();console.log(JSON.stringify(health()));')
        result = subprocess.run(['bun', '--no-install', '-e', program], capture_output=True, text=True, timeout=30,
            env=dict(os.environ, HOME=str(self.fixture.home), CLAUDE_CONFIG_DIR=str(self.root)))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        self.assertEqual(result.stdout.splitlines()[0], '[local-intelligence] started')
        health = json.loads(result.stdout.splitlines()[1])
        self.assertEqual(health['status'], 'healthy')
        self.assertIsNone(health['details']['last_refresh'])
        self.assertEqual(health['details']['sources_ok'], 0)
        self.assertFalse(runs.exists())
        self.assertEqual(path.stat().st_atime_ns, 1000000000)

    def test_started_status_uses_admitted_current_metadata_and_native_runtime(self):
        # Seed before the listener starts, then restart its actual handler with module start.
        self.write(PRIMARY, self.digest())
        self.process.terminate()
        _, error = self.process.communicate(timeout=10)
        self.assertEqual(error, '')
        program = self.fixture.home / 'pulse-local-start.ts'
        program.write_text('import {start,handleRequest} from ' + json.dumps(str(self.root / 'LIFEOS/PULSE/modules/local-intelligence.ts'))
            + ';await start();const server=Bun.serve({hostname:"127.0.0.1",port:0,async fetch(request){return await handleRequest(request,new URL(request.url).pathname)??new Response("not found",{status:404});}});console.log(server.port);')
        self.process = subprocess.Popen(['bun', '--no-install', str(program)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            env=dict(os.environ, HOME=str(self.fixture.home), CLAUDE_CONFIG_DIR=str(self.root)))
        self.assertTrue(select.select([self.process.stdout], [], [], 10)[0])
        self.assertEqual(self.process.stdout.readline().strip(), '[local-intelligence] started')
        self.assertTrue(select.select([self.process.stdout], [], [], 10)[0])
        self.native = 'http://127.0.0.1:' + self.process.stdout.readline().strip()
        with httpx.Client(timeout=30) as client:
            self.login(client)
            response = client.get(self.native + '/api/local-intelligence/status')
            self.assertEqual(response.status_code, 200, response.text[:250])
            body = response.json()
            expected = json.loads(self.original('/api/local-intelligence/status', start=True)['body'])
            self.assertTrue(body['running'])
            self.assertIsNotNone(body['startedAt'])
            self.assertEqual({k:v for k,v in body.items() if k != 'startedAt'}, {k:v for k,v in expected.items() if k != 'startedAt'})
            self.write(PRIMARY, self.digest('<private>SyntheticLocalStatusHidden</private>'))
            response = client.get(self.native + '/api/local-intelligence/status')
            self.assertEqual(response.status_code, 503, response.text[:250])
            self.assertNotIn('SyntheticLocalStatusHidden', response.text)

    def test_redirected_oversized_invalid_and_nested_private_sources_refuse(self):
        with httpx.Client(timeout=30) as client:
            self.login(client)
            for mode in ('symlink', 'hardlink', 'oversize', 'utf8', 'malformed', 'nested'):
                with self.subTest(mode=mode):
                    path = self.root / PRIMARY
                    path.unlink(missing_ok=True)
                    self.write(PRIMARY, self.digest())
                    if mode in ('symlink', 'hardlink'):
                        outside = self.fixture.home / 'synthetic-local-outside'
                        outside.write_bytes(path.read_bytes())
                        path.unlink()
                        if mode == 'symlink': path.symlink_to(outside)
                        else: os.link(outside, path)
                    elif mode == 'oversize': path.write_bytes(b'x' * (256 * 1024 + 1))
                    elif mode == 'utf8': path.write_bytes(b'\xff')
                    elif mode == 'malformed': path.write_text('{')
                    else: path.write_text('{"meta":{"city":"\\u003cprivate\\u003eSyntheticLocalHidden\\u003c/private\\u003e"}}')
                    response = client.get(self.native + '/api/local-intelligence')
                    self.assertEqual(response.status_code, 503, response.text[:250])
                    self.assertNotIn('SyntheticLocalHidden', response.text)

    def test_history_discovery_refuses_redirects_and_more_than_2048_entries(self):
        directory = self.root / HISTORY
        directory.mkdir(parents=True)
        for index in range(2049): (directory / ('synthetic-entry-' + str(index))).touch()
        with httpx.Client(timeout=30) as client:
            self.login(client)
            self.assertEqual(client.get(self.native + '/api/local-intelligence/history').status_code, 503)
            for path in directory.iterdir(): path.unlink()
            directory.rmdir()
            outside = self.fixture.home / 'synthetic-history-outside'
            outside.mkdir()
            directory.symlink_to(outside)
            self.assertEqual(client.get(self.native + '/api/local-intelligence/history').status_code, 503)

    def test_actual_render_rechecks_bytes_inode_creation_selection_and_authority(self):
        configuration = self.fixture.configuration.path.read_bytes()
        for mode in ('source', 'metadata', 'created', 'authority', 'selection'):
            with self.subTest(mode=mode):
                self.fixture.configuration.path.write_bytes(configuration)
                path = self.write(PRIMARY, self.digest())
                target = '/api/local-intelligence'
                relative = PRIMARY
                if mode == 'created': path.unlink()
                if mode == 'selection':
                    self.seed_history()
                    for malformed in (self.root / HISTORY).glob('*malformed_digest.json'): malformed.unlink()
                    target = '/api/local-intelligence/history'
                    relative = str(next((self.root / HISTORY).glob('*synthetic_digest.json')).relative_to(self.root))
                result = subprocess.run([sys.executable, str(Path(__file__).with_name('memory_local_intelligence_process.py')),
                    str(self.fixture.configuration.path), target, relative, mode], capture_output=True, text=True, timeout=30)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stderr, '')
                self.assertEqual(json.loads(result.stdout), {'rendered': True, 'withheld': True})

    def test_exact_review_admits_safe_old_digest_without_rewriting(self):
        from lifeos_hook_bridge.memory_source_review import preview, approve
        memory = self.fixture.fixture.fixture.fixture.fixture.memory
        path = self.write(PRIMARY, self.digest())
        saved = memory.remember(OWNER, category='principal', content='RULE: Synthetic unrelated local retirement',
            title='', project='', request_id='local-review-save')
        memory.forget(OWNER, saved['reference'], 'local-review-forget')
        os.utime(path, (1, 1))
        before = (path.read_bytes(), path.stat().st_mtime_ns)
        with httpx.Client(timeout=30) as client:
            self.login(client)
            self.assertEqual(client.get(self.native + '/api/local-intelligence').status_code, 503)
            selected = preview(memory, OWNER, [PRIMARY])
            self.assertTrue(selected['sources'][0]['accepted'], selected)
            self.assertEqual(approve(memory, OWNER, [PRIMARY], selected['signature'])['status'], 'committed')
            response = client.get(self.native + '/api/local-intelligence')
            self.assertEqual(response.status_code, 200, response.text[:250])
            self.assertEqual(response.json()['meta']['city'], 'SyntheticLocalCurrent')
        self.assertEqual((path.read_bytes(), path.stat().st_mtime_ns), before)

    def test_retired_primary_refuses_and_does_not_use_fallback(self):
        memory = self.fixture.fixture.fixture.fixture.fixture.memory
        self.write(PRIMARY, self.digest('SyntheticLocalRetired'))
        self.write(FALLBACK, self.digest('SyntheticLocalFallback'))
        saved = memory.remember(OWNER, category='principal', content='RULE: SyntheticLocalRetired', title='', project='', request_id='local-retired-save')
        memory.forget(OWNER, saved['reference'], 'local-retired-forget')
        with httpx.Client(timeout=30) as client:
            self.login(client)
            response = client.get(self.native + '/api/local-intelligence')
            self.assertEqual(response.status_code, 503, response.text[:250])
            self.assertNotIn('SyntheticLocal', response.text)

    def test_empty_primary_preserves_native_absence_without_fallback(self):
        primary = self.write(PRIMARY, '')
        self.write(FALLBACK, self.digest('<private>SyntheticLocalFallbackHidden</private>'))
        with httpx.Client(timeout=30) as client:
            self.login(client)
            response = client.get(self.native + '/api/local-intelligence')
            self.assertEqual(response.status_code, 404, response.text[:250])
            self.assertEqual(response.json(), json.loads(self.original('/api/local-intelligence')['body']))
            self.assertEqual(response.headers.get('cache-control'), 'no-store')
            self.assertEqual(primary.read_bytes(), b'')

    def test_unselected_old_private_history_does_not_block_native_week_window(self):
        today = datetime.now(timezone.utc).date()
        self.write(HISTORY + '/' + today.isoformat() + '_current_digest.json', self.digest())
        old = (today - timedelta(days=8)).isoformat()
        self.write(HISTORY + '/' + old + '_old_digest.json', self.digest('<private>SyntheticLocalOldHidden</private>'))
        with httpx.Client(timeout=30) as client:
            self.login(client)
            week = client.get(self.native + '/api/local-intelligence/history?range=week')
            self.assertEqual(week.status_code, 200, week.text[:250])
            self.assertEqual(week.json(), json.loads(self.original('/api/local-intelligence/history?range=week')['body']))
            month = client.get(self.native + '/api/local-intelligence/history?range=month')
            self.assertEqual(month.status_code, 503, month.text[:250])
            self.assertNotIn('SyntheticLocalOldHidden', month.text)

    def test_native_json_scalars_lists_and_null_preserve_latest_response(self):
        with httpx.Client(timeout=30) as client:
            self.login(client)
            for value in ('SyntheticLocalScalar', True, 23, 2.5, None, ['SyntheticLocalList']):
                with self.subTest(value=value):
                    self.write(PRIMARY, json.dumps(value))
                    response = client.get(self.native + '/api/local-intelligence')
                    self.assertEqual(response.status_code, 200, response.text[:250])
                    self.assertEqual(response.json(), json.loads(self.original('/api/local-intelligence')['body']))
                    self.assertEqual(response.headers.get('cache-control'), 'no-store')


if __name__ == '__main__': unittest.main()
