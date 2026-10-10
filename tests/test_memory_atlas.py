# ABOUTME: Exercises native Atlas graph delivery and collectors with disposable owner data.
# ABOUTME: Checks authentication, source admission, current authority, and retained cache behavior.
from datetime import datetime, timezone
import json
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import unittest
from dataclasses import asdict
from contextlib import closing

import httpx
import test_memory_pulse_relay as relay_fixture
from test_memory_native import OWNER, SOURCE
import test_memory_delegation as delegation_fixture


class MemoryAtlasTests(unittest.TestCase):
    native_module = 'atlas.ts'
    create_fixture = relay_fixture.MemoryPulseRelayTests.create_fixture
    native_module_name = relay_fixture.MemoryPulseRelayTests.native_module_name
    stop_dashboard = relay_fixture.MemoryPulseRelayTests.stop_dashboard
    stop_pulse = relay_fixture.MemoryPulseRelayTests.stop_pulse
    login = relay_fixture.MemoryPulseRelayTests.login

    def setUp(self):
        relay_fixture.MemoryPulseRelayTests.setUp(self)
        (self.root / 'LIFEOS/ATLAS').symlink_to(SOURCE / 'LIFEOS/ATLAS')
        self.directory = self.fixture.home / '.local/state/lifeos/atlas'
        self.directory.mkdir(parents=True)
        self.snapshot = self.directory / 'snapshot.json'
        self.gear = self.root / 'LIFEOS/USER/GEAR.md'
        self.projects = self.root / 'LIFEOS/USER/PROJECTS.md'
        self.gear.write_text('## Synthetic devices\n| **Laptop** | SyntheticAtlasDevice | Work |\n')
        self.projects.write_text('| Project | Path | URL | Deploy |\n| --- | --- | --- | --- |\n'
                                 '| SyntheticAtlasProject | /synthetic | example.invalid | local |\n')

    def seed(self, marker='SyntheticAtlasDevice'):
        self.snapshot.write_text(json.dumps({'assets': [{'display_name': marker}], 'edges': [],
            'observations': [], 'generated_at': datetime.now(timezone.utc).isoformat()}))

    def seed_graph(self, marker='SyntheticAtlasDevice', attrs=None):
        script = ('import {Store} from ' + json.dumps(str(self.root / 'LIFEOS/ATLAS/Store.ts')) + ';\n'
            'const store=new Store();store.applyRun("gear","full",' + json.dumps({'complete': True,
                'assets': [{'kind': 'device', 'key': 'gear:synthetic', 'name': marker, 'attrs': attrs or {}}], 'edges': []}) + ');\n'
            'console.log(JSON.stringify(store.insights()));store.close();')
        result = subprocess.run(['bun', '--no-install', '-e', script], capture_output=True, text=True,
            timeout=20, env=dict(os.environ, HOME=str(self.fixture.home), LIFEOS_MEMORY_INTERNAL="1"))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        metrics = json.loads(result.stdout)
        content = json.dumps(metrics, separators=(',', ':'), ensure_ascii=False)
        cache = self.root / 'LIFEOS/MEMORY/STATE/atlas-insights.json'
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps({'hash': hashlib.sha256(content.encode()).hexdigest()[:16],
            'narrative': 'SyntheticAtlasNarrative', 'generated_at': datetime.now(timezone.utc).isoformat()}))
        return metrics, cache

    def test_anonymous_cannot_read_snapshot_or_start_insights(self):
        self.seed()
        for route in ('/api/atlas', '/api/atlas/insights'):
            with self.subTest(route=route):
                response = httpx.get(self.native + route, headers={'X-LifeOS-Owner': 'owner'})
                self.assertEqual(response.status_code, 401, response.text[:300])
                self.assertEqual(response.headers.get('cache-control'), 'no-store')
                self.assertNotIn('SyntheticAtlasDevice', response.text)
        response = httpx.post(self.native + '/api/atlas/insights/regenerate')
        self.assertEqual(response.status_code, 401, response.text[:300])

    def test_owner_snapshot_fields_and_missing_source_match_native(self):
        with httpx.Client(timeout=30) as client:
            self.login(client)
            response = client.get(self.native + '/api/atlas')
            self.assertEqual(response.status_code, 200, response.text[:300])
            self.assertFalse(response.json()['available'])
            self.seed()
            before = (self.snapshot.read_bytes(), self.snapshot.stat().st_mtime_ns)
            response = client.get(self.native + '/api/atlas')
            self.assertEqual(response.status_code, 200, response.text[:300])
            result = response.json()
            self.assertTrue(result.pop('available'))
            self.assertGreaterEqual(result.pop('snapshot_age_ms'), 0)
            self.assertEqual(result, json.loads(self.snapshot.read_text()))
            self.assertEqual(response.headers.get('cache-control'), 'no-store')
            self.assertEqual((self.snapshot.read_bytes(), self.snapshot.stat().st_mtime_ns), before)

    def test_cached_snapshot_cannot_survive_private_replacement_or_retirement(self):
        self.seed()
        with httpx.Client(timeout=30) as client:
            self.login(client)
            self.assertEqual(client.get(self.native + '/api/atlas').status_code, 200)
            self.seed('<private>SyntheticAtlasHidden</private>')
            response = client.get(self.native + '/api/atlas')
            self.assertEqual(response.status_code, 503, response.text[:300])
            self.assertNotIn('SyntheticAtlasDevice', response.text)
            self.assertNotIn('SyntheticAtlasHidden', response.text)
            self.seed()
            memory = self.fixture.fixture.fixture.fixture.fixture.memory
            saved = memory.remember(OWNER, category='project', content='SyntheticAtlasDevice',
                title='Synthetic Atlas fixture', project='lab', request_id='atlas-remember')
            memory.forget(OWNER, saved['reference'], 'atlas-forget')
            response = client.get(self.native + '/api/atlas')
            self.assertEqual(response.status_code, 503, response.text[:300])
            self.assertNotIn('SyntheticAtlasDevice', response.text)

    def test_current_collector_source_exclusion_withholds_prior_snapshot(self):
        self.seed()
        with httpx.Client(timeout=30) as client:
            self.login(client)
            self.assertEqual(client.get(self.native + '/api/atlas').status_code, 200)
            self.gear.write_text('## Devices\n| **Laptop** | <private>SyntheticAtlasHidden</private> | Work |\n')
            response = client.get(self.native + '/api/atlas')
            self.assertEqual(response.status_code, 503, response.text[:300])
            self.assertNotIn('SyntheticAtlasDevice', response.text)

    def test_revocation_connector_loss_and_origin_cannot_reuse_cache(self):
        self.seed()
        with httpx.Client(timeout=30) as client:
            self.login(client)
            self.assertEqual(client.get(self.native + '/api/atlas').status_code, 200)
            response = client.get(self.native + '/api/atlas', headers={'Origin': 'https://untrusted.invalid'})
            self.assertEqual(response.status_code, 403, response.text[:300])
            response = client.get(self.native + '/api/atlas', headers={'Authorization': 'Bearer invalid'})
            self.assertEqual(response.status_code, 401, response.text[:300])
            self.fixture.configuration.update(lambda config: config['accounts'].clear())
            self.assertEqual(client.get(self.native + '/api/atlas').status_code, 403)
            (self.root / 'LIFEOS/USER/CONFIG/memory-access.json').unlink()
            response = client.get(self.native + '/api/atlas')
            self.assertEqual(response.status_code, 503, response.text[:300])
            self.assertNotIn('SyntheticAtlasDevice', response.text)

    def test_snapshot_links_invalid_encoding_and_size_refuse(self):
        with httpx.Client(timeout=30) as client:
            self.login(client)
            for mode in ('symlink', 'hardlink', 'utf8', 'oversize', 'malformed'):
                with self.subTest(mode=mode):
                    if self.snapshot.exists() or self.snapshot.is_symlink(): self.snapshot.unlink()
                    self.seed()
                    if mode in ('symlink', 'hardlink'):
                        outside = self.fixture.home / 'synthetic-atlas-outside'
                        outside.write_bytes(self.snapshot.read_bytes())
                        self.snapshot.unlink()
                        if mode == 'symlink': self.snapshot.symlink_to(outside)
                        else: os.link(outside, self.snapshot)
                    elif mode == 'utf8': self.snapshot.write_bytes(b'{"assets":[]}\xff')
                    elif mode == 'oversize': self.snapshot.write_text(' ' * (256 * 1024 + 1))
                    else: self.snapshot.write_text('{"assets":[')
                    response = client.get(self.native + '/api/atlas')
                    self.assertEqual(response.status_code, 503, response.text[:300])
                    self.assertNotIn('SyntheticAtlasDevice', response.text)

    def test_fixed_methods_selectors_and_unknown_routes_refuse(self):
        self.seed()
        with httpx.Client(timeout=30) as client:
            self.login(client)
            for method, route, status in (('POST', '/api/atlas', 405),
                    ('GET', '/api/atlas?owner=other', 400), ('GET', '/api/atlas/unsupported', 404)):
                with self.subTest(route=route):
                    response = client.request(method, self.native + route)
                    self.assertEqual(response.status_code, status, response.text[:300])
                    self.assertEqual(response.headers.get('cache-control'), 'no-store')

    def test_custom_snapshot_environment_cannot_read_another_owner_source(self):
        script = ('import {handleRequest} from ' + json.dumps(str(self.root / 'LIFEOS/PULSE/modules/atlas.ts')) + ';\n'
            'const response=await handleRequest(new Request("http://localhost/api/atlas"),"/api/atlas");\n'
            'console.log(JSON.stringify({status:response.status,body:await response.text()}));')
        outside = self.fixture.home / 'synthetic-custom-atlas.json'
        outside.write_text('{"assets":[{"display_name":"SyntheticOutsideAtlas"}]}')
        result = subprocess.run(['bun', '--no-install', '-e', script], capture_output=True, text=True,
            timeout=20, env=dict(os.environ, HOME=str(self.fixture.home), ATLAS_SNAPSHOT_PATH=str(outside)))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        response = json.loads(result.stdout)
        self.assertEqual(response['status'], 503, response)
        self.assertNotIn('SyntheticOutsideAtlas', response['body'])

    def test_admitted_insights_preserve_native_metrics_and_current_narrative(self):
        metrics, cache = self.seed_graph()
        before = (cache.read_bytes(), cache.stat().st_mtime_ns)
        with httpx.Client(timeout=30) as client:
            self.login(client)
            response = client.get(self.native + '/api/atlas/insights')
            self.assertEqual(response.status_code, 200, response.text[:300])
            self.assertEqual(response.json(), {'available': True, 'metrics': metrics,
                'narrative': 'SyntheticAtlasNarrative', 'narrative_generated_at': json.loads(cache.read_text())['generated_at'],
                'stale': False, 'generating': False})
            self.assertEqual((cache.read_bytes(), cache.stat().st_mtime_ns), before)
            cache.write_text(cache.read_text().replace('SyntheticAtlasNarrative', 'SyntheticAtlasCurrentNarrative'))
            self.assertEqual(client.get(self.native + '/api/atlas/insights').json()['narrative'], 'SyntheticAtlasCurrentNarrative')

    def test_private_graph_and_cache_refuse_counts_and_narrative(self):
        _, cache = self.seed_graph(attrs={'nested': {'text': '<private>SyntheticAtlasHidden</private>'}})
        with httpx.Client(timeout=30) as client:
            self.login(client)
            response = client.get(self.native + '/api/atlas/insights')
            self.assertEqual(response.status_code, 503, response.text[:300])
            self.assertNotIn('SyntheticAtlasNarrative', response.text)
            # Replace the entire native database with a safe actual Store before testing the separate cache source.
            for name in ('atlas.db', 'atlas.db-wal', 'atlas.db-shm'):
                (self.directory / name).unlink(missing_ok=True)
            _, cache = self.seed_graph()
            cache.write_text(cache.read_text().replace('SyntheticAtlasNarrative', '<private>SyntheticAtlasHidden</private>'))
            response = client.get(self.native + '/api/atlas/insights')
            self.assertEqual(response.status_code, 503, response.text[:300])
            self.assertNotIn('SyntheticAtlasHidden', response.text)

    def test_graph_row_limit_refuses_without_returning_truncated_metrics(self):
        import sqlite3
        self.seed_graph()
        with closing(sqlite3.connect(self.directory / 'atlas.db')) as connection, connection:
            row = connection.execute('SELECT * FROM asset').fetchone()
            values = [(i, row[1], 'gear:synthetic-' + str(i), 'SyntheticAtlasLargeGraph', *row[4:])
                      for i in range(2, 2050)]
            connection.executemany('INSERT INTO asset VALUES (?,?,?,?,?,?,?,?)', values)
        self.seed_graph()
        with httpx.Client(timeout=30) as client:
            self.login(client)
            response = client.get(self.native + '/api/atlas/insights')
            self.assertEqual(response.status_code, 503, response.text[:300])
            self.assertNotIn('census', response.text)

    def test_exact_owner_review_restores_safe_old_snapshot_and_graph(self):
        from lifeos_hook_bridge.memory_source_review import preview, approve
        from lifeos_hook_bridge.memory_atlas import SNAPSHOT, DATABASE, CACHE
        self.seed()
        _, cache = self.seed_graph()
        memory = self.fixture.fixture.fixture.fixture.fixture.memory
        saved = memory.remember(OWNER, category='principal', content='RULE: Synthetic unrelated Atlas retirement',
            title='', project='', request_id='atlas-review-unrelated')
        memory.forget(OWNER, saved['reference'], 'atlas-review-unrelated-forget')
        paths = (self.snapshot, self.directory / 'atlas.db', cache, self.gear, self.projects)
        for path in paths: os.utime(path, (1, 1))
        before = [(path.read_bytes(), path.stat().st_mtime_ns) for path in paths]
        relatives = [SNAPSHOT, DATABASE, CACHE, 'LIFEOS/USER/GEAR.md', 'LIFEOS/USER/PROJECTS.md']
        with httpx.Client(timeout=30) as client:
            self.login(client)
            self.assertEqual(client.get(self.native + '/api/atlas').status_code, 503)
            self.assertEqual(client.get(self.native + '/api/atlas/insights').status_code, 503)
            selected = preview(memory, OWNER, relatives)
            self.assertTrue(all(row['accepted'] for row in selected['sources']), selected)
            approve(memory, OWNER, relatives, selected['signature'])
            self.assertEqual(client.get(self.native + '/api/atlas').status_code, 200)
            self.assertEqual(client.get(self.native + '/api/atlas/insights').status_code, 200)
        self.assertEqual([(path.read_bytes(), path.stat().st_mtime_ns) for path in paths], before)

    def test_actual_native_render_rechecks_graph_sources_and_authority(self):
        configuration = self.fixture.configuration.path.read_bytes()
        gear = self.gear.read_bytes()
        for mode, view in (('source', 'snapshot'), ('metadata', 'snapshot'), ('created', 'snapshot'),
                ('collector', 'snapshot'), ('authority', 'snapshot'), ('graph', 'insights'),
                ('cache', 'insights'), ('authority', 'insights')):
            with self.subTest(mode=mode, view=view):
                self.fixture.configuration.path.write_bytes(configuration)
                self.gear.write_bytes(gear)
                self.seed()
                self.seed_graph()
                if mode == 'created': self.snapshot.unlink()
                result = subprocess.run([sys.executable, str(Path(__file__).with_name('memory_atlas_process.py')),
                    str(self.fixture.configuration.path), mode, view], capture_output=True, text=True, timeout=30,
                    env=dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1])))
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stderr, '')
                self.assertEqual(json.loads(result.stdout), {'rendered': True, 'withheld': True})


