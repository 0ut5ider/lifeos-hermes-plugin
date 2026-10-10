# ABOUTME: Exercises fresh Atlas initialization through the current owner service.
# ABOUTME: Checks native reconciliation, private files, and refusal before graph publication.
import json
from contextlib import closing
from dataclasses import asdict
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import unittest

import test_memory_atlas_insight as atlas_fixture
import test_memory_owner_jobs as owner_jobs_fixture
from lifeos_hook_bridge import memory_atlas_insight
from lifeos_hook_bridge import memory_atlas_sync
from lifeos_hook_bridge.memory_access import MemoryUnavailable
import test_memory_publication_destinations as publication_fixture


class MemoryAtlasSyncTests(unittest.TestCase):
    setUp = atlas_fixture.MemoryAtlasInsightTests.setUp
    call = atlas_fixture.MemoryAtlasInsightTests.call

    def sources(self):
        (self.root/'LIFEOS/USER/GEAR.md').write_text('## Computing\n| **Laptop** | Synthetic Atlas Machine | daily |\n')
        (self.root/'LIFEOS/USER/PROJECTS.md').write_text(
            '| Name | Path | URL | Deploy |\n| --- | --- | --- | --- |\n'
            '| Synthetic Atlas Project | /synthetic/project | atlas.example.invalid | local |\n')

    def sync(self, collectors=None, scope='full'):
        return self.call('atlas_sync', collectors=collectors or ['gear', 'projects'], scope=scope)

    def graph(self):
        return self.root.parent/'.local/state/lifeos/atlas/atlas.db'

    def test_fresh_sync_uses_native_graph_and_snapshot(self):
        self.sources()
        result = self.sync()
        self.assertTrue(result['ok'], result)
        self.assertEqual([run['collector'] for run in result['runs']], ['gear', 'projects'])
        with closing(sqlite3.connect(self.graph())) as connection:
            kinds = [row[0] for row in connection.execute('SELECT kind FROM asset ORDER BY kind')]
            self.assertEqual(kinds, ['device', 'domain', 'project'])
            self.assertEqual(connection.execute('SELECT COUNT(*) FROM edge').fetchone()[0], 1)
        snapshot = self.graph().with_name('snapshot.json')
        self.assertEqual(len(json.loads(snapshot.read_text())['assets']), 3)
        for path in (self.graph(), snapshot):
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.assertFalse(self.cache.exists())

    def test_repeat_sync_preserves_native_identity_and_incomplete_observations(self):
        self.sources()
        self.assertTrue(self.sync()['ok'])
        with closing(sqlite3.connect(self.graph())) as connection:
            original = connection.execute('SELECT id, canonical_key FROM asset ORDER BY id').fetchall()
        self.assertTrue(self.sync()['ok'])
        (self.root/'LIFEOS/USER/GEAR.md').unlink()
        self.assertTrue(self.sync(['gear'])['ok'])
        with closing(sqlite3.connect(self.graph())) as connection:
            self.assertEqual(connection.execute('SELECT id, canonical_key FROM asset ORDER BY id').fetchall(), original)
            self.assertEqual(connection.execute("SELECT fresh FROM source_observation WHERE collector='gear'").fetchone()[0], 1)
            self.assertEqual(connection.execute('SELECT COUNT(*) FROM sync_run').fetchone()[0], 5)

    def test_fresh_empty_graph_and_targeted_runs_keep_native_sweep_rules(self):
        self.assertTrue(self.sync()['ok'])
        self.sources()
        self.assertTrue(self.sync()['ok'])
        (self.root/'LIFEOS/USER/GEAR.md').write_text('# Gear\n')
        self.assertTrue(self.sync(['gear'], 'targeted:manual')['ok'])
        with closing(sqlite3.connect(self.graph())) as connection:
            self.assertEqual(connection.execute("SELECT fresh FROM source_observation WHERE collector='gear'").fetchone()[0], 1)
        self.assertTrue(self.sync(['gear'])['ok'])
        with closing(sqlite3.connect(self.graph())) as connection:
            self.assertEqual(connection.execute("SELECT fresh FROM source_observation WHERE collector='gear'").fetchone()[0], 0)

    def test_actual_managed_cli_routes_sync_and_refuses_unbound_raw_writes(self):
        self.sources()
        environment = dict(os.environ, HOME=str(self.root.parent), BUN_CONFIG_NO_AUTO_INSTALL='1')
        environment.pop('LIFEOS_MEMORY_INTERNAL', None)
        environment['LIFEOS_MEMORY_CONTEXT'] = json.dumps(asdict(self.owner.context))
        command = ['bun', '--no-install', str(self.root/'LIFEOS/ATLAS/Atlas.ts'), 'sync']
        result = subprocess.run(command, env=environment, capture_output=True, text=True, timeout=40)
        self.assertEqual((result.returncode, result.stderr), (0, ''), result.stdout + result.stderr)
        self.assertTrue(json.loads(result.stdout)['ok'])
        before = self.graph().read_bytes()
        hints = self.graph().with_name('events.jsonl')
        hints.write_text('{"source":"gear"}\n')
        result = subprocess.run([*command[:-1], 'tick'], env=environment, capture_output=True, text=True, timeout=10)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Managed Atlas tick requires an admitted event scheduler', result.stderr)
        self.assertEqual(hints.read_text(), '{"source":"gear"}\n')
        self.assertFalse(hints.with_name('events.jsonl.processing').exists())
        environment.pop('LIFEOS_MEMORY_CONTEXT')
        result = subprocess.run(command, env=environment, capture_output=True, text=True, timeout=40)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('requires current owner admission', result.stderr)
        module = str(self.root/'LIFEOS/ATLAS/Store.ts')
        result = subprocess.run(['bun', '--no-install', '-e',
            'import {Store} from '+json.dumps(module)+';new Store();'],
            env=environment, capture_output=True, text=True, timeout=10)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Managed Atlas writes require governed synchronization', result.stderr)
        self.assertEqual(self.graph().read_bytes(), before)

    def test_later_edits_preserve_the_whole_publication_group_and_recovery(self):
        for selected in ('atlas.db', 'snapshot.json'):
            with self.subTest(destination=selected):
                fixture = MemoryAtlasSyncTests()
                fixture.setUp()
                self.addCleanup(fixture.doCleanups)
                fixture.sources()
                self.assertTrue(fixture.sync()['ok'])
                memory = fixture.owner.fixture.memory
                paths = [fixture.graph(), fixture.graph().with_name('snapshot.json')]
                originals = {path: path.read_bytes() for path in paths}
                published, changed = {}, []
                destination = fixture.graph().with_name(selected)
                original_publish = memory_atlas_sync.publish
                def observed_publish(path, content):
                    original_publish(path, content)
                    published[path] = content
                    if path == destination:
                        if selected == 'atlas.db':
                            with closing(sqlite3.connect(path)) as connection:
                                connection.execute("UPDATE asset SET display_name='Synthetic later Atlas owner edit' WHERE kind='device'")
                                connection.commit()
                        else:
                            value = json.loads(path.read_text())
                            value['generated_at'] = '2026-10-10T12:01:00Z'
                            path.write_text(json.dumps(value))
                        changed.append(path.read_bytes())
                memory_atlas_sync.publish = observed_publish
                try:
                    result = fixture.sync()
                finally:
                    memory_atlas_sync.publish = original_publish
                self.assertFalse(result['ok'], result)
                self.assertEqual(len(changed), 1)
                self.assertTrue(memory.transaction.journal.exists())
                before = {path: path.read_bytes() for path in paths}
                with self.assertRaisesRegex(MemoryUnavailable, 'later artifact edit'):
                    with memory._transaction(): pass
                self.assertEqual({path: path.read_bytes() for path in paths}, before)
                destination.write_bytes(published[destination])
                with memory._transaction(): pass
                self.assertFalse(memory.transaction.journal.exists())
                self.assertEqual({path: path.read_bytes() for path in paths}, originals)

    def test_process_death_and_post_publication_changes_keep_recovery(self):
        for mode in ('interrupt', 'source', 'authority'):
            with self.subTest(mode=mode):
                fixture = MemoryAtlasSyncTests()
                fixture.setUp()
                self.addCleanup(fixture.doCleanups)
                fixture.sources()
                self.assertTrue(fixture.sync()['ok'])
                memory = fixture.owner.fixture.memory
                paths = [fixture.graph(), fixture.graph().with_name('snapshot.json')]
                originals = {path: path.read_bytes() for path in paths}
                configuration = fixture.configuration.path.read_bytes()
                result = subprocess.run([sys.executable, str(Path(__file__).with_name('memory_atlas_sync_process.py')),
                    str(fixture.configuration.path), json.dumps(asdict(fixture.owner.context)), mode],
                    capture_output=True, text=True, timeout=30)
                self.assertEqual(result.stderr, '')
                if mode == 'interrupt':
                    self.assertEqual(result.returncode, 73)
                else:
                    self.assertEqual(result.returncode, 0)
                    self.assertFalse(json.loads(result.stdout)['ok'])
                self.assertTrue(memory.transaction.journal.exists())
                with closing(sqlite3.connect(memory.database)) as connection:
                    receipts = [json.loads(row[0])['status'] for row in connection.execute('SELECT receipt FROM operations')]
                self.assertEqual(receipts.count('unknown'), 1)
                fixture.configuration.path.write_bytes(configuration)
                with memory._transaction(): pass
                self.assertFalse(memory.transaction.journal.exists())
                self.assertEqual({path: path.read_bytes() for path in paths}, originals)

    def test_database_companions_and_aliases_refuse_without_replacing_files(self):
        self.sources()
        self.assertTrue(self.sync()['ok'])
        before = self.graph().read_bytes()
        for suffix in ('-wal', '-shm', '-journal'):
            companion = self.graph().with_name('atlas.db'+suffix)
            companion.write_bytes(b'Synthetic companion')
            self.assertFalse(self.sync()['ok'])
            self.assertEqual(self.graph().read_bytes(), before)
            self.assertEqual(companion.read_bytes(), b'Synthetic companion')
            companion.unlink()
        original = self.graph().with_name('original.db')
        self.graph().rename(original)
        self.graph().symlink_to(original)
        self.assertFalse(self.sync()['ok'])
        self.assertEqual(original.read_bytes(), before)

    def test_inherited_atlas_directory_cannot_redirect_planner_effects(self):
        outside = self.root.parent/'unselected-atlas-directory'
        original = os.environ.get('ATLAS_DIR')
        os.environ['ATLAS_DIR'] = str(outside)
        try:
            self.assertTrue(self.sync()['ok'])
        finally:
            if original is None:
                os.environ.pop('ATLAS_DIR')
            else:
                os.environ['ATLAS_DIR'] = original
        self.assertFalse(outside.exists())

    def test_disabled_read_only_private_and_undeclared_collectors_do_not_create_graph(self):
        self.sources()
        for collectors, scope in ((['systemd'], 'full'), (['gear', 'gear'], 'full'), (['gear'], ''), (['gear'], 'x'*129)):
            with self.subTest(collectors=collectors, scope=scope):
                self.assertFalse(self.sync(collectors, scope)['ok'])
                self.assertFalse(self.graph().exists())
        (self.root/'LIFEOS/USER/GEAR.md').write_text('<private>Synthetic Atlas Private</private>')
        self.assertFalse(self.sync()['ok'])
        self.assertFalse(self.graph().exists())
        self.sources()
        self.configuration.update(lambda value: value['destinations']['chat-a:200'].update(write=[]))
        self.assertFalse(self.sync()['ok'])
        self.assertFalse(self.graph().exists())
        self.configuration.update(lambda value: value['accounts'].clear())
        self.assertFalse(self.sync()['ok'])
        self.assertFalse(self.graph().exists())


