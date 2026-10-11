# ABOUTME: Exercises governed Atlas history archives with the actual native graph store.
# ABOUTME: Verifies observation references, cumulative counts, refusal, and grouped recovery.
from contextlib import closing
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import unittest

import test_memory_atlas_sync as sync_fixture
import test_memory_atlas_capacity as capacity_fixture
import test_memory_atlas_guest_recovery as recovery_fixture
import test_memory_owner_job_command as command_fixture
import test_memory_model_calls as model_fixture
from lifeos_hook_bridge import memory_atlas_sync
from lifeos_hook_bridge.memory_access import MemoryUnavailable
from test_memory_native import OWNER


class MemoryAtlasRetentionTests(unittest.TestCase):
    setUp = sync_fixture.MemoryAtlasSyncTests.setUp
    call = sync_fixture.MemoryAtlasSyncTests.call
    sync = sync_fixture.MemoryAtlasSyncTests.sync
    graph = sync_fixture.MemoryAtlasSyncTests.graph
    sources = sync_fixture.MemoryAtlasSyncTests.sources
    seed_runs = capacity_fixture.MemoryAtlasCapacityTests.seed_runs
    inventory = capacity_fixture.MemoryAtlasCapacityTests.inventory

    def test_projection_pressure_archives_before_the_fixed_run_trigger(self):
        self.inventory(100, 50)
        self.assertTrue(self.sync()['ok'])
        self.seed_runs(56)
        database = self.graph().read_bytes()
        result = self.sync()
        archive = self.archive(result)
        self.assertEqual((archive/'atlas.db').read_bytes(), database)
        self.assertLess(result['capacity']['graph_fields']['used'], 10000)

    def prepare_history(self):
        self.sources()
        self.assertTrue(self.sync()['ok'])
        self.seed_runs(64)
        return self.graph().read_bytes(), self.graph().with_name('snapshot.json').read_bytes()

    def archive(self, result):
        self.assertTrue(result['ok'], result)
        identifier = result['history']['archive_id']
        self.assertRegex(identifier, '^[0-9a-f]{64}$')
        return self.graph().parent/'history'/identifier

    def test_archive_preserves_exact_inputs_and_every_observation_reference(self):
        database, snapshot = self.prepare_history()
        # A missing collector leaves its earlier observation and run reference intact.
        (self.root/'LIFEOS/USER/GEAR.md').unlink()
        result = self.sync(['gear'])
        archive = self.archive(result)
        self.assertEqual((archive/'atlas.db').read_bytes(), database)
        self.assertEqual((archive/'snapshot.json').read_bytes(), snapshot)
        manifest = json.loads((archive/'manifest.json').read_text())
        self.assertEqual(manifest['before']['database'], hashlib.sha256(database).hexdigest())
        self.assertGreater(manifest['removed']['sync_run'], 0)
        with closing(sqlite3.connect(self.graph())) as connection:
            self.assertLessEqual(connection.execute('SELECT COUNT(*) FROM sync_run').fetchone()[0], 35)
            self.assertEqual(connection.execute('SELECT COUNT(*) FROM source_observation o '
                'LEFT JOIN sync_run r ON r.id=o.last_run_id WHERE r.id IS NULL').fetchone()[0], 0)
            self.assertEqual(connection.execute('SELECT COUNT(*) FROM edge_observation o '
                'LEFT JOIN sync_run r ON r.id=o.last_run_id WHERE r.id IS NULL').fetchone()[0], 0)
            self.assertEqual(connection.execute("SELECT fresh FROM source_observation WHERE collector='gear'").fetchone()[0], 1)
        for path in archive.iterdir():
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.assertFalse(self.owner.fixture.memory.transaction.journal.exists())

    def test_repeated_retention_preserves_lifetime_counts_and_archive_reads(self):
        self.prepare_history()
        for iteration in range(3):
            result = self.sync()
            archive = self.archive(result)
            snapshot = json.loads(self.graph().with_name('snapshot.json').read_text())
            counts = {row['collector']: row['runs'] for row in snapshot['status']['collectors']}
            self.assertEqual(counts['gear'], 66 + iteration*65)
            self.assertEqual(counts['projects'], 2 + iteration)
            history = self.call('atlas_history', archive_id=archive.name, table='sync_run', offset=0)
            self.assertTrue(history['ok'], history)
            self.assertGreater(len(history['rows']), 0)
            self.assertLessEqual(len(history['rows']), 100)
            if iteration != 2:
                self.seed_runs(64)
        self.assertEqual(len(list((self.graph().parent/'history').iterdir())), 3)

    def test_retention_preserves_native_maximum_collector_timestamp(self):
        self.prepare_history()
        with closing(sqlite3.connect(self.graph())) as connection:
            connection.execute("UPDATE sync_run SET finished_at='2099-01-01T00:00:00Z' WHERE id=3")
            connection.commit()
        result = self.sync()
        self.archive(result)
        snapshot = json.loads(self.graph().with_name('snapshot.json').read_text())
        gear = next(row for row in snapshot['status']['collectors'] if row['collector']=='gear')
        self.assertEqual(gear['last_run'],'2099-01-01T00:00:00Z')

    def test_lifecycle_retention_keeps_recent_snapshot_and_exact_old_events(self):
        self.sources()
        self.assertTrue(self.sync()['ok'])
        with closing(sqlite3.connect(self.graph())) as connection:
            connection.executemany('INSERT INTO lifecycle_event (asset_id,event,at,detail) VALUES (?,?,?,?)',
                [(1, 'synthetic', '2026-10-11T00:00:00Z', str(index)) for index in range(140)])
            connection.commit()
        database = self.graph().read_bytes()
        archive = self.archive(self.sync())
        self.assertEqual((archive/'atlas.db').read_bytes(), database)
        with closing(sqlite3.connect(self.graph())) as connection:
            self.assertEqual(connection.execute('SELECT COUNT(*) FROM lifecycle_event').fetchone()[0], 64)
        snapshot = json.loads(self.graph().with_name('snapshot.json').read_text())
        self.assertEqual(len(snapshot['lifecycle']), 50)
        self.assertEqual(snapshot['lifecycle'][0]['detail'], '139')

    def test_archive_reads_require_current_owner(self):
        self.prepare_history()
        archive = self.archive(self.sync())
        arguments = {'archive_id': archive.name, 'table': 'sync_run', 'offset': 0}
        self.configuration.update(lambda value: value['accounts'].clear())
        self.assertFalse(self.call('atlas_history', **arguments)['ok'])

    def test_archive_read_refuses_changed_bytes_and_arbitrary_paths(self):
        self.prepare_history()
        archive = self.archive(self.sync())
        arguments = {'archive_id': archive.name, 'table': 'sync_run', 'offset': 0}
        for change in ({'archive_id': '../atlas.db'}, {'table': 'asset; DELETE FROM asset'}, {'offset': True}, {'offset': 2049}):
            self.assertFalse(self.call('atlas_history', **(arguments | change))['ok'])
        (archive/'snapshot.json').write_bytes(b'{"synthetic":"later edit"}')
        self.assertFalse(self.call('atlas_history', **arguments)['ok'])

    def test_archive_read_refuses_changed_provenance_manifest(self):
        self.prepare_history()
        archive = self.archive(self.sync())
        manifest = json.loads((archive/'manifest.json').read_text())
        manifest['sources'] = {'synthetic': 'later owner edit'}
        (archive/'manifest.json').write_text(json.dumps(manifest))
        result = self.call('atlas_history', archive_id=archive.name, table='sync_run', offset=0)
        self.assertFalse(result['ok'], result)

    def test_archive_history_pagination_keeps_complete_ordered_rows(self):
        self.prepare_history()
        self.seed_runs(80)
        archive = self.archive(self.sync())
        first = self.call('atlas_history', archive_id=archive.name, table='sync_run', offset=0)
        second = self.call('atlas_history', archive_id=archive.name, table='sync_run', offset=first['next_offset'])
        self.assertTrue(first['ok'], first)
        self.assertTrue(second['ok'], second)
        self.assertEqual((len(first['rows']), len(second['rows'])), (100, 46))
        self.assertIsNone(second['next_offset'])
        self.assertEqual([row['id'] for row in first['rows']+second['rows']], list(range(1,147)))

    def test_retired_archive_text_is_withheld_without_erasing_the_archive(self):
        self.sources()
        self.assertTrue(self.sync()['ok'])
        memory = self.owner.fixture.memory
        marker = 'SyntheticAtlasArchivedRetiredObservation'
        saved = memory.remember(OWNER, category='principal', content=marker, title='Synthetic archive policy',
            project='', request_id='atlas-history-save')
        with closing(sqlite3.connect(self.graph())) as connection:
            connection.executemany('INSERT INTO lifecycle_event (asset_id,event,at,detail) VALUES (?,?,?,?)',
                [(1,'synthetic','2026-10-11T00:00:00Z',marker if index==0 else str(index)) for index in range(140)])
            connection.commit()
        archive = self.archive(self.sync())
        original = {path:path.read_bytes() for path in archive.iterdir()}
        before = self.call('atlas_history', archive_id=archive.name, table='lifecycle_event', offset=0)
        self.assertTrue(before['ok'],before)
        self.assertIn(marker,json.dumps(before['rows']))
        memory.forget(OWNER,saved['reference'],'atlas-history-forget')
        after = self.call('atlas_history', archive_id=archive.name, table='lifecycle_event', offset=0)
        self.assertFalse(after['ok'],after)
        self.assertNotIn(marker,json.dumps(after))
        self.assertEqual({path:path.read_bytes() for path in archive.iterdir()},original)

    def test_authority_revocation_after_archive_stops_before_live_graph_publication(self):
        database, snapshot = self.prepare_history()
        original = memory_atlas_sync.publish
        published = []
        def observe(path, content):
            original(path, content)
            published.append(path.name)
            if path.name == 'atlas.db' and 'history' in path.parts:
                self.configuration.update(lambda value: value['accounts'].clear())
        memory_atlas_sync.publish = observe
        try:
            self.assertFalse(self.sync()['ok'])
        finally:
            memory_atlas_sync.publish = original
        self.assertEqual(published, ['atlas.db'])
        self.assertEqual(self.graph().read_bytes(), database)
        self.assertEqual(self.graph().with_name('snapshot.json').read_bytes(), snapshot)
        self.assertTrue(self.owner.fixture.memory.transaction.journal.exists())

    def test_archive_alias_refuses_without_live_publication(self):
        self.prepare_history()
        before = self.graph().read_bytes()
        outside = self.root.parent/'synthetic-outside'
        outside.mkdir()
        (self.graph().parent/'history').symlink_to(outside, target_is_directory=True)
        self.assertFalse(self.sync()['ok'])
        self.assertEqual(self.graph().read_bytes(), before)
        self.assertEqual(list(outside.iterdir()), [])

    def test_process_death_after_archive_publication_recovers_the_whole_group(self):
        database, snapshot = self.prepare_history()
        memory = self.owner.fixture.memory
        for boundary in ('archive-atlas.db', 'archive-snapshot.json', 'archive-manifest.json', 'atlas.db', 'snapshot.json'):
            with self.subTest(boundary=boundary):
                result = subprocess.run([sys.executable, str(Path(__file__).with_name('memory_atlas_retention_process.py')),
                    str(self.configuration.path), json.dumps(asdict(self.owner.context)), boundary],
                    capture_output=True, text=True, timeout=40)
                self.assertEqual((result.returncode, result.stdout, result.stderr), (73, '', ''))
                self.assertTrue(memory.transaction.journal.exists())
                with memory._transaction():
                    pass
                self.assertEqual(self.graph().read_bytes(), database)
                self.assertEqual(self.graph().with_name('snapshot.json').read_bytes(), snapshot)
                self.assertEqual(list((self.graph().parent/'history').rglob('*.db')), [])

    def test_later_archive_edit_blocks_group_recovery(self):
        self.prepare_history()
        memory = self.owner.fixture.memory
        original = memory_atlas_sync.publish
        modified = []
        def observe(path, content):
            original(path, content)
            if path.name == 'manifest.json':
                path.write_bytes(content + b' ')
                modified.append(path)
        memory_atlas_sync.publish = observe
        try:
            self.assertFalse(self.sync()['ok'])
        finally:
            memory_atlas_sync.publish = original
        self.assertEqual(len(modified), 1)
        before = self.graph().read_bytes()
        with self.assertRaisesRegex(MemoryUnavailable, 'later artifact edit'):
            with memory._transaction():
                pass
        self.assertEqual(self.graph().read_bytes(), before)
        self.assertTrue(memory.transaction.journal.exists())