class MemoryAtlasCollectorTests(unittest.TestCase):
    def setUp(self):
        self.fixture = delegation_fixture.MemoryDelegationTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        (self.root / 'LIFEOS/ATLAS').symlink_to(SOURCE / 'LIFEOS/ATLAS')
        self.gear = self.root / 'LIFEOS/USER/GEAR.md'
        self.projects = self.root / 'LIFEOS/USER/PROJECTS.md'
        self.gear.write_text('## Devices\n| **Laptop** | SyntheticAtlasDevice | Work |\n')
        self.projects.write_text('| Project | Path | URL | Deploy |\n| --- | --- | --- | --- |\n'
                                 '| SyntheticAtlasProject | /synthetic | example.invalid | local |\n')
        marker = self.root / 'LIFEOS/USER/CONFIG/memory-http.json'
        marker.write_text('{"version":1,"managed":true}')
        marker.chmod(0o600)

    def collect(self, name, *, context=True, internal=False):
        script = ('import {' + name.lower() + '} from ' + json.dumps(str(
            self.root / 'LIFEOS/ATLAS/collectors' / (name + '.ts'))) + ';\nconsole.log(JSON.stringify(await '
            + name.lower() + '.collect()));')
        environment = dict(os.environ, HOME=str(self.fixture.fixture.home), BUN_CONFIG_NO_AUTO_INSTALL='1')
        environment.pop('LIFEOS_MEMORY_INTERNAL', None)
        environment.pop('LIFEOS_MEMORY_CONTEXT', None)
        if context: environment['LIFEOS_MEMORY_CONTEXT'] = json.dumps(asdict(self.fixture.context))
        if internal: environment['LIFEOS_MEMORY_INTERNAL'] = '1'
        return subprocess.run(['bun', '--no-install', '-e', script], env=environment,
            capture_output=True, text=True, timeout=20)

    def test_unbound_collectors_cannot_disclose_sources(self):
        for name in ('Gear', 'Projects'):
            with self.subTest(name=name):
                result = self.collect(name, context=False)
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertNotIn('SyntheticAtlasDevice', result.stdout + result.stderr)
                self.assertNotIn('SyntheticAtlasProject', result.stdout + result.stderr)

    def test_owner_collectors_preserve_native_assets_edges_and_absence(self):
        for name in ('Gear', 'Projects'):
            with self.subTest(name=name):
                original = self.collect(name, internal=True)
                result = self.collect(name)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stderr, '')
                self.assertEqual(json.loads(result.stdout), json.loads(original.stdout))
                path = self.gear if name == 'Gear' else self.projects
                before = path.read_bytes()
                path.unlink()
                result = self.collect(name)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(result.stdout), {'complete': False, 'assets': [], 'edges': []})
                path.write_bytes(before)

    def test_private_and_retired_collector_sources_refuse(self):
        for name, path, marker in (('Gear', self.gear, 'SyntheticAtlasDevice'),
                                   ('Projects', self.projects, 'SyntheticAtlasProject')):
            with self.subTest(name=name):
                original = path.read_text()
                path.write_text(original.replace(marker, '<private>' + marker + '</private>'))
                self.assertNotEqual(self.collect(name).returncode, 0)
                path.write_text(original)
                saved = self.fixture.fixture.memory.remember(OWNER, category='project', content=marker,
                    title='Synthetic Atlas retirement', project='lab', request_id='atlas-save-' + name)
                self.fixture.fixture.memory.forget(OWNER, saved['reference'], 'atlas-retire-' + name)
                self.assertNotEqual(self.collect(name).returncode, 0)

    def test_collector_links_invalid_encoding_and_connector_loss_refuse(self):
        for name, path in (('Gear', self.gear), ('Projects', self.projects)):
            original = path.read_bytes()
            for mode in ('symlink', 'hardlink', 'utf8', 'oversize'):
                with self.subTest(name=name, mode=mode):
                    path.unlink()
                    if mode in ('symlink', 'hardlink'):
                        outside = self.fixture.fixture.home / ('outside-' + name)
                        outside.write_bytes(original)
                        if mode == 'symlink': path.symlink_to(outside)
                        else: os.link(outside, path)
                    elif mode == 'utf8': path.write_bytes(b'\xff')
                    else: path.write_bytes(b'x' * (256 * 1024 + 1))
                    result = self.collect(name)
                    self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                    path.unlink()
                    path.write_bytes(original)
        (self.root / 'LIFEOS/USER/CONFIG/memory-access.json').unlink()
        for name in ('Gear', 'Projects'):
            self.assertNotEqual(self.collect(name).returncode, 0)

    def test_actual_collector_render_rechecks_bytes_inode_and_authority(self):
        configuration = self.fixture.configuration.path.read_bytes()
        original = self.gear.read_bytes()
        for mode in ('source', 'metadata', 'created', 'authority'):
            with self.subTest(mode=mode):
                self.fixture.configuration.path.write_bytes(configuration)
                self.gear.write_bytes(original)
                if mode == 'created': self.gear.unlink()
                result = subprocess.run([sys.executable, str(Path(__file__).with_name('memory_atlas_process.py')),
                    str(self.fixture.configuration.path), mode, 'gear'], capture_output=True, text=True, timeout=30,
                    env=dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1])))
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stderr, '')
                self.assertEqual(json.loads(result.stdout), {'rendered': True, 'withheld': True})


if __name__ == '__main__': unittest.main()