class MemoryAtlasNarrativeFinalizationTests(unittest.TestCase):
    fixture = publication_fixture.MemoryPublicationDestinationTests.fixture
    receipts = publication_fixture.MemoryPublicationDestinationTests.receipts
    assert_destination_refusal = publication_fixture.MemoryPublicationDestinationTests.assert_destination_refusal
    # These tests use the actual native graph and observe real cache publication.
    def test_atlas_destination_changes_retain_recovery(self):
        for phase in ('publication', 'snapshot'):
            with self.subTest(phase=phase):
                fixture = self.fixture(atlas_fixture.MemoryAtlasInsightTests)
                fixture.seed()
                prepared = fixture.prepare()
                def edit(value):
                    value['narrative'] = 'Synthetic later owner Atlas narrative.'
                self.assert_destination_refusal(fixture.owner.fixture.memory, memory_atlas_insight,
                    memory_atlas_insight, [fixture.cache], fixture.cache, phase, edit,
                    lambda: fixture.call('atlas_insight_publish', signature=prepared['signature'], value=fixture.value(prepared)))


class MemoryAtlasOwnerSyncTests(unittest.TestCase):
    run_job = owner_jobs_fixture.MemoryOwnerJobsTests.run_job

    def setUp(self):
        owner_jobs_fixture.MemoryOwnerJobsTests.setUp(self)
        self.root = self.fixture.root
        (self.root/'LIFEOS/ATLAS').symlink_to(Path(os.environ['LIFEOS_MEMORY_SOURCE'])/'LIFEOS/ATLAS')

    def test_actual_owner_job_initializes_graph_without_inference(self):
        result = self.run_job('atlas-sync')
        self.assertEqual(result['status'], 'completed', result)
        self.assertTrue(json.loads(result['output'])['ok'])
        self.assertTrue((self.root.parent/'.local/state/lifeos/atlas/atlas.db').exists())
        self.assertFalse((self.root/'LIFEOS/MEMORY/STATE/atlas-insights.json').exists())