class MemoryAtlasArchiveRecoveryTests(unittest.TestCase):
    def test_offline_group_restore_preserves_archives_and_owner_reads(self):
        fixture = recovery_fixture.MemoryAtlasGuestRecoveryTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        capacity_fixture.MemoryAtlasCapacityTests.seed_runs(fixture.fixture,64)
        result = fixture.fixture.sync()
        self.assertTrue(result['ok'],result)
        identifier = result['history']['archive_id']
        archive = fixture.fixture.graph().parent/'history'/identifier
        files = [*fixture.artifacts, *archive.iterdir()]
        original = {path:path.read_bytes() for path in files}
        fixture.offline_round_trip()
        self.assertEqual({path:path.read_bytes() for path in files},original)
        history = fixture.fixture.call('atlas_history', archive_id=identifier, table='sync_run', offset=0)
        self.assertTrue(history['ok'],history)
        self.assertEqual(history['total'],66)


class MemoryAtlasHistoryCommandTests(unittest.TestCase):
    def setUp(self):
        self.fixture = command_fixture.MemoryOwnerJobCommandTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.native.root
        for name in ('ATLAS', 'PULSE'):
            target = self.root/'LIFEOS'/name
            if not target.exists():
                target.symlink_to(Path(os.environ['LIFEOS_MEMORY_SOURCE'])/'LIFEOS'/name)
        self.environment = {key: os.environ[key] for key in ('PATH', 'LANG', 'TZ') if key in os.environ}
        self.environment.update(HOME=str(self.fixture.native.home), HERMES_HOME=str(self.fixture.fixture.home),
            PYTHONPATH=str(model_fixture.HOST), LIFEOS_HOOK_SETTINGS=str(self.root/'settings.json'),
            BUN_CONFIG_NO_AUTO_INSTALL='1')

    def test_actual_hermes_command_reads_archive_and_refuses_disabled_ownership(self):
        initial = self.fixture.call('atlas-sync')
        self.assertEqual(initial.returncode, 0, initial.stdout+initial.stderr)
        script = 'import {Store} from '+json.dumps(str(self.root/'LIFEOS/ATLAS/Store.ts'))+';const s=new Store();'
        script += 'for(let i=0;i<64;i++)s.applyRun("gear","full",{complete:false,assets:[],edges:[]});'
        script += 's.db.exec("PRAGMA wal_checkpoint(TRUNCATE)");s.db.exec("PRAGMA journal_mode=DELETE");s.close();'
        seeded = subprocess.run(['bun', '--no-install', '-e', script], capture_output=True, text=True,
            env=dict(os.environ, HOME=str(self.root.parent), LIFEOS_MEMORY_INTERNAL='1'), timeout=30)
        self.assertEqual((seeded.returncode, seeded.stdout, seeded.stderr), (0, '', ''))
        synced = self.fixture.call('atlas-sync')
        self.assertEqual(synced.returncode, 0, synced.stdout+synced.stderr)
        identifier = json.loads(json.loads(synced.stdout)['output'])['history']['archive_id']
        command = [sys.executable, '-m', 'hermes_cli.main', 'lifeos-atlas-history', identifier, '--table', 'sync_run']
        read = subprocess.run(command, env=self.environment, capture_output=True, text=True, timeout=40)
        self.assertEqual((read.returncode, read.stderr), (0, ''), read.stdout+read.stderr)
        self.assertTrue(json.loads(read.stdout)['ok'])
        self.fixture.configuration.update(lambda value: value.update(ownership_enabled=False))
        refused = subprocess.run(command, env=self.environment, capture_output=True, text=True, timeout=40)
        self.assertEqual(refused.stderr, '')
        self.assertNotEqual(refused.returncode, 0)
        self.assertFalse(json.loads(refused.stdout)['ok'])


if __name__ == '__main__':
    unittest.main()
