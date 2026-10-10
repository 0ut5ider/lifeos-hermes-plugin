# ABOUTME: Checks native Conduit read responses and first-read configuration publication.
# ABOUTME: Uses synthetic owner events to require authenticated reads and governed initialization effects.
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

import httpx
import test_memory_pulse_relay as relay_fixture
from test_memory_native import OWNER


class MemoryConduitTests(unittest.TestCase):
    native_module = 'conduit.ts'
    setUp = relay_fixture.MemoryPulseRelayTests.setUp
    create_fixture = relay_fixture.MemoryPulseRelayTests.create_fixture
    stop_dashboard = relay_fixture.MemoryPulseRelayTests.stop_dashboard
    stop_pulse = relay_fixture.MemoryPulseRelayTests.stop_pulse
    login = relay_fixture.MemoryPulseRelayTests.login

    def native_module_name(self): return 'memory.ts'

    def original(self, target='/api/conduit/today'):
        control = Path(os.environ['LIFEOS_HARVEST_CONTROL_SOURCE'])
        script = ('import {handleRequest} from ' + json.dumps(str(control / 'LIFEOS/PULSE/modules/conduit.ts'))
            + ';const target=' + json.dumps(target) + ';const response=await handleRequest(new Request("http://localhost"+target),'
            + 'new URL("http://localhost"+target).pathname);console.log(await response.text());')
        result = subprocess.run(['bun', '--no-install', '-e', script], capture_output=True, text=True,
            timeout=30, env=dict(os.environ, HOME=str(self.fixture.home), CLAUDE_CONFIG_DIR=str(self.root)))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        return json.loads(result.stdout)

    @staticmethod
    def stable(body):
        if isinstance(body, dict): return {k: MemoryConduitTests.stable(v) for k, v in body.items() if k != 'generatedAt'}
        if isinstance(body, list): return [MemoryConduitTests.stable(v) for v in body]
        return body

    def put(self, name, body):
        path = self.root / 'LIFEOS/USER/CONDUIT' / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(body))
        return path

    def seed(self):
        date = datetime.now().strftime('%Y-%m-%d')
        path = self.root / 'LIFEOS/USER/CONDUIT/events' / (date + '.jsonl')
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({'ts': datetime.now(timezone.utc).isoformat(), 'type': 'app-focus',
            'source': 'synthetic', 'app': 'SyntheticConduitCurrent', 'detail': {'intervalSec': 120}}) + '\n')
        return path

    def test_original_first_read_writes_native_defaults_and_preserves_daily_fields(self):
        config = self.root / 'LIFEOS/USER/CONDUIT/config.json'
        self.assertFalse(config.exists())
        self.seed()
        body = self.original()
        self.assertTrue(config.is_file())
        defaults = json.loads(config.read_text())
        self.assertEqual(defaults['pollIntervalSec'], 120)
        self.assertFalse(defaults['sources']['github'])
        self.assertEqual(defaults['repos'], [])
        self.assertEqual(body['blocks'][0]['label'], 'SyntheticConduitCurrent')
        self.assertEqual(body['totalMinutes'], 2)
        before = (config.read_bytes(), config.stat().st_mtime_ns)
        self.original()
        self.assertEqual((config.read_bytes(), config.stat().st_mtime_ns), before)

    def test_anonymous_first_read_refuses_before_native_config_creation(self):
        self.seed()
        config = self.root / 'LIFEOS/USER/CONDUIT/config.json'
        response = httpx.get(self.native + '/api/conduit/today')
        self.assertEqual(response.status_code, 401, response.text[:300])
        self.assertEqual(response.headers.get('cache-control'), 'no-store')
        self.assertFalse(config.exists())
        self.assertNotIn('SyntheticConduitCurrent', response.text)

    def test_owner_first_read_publishes_identical_native_defaults_privately(self):
        self.seed()
        config = self.root / 'LIFEOS/USER/CONDUIT/config.json'
        self.original()
        expected = config.read_bytes()
        config.unlink()
        with httpx.Client(timeout=30) as client:
            self.login(client)
            response = client.get(self.native + '/api/conduit/today')
            self.assertEqual(response.status_code, 200, response.text[:300])
            self.assertEqual(response.headers.get('cache-control'), 'no-store')
            self.assertEqual(config.read_bytes(), expected)
            self.assertEqual(config.stat().st_mode & 0o777, 0o600)
            actual = response.json()
            actual.pop('generatedAt')
            original = self.original()
            original.pop('generatedAt')
            self.assertEqual(actual, original)

    def test_original_recent_insight_sources_and_missing_characterization(self):
        self.seed()
        self.put('daily/2026-10-07.json', {'date': '2026-10-07', 'label': 'SyntheticConduitPast'})
        self.put('daily/2026-10-08.json', {'date': '2026-10-08', 'label': 'SyntheticConduitNewer'})
        self.assertEqual(self.original('/api/conduit/recent?days=1')[0]['label'], 'SyntheticConduitNewer')
        insight = self.put('insights/2026-10-07.json', {'date': '2026-10-07', 'model': 'synthetic',
            'contentTypes': [{'label': 'SyntheticConduitInsight'}], 'narrative': 'Synthetic read'})
        self.assertTrue(self.original('/api/conduit/insight')['available'])
        insight.write_text('{"contentTypes":[],"model":"(failed)","narrative":"Synthetic failure"}')
        self.assertFalse(self.original('/api/conduit/insight')['available'])
        insight.write_text('{"contentTypes":')
        self.assertEqual(self.original('/api/conduit/insight')['narrative'], 'Insight file unreadable.')
        insight.unlink()
        self.assertFalse(self.original('/api/conduit/insight')['available'])
        self.assertEqual(self.original('/api/conduit/status')['details']['eventsToday'], 1)
        self.assertEqual(self.original('/api/conduit/sources')['pollIntervalSec'], 120)

    def test_all_admitted_read_routes_preserve_native_fields(self):
        self.seed()
        self.put('daily/2026-10-07.json', {'date': '2026-10-07', 'label': 'SyntheticConduitPast'})
        self.put('daily/2026-10-08.json', {'date': '2026-10-08', 'label': 'SyntheticConduitNewer'})
        self.put('insights/2026-10-07.json', {'date': '2026-10-07', 'model': 'synthetic',
            'contentTypes': [{'label': 'SyntheticConduitInsight'}], 'narrative': 'Synthetic read'})
        with httpx.Client(timeout=30) as client:
            self.login(client)
            for suffix in ('', '/', '/today', '/recent', '/recent?days=1', '/recent?days=90', '/sources', '/status', '/health', '/insight'):
                with self.subTest(route=suffix):
                    target = '/api/conduit' + suffix
                    response = client.get(self.native + target)
                    self.assertEqual(response.status_code, 200, response.text[:300])
                    self.assertEqual(response.headers.get('cache-control'), 'no-store')
                    self.assertEqual(self.stable(response.json()), self.stable(self.original(target)))

    def test_private_and_retired_events_do_not_contribute_labels_or_counts(self):
        path = self.seed()
        with httpx.Client(timeout=30) as client:
            self.login(client)
            for retired in (False, True):
                self.seed()
                if retired:
                    memory = self.fixture.fixture.fixture.fixture.fixture.memory
                    saved = memory.remember(OWNER, category='principal', content='RULE: SyntheticConduitCurrent',
                        title='', project='', request_id='conduit-save')
                    memory.forget(OWNER, saved['reference'], 'conduit-forget')
                else: path.write_text(path.read_text().replace('SyntheticConduitCurrent', '<private>SyntheticConduitHidden</private>'))
                self.put('config.json', {'pollIntervalSec': 120})
                for suffix in ('/today', '/status', '/sources'):
                    response = client.get(self.native + '/api/conduit' + suffix)
                    self.assertEqual(response.status_code, 200, response.text[:300])
                    self.assertNotIn('SyntheticConduitCurrent', response.text)
                    self.assertNotIn('SyntheticConduitHidden', response.text)
                self.assertEqual(client.get(self.native + '/api/conduit/status').json()['details']['eventsToday'], 0)

    def test_excluded_current_insight_cannot_use_older_fallback(self):
        self.seed()
        self.put('insights/2026-10-01.json', {'contentTypes': ['SyntheticConduitOlder'], 'model': 'synthetic'})
        self.put('insights/' + datetime.now().strftime('%Y-%m-%d') + '.json',
            {'contentTypes': ['<private>SyntheticConduitHidden</private>'], 'model': 'synthetic'})
        with httpx.Client(timeout=30) as client:
            self.login(client)
            response = client.get(self.native + '/api/conduit/insight')
            self.assertEqual(response.status_code, 503, response.text[:300])
            self.assertNotIn('SyntheticConduitOlder', response.text)
            self.assertNotIn('SyntheticConduitHidden', response.text)

    def test_current_owner_origin_bearer_and_connector_govern_delivery(self):
        self.seed()
        with httpx.Client(timeout=30) as client:
            self.login(client)
            self.assertEqual(client.get(self.native + '/api/conduit/today').status_code, 200)
            self.assertEqual(client.get(self.native + '/api/conduit/today', headers={'Origin': 'https://untrusted.invalid'}).status_code, 403)
            self.assertEqual(client.get(self.native + '/api/conduit/today', headers={'Authorization': 'Bearer invalid'}).status_code, 401)
            self.fixture.configuration.update(lambda value: value['accounts'].clear())
            self.assertEqual(client.get(self.native + '/api/conduit/today').status_code, 403)
            (self.root / 'LIFEOS/USER/CONFIG/memory-access.json').unlink()
            self.assertEqual(client.get(self.native + '/api/conduit/today').status_code, 503)

    def test_redirected_invalid_and_oversize_config_refuse(self):
        with httpx.Client(timeout=30) as client:
            self.login(client)
            for mode in ('symlink', 'hardlink', 'utf8', 'oversize'):
                with self.subTest(mode=mode):
                    path = self.root / 'LIFEOS/USER/CONDUIT/config.json'
                    if path.exists() or path.is_symlink(): path.unlink()
                    path = self.put('config.json', {'pollIntervalSec': 120})
                    if mode in ('symlink', 'hardlink'):
                        outside = self.fixture.home / 'conduit-outside'
                        outside.write_bytes(path.read_bytes())
                        path.unlink()
                        if mode == 'symlink': path.symlink_to(outside)
                        else: os.link(outside, path)
                    elif mode == 'utf8': path.write_bytes(b'\xff')
                    else: path.write_bytes(b'x' * (256 * 1024 + 1))
                    self.assertEqual(client.get(self.native + '/api/conduit/today').status_code, 503)

    def test_unknown_methods_and_selectors_refuse_without_initialization(self):
        with httpx.Client(timeout=30) as client:
            self.login(client)
            for method, suffix, code in (('POST', '/today', 405), ('GET', '/today?owner=other', 400),
                    ('GET', '/recent?days=0', 400), ('GET', '/recent?days=91', 400),
                    ('GET', '/recent?days=01', 400), ('GET', '/unknown', 404),
                    ('GET', '/insight/build', 405)):
                response = client.request(method, self.native + '/api/conduit' + suffix)
                self.assertEqual(response.status_code, code, response.text[:300])
                self.assertEqual(response.headers.get('cache-control'), 'no-store')
            self.assertFalse((self.root / 'LIFEOS/USER/CONDUIT/config.json').exists())

    def test_complete_event_log_retains_native_counts_without_tail_truncation(self):
        path = self.seed()
        line = path.read_text()
        path.write_text(line * 8001)
        self.assertGreater(path.stat().st_size, 1024 * 1024)
        with httpx.Client(timeout=30) as client:
            self.login(client)
            response = client.get(self.native + '/api/conduit/status')
            self.assertEqual(response.status_code, 200, response.text[:300])
            self.assertEqual(response.json()['details']['eventsToday'], 8001)

    def test_exact_review_preserves_safe_old_config_and_event_bytes(self):
        from lifeos_hook_bridge.memory_source_review import preview, approve
        paths = [self.seed(), self.put('config.json', {'pollIntervalSec': 120})]
        memory = self.fixture.fixture.fixture.fixture.fixture.memory
        saved = memory.remember(OWNER, category='principal', content='RULE: Synthetic unrelated Conduit retirement',
            title='', project='', request_id='conduit-review-save')
        memory.forget(OWNER, saved['reference'], 'conduit-review-forget')
        for path in paths: os.utime(path, (1, 1))
        before = [(p.read_bytes(), p.stat().st_mtime_ns) for p in paths]
        names = [p.relative_to(self.root).as_posix() for p in paths]
        with httpx.Client(timeout=30) as client:
            self.login(client)
            self.assertEqual(client.get(self.native + '/api/conduit/today').status_code, 503)
            selected = preview(memory, OWNER, names)
            self.assertTrue(all(row['accepted'] for row in selected['sources']), selected)
            self.assertEqual(approve(memory, OWNER, names, selected['signature'])['status'], 'committed')
            response = client.get(self.native + '/api/conduit/today')
            self.assertEqual(response.status_code, 200, response.text[:300])
            self.assertEqual(response.json()['blocks'][0]['label'], 'SyntheticConduitCurrent')
        self.assertEqual([(p.read_bytes(), p.stat().st_mtime_ns) for p in paths], before)

    def test_actual_render_rechecks_sources_selection_descriptor_and_authority(self):
        configuration = self.fixture.configuration.path.read_bytes()
        for mode in ('source', 'metadata', 'created', 'authority', 'descriptor', 'selection'):
            with self.subTest(mode=mode):
                self.fixture.configuration.path.write_bytes(configuration)
                path = self.seed()
                self.put('config.json', {'pollIntervalSec': 120})
                target = '/api/conduit/today'
                if mode == 'created': path.unlink()
                if mode == 'selection':
                    path = self.put('daily/2026-10-08.json', {'label': 'SyntheticConduitCurrent'})
                    target = '/api/conduit/recent'
                result = subprocess.run([sys.executable, str(Path(__file__).with_name('memory_conduit_process.py')),
                    str(self.fixture.configuration.path), target, path.relative_to(self.root).as_posix(), mode],
                    capture_output=True, text=True, timeout=30,
                    env=dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1])))
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stderr, '')
                self.assertEqual(json.loads(result.stdout), {'rendered': True, 'withheld': True})

    def test_repeat_and_concurrent_initialization_keep_one_native_publication(self):
        self.seed()
        with httpx.Client(timeout=30) as client:
            self.login(client)
            with ThreadPoolExecutor(max_workers=3) as pool:
                responses = list(pool.map(lambda _: client.get(self.native + '/api/conduit/today'), range(3)))
            self.assertTrue(any(response.status_code == 200 for response in responses))
            self.assertTrue(all(response.status_code in (200, 503) for response in responses),
                [response.status_code for response in responses])
            config = self.root / 'LIFEOS/USER/CONDUIT/config.json'
            before = (config.read_bytes(), config.stat().st_mtime_ns)
            for _ in range(2): self.assertEqual(client.get(self.native + '/api/conduit/today').status_code, 200)
            self.assertEqual((config.read_bytes(), config.stat().st_mtime_ns), before)
        memory = self.fixture.fixture.fixture.fixture.fixture.memory
        with memory._transaction() as connection:
            rows = connection.execute("SELECT receipt FROM operations WHERE request_id LIKE 'conduit-initialize-%'").fetchall()
            self.assertEqual(sum(json.loads(row['receipt'])['status'] == 'committed' for row in rows), 1)

    def test_failed_publication_recovers_before_retry_and_keeps_later_edit(self):
        self.seed()
        for mode in ('interrupted', 'later-edit'):
            with self.subTest(mode=mode):
                config = self.root / 'LIFEOS/USER/CONDUIT/config.json'
                config.unlink(missing_ok=True)
                result = subprocess.run([sys.executable, str(Path(__file__).with_name('memory_conduit_publication_process.py')),
                    str(self.fixture.configuration.path), mode], capture_output=True, text=True, timeout=30,
                    env=dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1])))
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stderr, '')
                actual = json.loads(result.stdout)
                self.assertTrue(actual['published'])
                self.assertTrue(actual['withheld'])
                self.assertTrue(actual['journaled'])
                if mode == 'interrupted':
                    self.assertTrue(actual['recovered_absence'])
                    self.assertTrue(actual['retried'])
                    self.assertTrue(actual['private'])
                else:
                    self.assertTrue(actual['recovery_refuses_later_edit'])
                    self.assertTrue(actual['later_edit_preserved'])
        # The synthetic later edit deliberately leaves an unresolved recovery journal in this disposable fixture.

    def test_anonymous_generation_refuses_and_owner_generation_stays_staged(self):
        self.seed()
        self.assertEqual(httpx.post(self.native + '/api/conduit/insight/build').status_code, 401)
        with httpx.Client(timeout=30) as client:
            self.login(client)
            response = client.post(self.native + '/api/conduit/insight/build')
            self.assertEqual(response.status_code, 503, response.text[:300])
            self.assertEqual(response.headers.get('cache-control'), 'no-store')
        self.assertFalse((self.root / 'LIFEOS/USER/CONDUIT/insights').exists())
        self.assertFalse((self.root / 'LIFEOS/USER/CONDUIT/config.json').exists())

    def test_non_initializing_routes_do_not_write_defaults(self):
        with httpx.Client(timeout=30) as client:
            self.login(client)
            for suffix in ('/recent', '/insight', '/status', '/health'):
                response = client.get(self.native + '/api/conduit' + suffix)
                self.assertEqual(response.status_code, 200, response.text[:300])
                self.assertFalse((self.root / 'LIFEOS/USER/CONDUIT/config.json').exists())


if __name__ == '__main__': unittest.main()
