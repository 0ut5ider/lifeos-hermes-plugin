# ABOUTME: Verifies coherent selected-profile and native-data snapshots with actual SQLite and filesystem state.
# ABOUTME: Checks configuration preservation, skill and history coverage, redirects, and private archive integrity.
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import time
import unittest

from lifeos_hook_bridge.memory_access import MemoryUnavailable
from lifeos_hook_bridge.memory_backup import inspect as inspect_native
from lifeos_hook_bridge.memory_service import MemoryConfiguration
from lifeos_hook_bridge.profile_backup import _entries, create, inspect
import test_memory_runtime as runtime_fixture
import test_memory_native as native_fixture


class ProfileBackupTests(unittest.TestCase):
    def setUp(self):
        self.fixture = runtime_fixture.MemoryRuntimeTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.profile = self.fixture.home
        self.configuration = MemoryConfiguration(self.fixture.path)
        self.destination = self.fixture.fixture.home / 'profile-backups/one'
        self.saved = self.fixture.fixture.remember('Synthetic coherent profile backup fact', 'profile-backup-original')
        self.sources = {'config.yaml': b'memory:\n  memory_enabled: true\n  user_profile_enabled: true\n',
                        'SOUL.md': b'# Synthetic preserved profile identity\n',
                        'memories/MEMORY.md': b'Synthetic preserved Hermes memory.\n',
                        'memories/USER.md': b'Synthetic preserved Hermes preference.\n',
                        'skills/retained/SKILL.md': b'# Synthetic retained skill\n',
                        'sessions/history.json': b'[{"role":"user","content":"Synthetic retained history"}]\n',
                        'custom-owner-file.bin': bytes(range(256))}
        for name, data in self.sources.items():
            path = self.profile / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        self.database = self.profile / 'state.db'
        with closing(sqlite3.connect(self.database)) as connection:
            connection.execute('CREATE TABLE sessions (id TEXT PRIMARY KEY, body TEXT)')
            connection.execute("INSERT INTO sessions VALUES ('session','Synthetic committed profile history')")
            connection.commit()
        self.database.chmod(0o600)

    def snapshot(self):
        result = create(self.configuration, self.destination)
        return result, inspect(self.configuration, self.destination, result['signature'])

    def test_snapshot_keeps_profile_files_history_skills_and_native_references_together(self):
        before = self.fixture.path.read_bytes()
        result, manifest = self.snapshot()
        self.assertEqual(result['status'], 'committed', result)
        self.assertEqual(self.fixture.path.read_bytes(), before)
        self.assertEqual(manifest['profile'], str(self.profile))
        self.assertEqual(manifest['native_root'], str(self.fixture.fixture.root))
        files = {item['path']: item for item in manifest['files']}
        for name, data in self.sources.items():
            self.assertEqual((self.destination / 'profile/files' / str(files[name]['copy'])).read_bytes(), data)
            self.assertEqual((self.profile / name).read_bytes(), data)
        with closing(sqlite3.connect(':memory:')) as database:
            database.deserialize((self.destination / 'profile/files' / str(files['state.db']['copy'])).read_bytes())
            self.assertEqual(database.execute('SELECT body FROM sessions').fetchall(), [('Synthetic committed profile history',)])
        native = inspect_native(self.fixture.fixture.memory, native_fixture.OWNER, self.destination / 'native', manifest['native_signature'])
        self.assertIn('MEMORY/STATE/memory-access.sqlite', [item['path'] for item in native['files']])
        self.assertNotIn('Synthetic coherent profile backup fact', json.dumps(result))

    def test_snapshot_captures_committed_wal_history_without_changing_live_journal_mode(self):
        connection = sqlite3.connect(self.database)
        self.addCleanup(connection.close)
        if hasattr(sqlite3, 'SQLITE_DBCONFIG_NO_CKPT_ON_CLOSE'):
            connection.setconfig(sqlite3.SQLITE_DBCONFIG_NO_CKPT_ON_CLOSE, True)
        self.assertEqual(connection.execute('PRAGMA journal_mode=WAL').fetchone()[0], 'wal')
        connection.execute("INSERT INTO sessions VALUES ('latest','Synthetic latest WAL history')")
        connection.commit()
        _, manifest = self.snapshot()
        files = {item['path']: item for item in manifest['files']}
        image = (self.destination / 'profile/files' / str(files['state.db']['copy'])).read_bytes()
        with closing(sqlite3.connect(':memory:')) as recovered:
            recovered.deserialize(image)
            self.assertEqual(recovered.execute('SELECT COUNT(*) FROM sessions').fetchone()[0], 2)
        self.assertFalse(any(item['path'].endswith(('-wal', '-shm', '-journal')) for item in manifest['files']))
        self.assertEqual(connection.execute('PRAGMA journal_mode').fetchone()[0], 'wal')

    def test_snapshot_keeps_internal_links_and_native_data_links_without_following_them(self):
        (self.profile / 'memory-alias').symlink_to('memories/MEMORY.md')
        (self.profile / 'native-data').symlink_to(self.fixture.fixture.home / '.config/LIFEOS/USER')
        _, manifest = self.snapshot()
        links = {item['path']: item['target'] for item in manifest['links']}
        self.assertEqual(links['memory-alias'], 'memories/MEMORY.md')
        self.assertEqual(links['native-data'], str(self.fixture.fixture.home / '.config/LIFEOS/USER'))

    def test_snapshot_refuses_unknown_external_links_without_publishing(self):
        (self.profile / 'external-source').symlink_to(self.fixture.fixture.home / 'unreviewed-external')
        with self.assertRaises(MemoryUnavailable):
            create(self.configuration, self.destination)
        self.assertFalse(self.destination.exists())

    def test_snapshot_requires_owner_account_and_preserves_existing_archives(self):
        with self.assertRaises(PermissionError):
            create(self.configuration, self.destination, account='chat-a:other')
        self.destination.mkdir(parents=True)
        marker = self.destination / 'prior-owner-data'
        marker.write_text('Preserve this archive.\n')
        with self.assertRaises(MemoryUnavailable):
            create(self.configuration, self.destination)
        self.assertEqual(marker.read_text(), 'Preserve this archive.\n')

    def test_snapshot_is_private_and_inspection_refuses_changed_copies(self):
        result, manifest = self.snapshot()
        for path in [self.destination, *self.destination.rglob('*')]:
            self.assertEqual(path.stat().st_mode & 0o777, 0o700 if path.is_dir() else 0o600, path)
        entry = next(item for item in manifest['files'] if item['path'] == 'SOUL.md')
        copy = self.destination / 'profile/files' / str(entry['copy'])
        copy.write_bytes(b'Synthetic changed archive copy')
        with self.assertRaises(MemoryUnavailable):
            inspect(self.configuration, self.destination, result['signature'])

    def test_inspection_rejects_incomplete_and_ambiguous_source_metadata(self):
        _, manifest = self.snapshot()
        invalid = []
        for field, value in [('files', None), ('directories', None), ('links', None)]:
            invalid.append({**manifest, field: value})
        invalid.append({**manifest, 'directories': [item for item in manifest['directories'] if item['path'] != '.']})
        invalid.append({**manifest, 'directories': [*manifest['directories'], manifest['directories'][0]]})
        invalid.append({**manifest, 'files': [{**manifest['files'][0], 'mode': True}, *manifest['files'][1:]]})
        invalid.append({**manifest, 'links': [{'path': 'SOUL.md', 'target': 'memories/MEMORY.md', 'mtime_ns': 0}]})
        invalid.append({**manifest, 'links': [{'path': 'outside', 'target': '/unreviewed', 'mtime_ns': 0}]})
        invalid.append({**manifest, 'files': [{**manifest['files'][0], 'path': 'missing-parent/source'}, *manifest['files'][1:]]})
        invalid.append({**manifest, 'files': [item for item in manifest['files'] if item['path'] != self.fixture.path.name]})
        invalid.append({**manifest, 'native_signature': None})
        invalid.append({**manifest, 'version': True})
        for candidate in invalid:
            with self.subTest(candidate=candidate):
                (self.destination / 'manifest.json').write_text(json.dumps(candidate))
                with self.assertRaises(MemoryUnavailable):
                    inspect(self.configuration, self.destination)

    def start_process(self, mode, markers):
        settings = {'mode': mode, 'markers': str(markers), 'configuration': str(self.fixture.path),
                    'destination': str(self.destination), 'database': str(self.database),
                    'root': str(self.fixture.fixture.root)}
        process = subprocess.Popen([sys.executable, '-W', 'error::ResourceWarning',
            str(Path(__file__).with_name('profile_backup_process.py'))], stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=os.environ.copy())
        process.stdin.write(json.dumps(settings))
        process.stdin.close()
        process.stdin = None
        def cleanup():
            if process.poll() is None:
                process.kill()
            process.communicate(timeout=5)
        self.addCleanup(cleanup)
        return process

    def wait_marker(self, path, processes):
        deadline = time.monotonic() + 15
        while not path.exists():
            for process in processes:
                if process.poll() is not None:
                    stdout, stderr = process.communicate(timeout=5)
                    self.fail(f'The control exits before its observed barrier: {process.returncode}: {stdout}{stderr}')
            if time.monotonic() > deadline:
                self.fail(f'The isolated control has no barrier marker: {path.name}')
            time.sleep(0.01)

    def test_real_native_and_profile_writers_wait_for_one_coherent_snapshot(self):
        markers = self.fixture.fixture.home / 'writer-controls'
        markers.mkdir()
        backup = self.start_process('backup', markers)
        self.wait_marker(markers / 'backup-ready', [backup])
        native_probe = self.start_process('native-sqlite-probe', markers)
        stdout, stderr = native_probe.communicate(timeout=5)
        self.assertEqual(native_probe.returncode, 0, stdout + stderr)
        self.assertEqual(stdout + stderr, '')
        self.assertTrue((markers / 'native-sqlite-probe-blocked').exists())
        writers = [self.start_process(mode, markers) for mode in ('sqlite', 'native')]
        for mode in ('sqlite', 'native'):
            self.wait_marker(markers / (mode + '-blocked'), [backup, *writers])
            self.assertFalse((markers / (mode + '-result.json')).exists())
        (markers / 'release').touch()
        for index in (1, 2):
            self.wait_marker(markers / f'collection-{index}-ready', [backup, *writers])
            probe = self.start_process(f'sqlite-probe-{index}', markers)
            stdout, stderr = probe.communicate(timeout=5)
            self.assertEqual(probe.returncode, 0, stdout + stderr)
            self.assertEqual(stdout + stderr, '')
            self.assertTrue((markers / f'sqlite-probe-{index}-blocked').exists())
            self.assertFalse((markers / 'sqlite-result.json').exists())
            (markers / f'collection-{index}-release').touch()
        for process in [backup, *writers]:
            stdout, stderr = process.communicate(timeout=30)
            evidence = markers / 'collections.json'
            observations = markers / 'observations.json'
            self.assertEqual(process.returncode, 0, stdout + stderr + (evidence.read_text() if evidence.exists() else '')
                             + (observations.read_text() if observations.exists() else ''))
            self.assertEqual(stdout + stderr, '')
        receipt = json.loads((markers / 'backup-result.json').read_text())
        manifest = inspect(self.configuration, self.destination, receipt['signature'])
        entry = next(item for item in manifest['files'] if item['path'] == 'state.db')
        with closing(sqlite3.connect(':memory:')) as archived:
            archived.deserialize((self.destination / 'profile/files' / str(entry['copy'])).read_bytes())
            self.assertEqual(archived.execute('SELECT COUNT(*) FROM sessions').fetchone()[0], 1)
        with closing(sqlite3.connect(self.database)) as live:
            self.assertEqual(live.execute('SELECT COUNT(*) FROM sessions').fetchone()[0], 2)
        native = inspect_native(self.fixture.fixture.memory, native_fixture.OWNER,
                                self.destination / 'native', manifest['native_signature'])
        entry = next(item for item in native['files'] if item['path'] == 'MEMORY/STATE/memory-access.sqlite')
        with closing(sqlite3.connect(':memory:')) as archived:
            archived.deserialize((self.destination / 'native/files' / str(entry['copy'])).read_bytes())
            self.assertEqual(archived.execute('SELECT COUNT(*) FROM records').fetchone()[0], 1)
        later = json.loads((markers / 'native-result.json').read_text())
        self.assertEqual(self.fixture.fixture.memory.get(native_fixture.OWNER, later['reference'])['content'],
                         'Synthetic later concurrent native fact')

    def test_process_exit_retains_a_private_verified_stage_and_releases_writers(self):
        markers = self.fixture.fixture.home / 'interruption-controls'
        markers.mkdir()
        before = self.fixture.path.read_bytes()
        process = self.start_process('interrupt', markers)
        stdout, stderr = process.communicate(timeout=30)
        self.assertEqual(process.returncode, 73, stdout + stderr)
        self.assertEqual(stdout + stderr, '')
        self.assertFalse(self.destination.exists())

        stages = list(self.destination.parent.glob('.profile-backup-*'))
        self.assertEqual(len(stages), 1)
        signature = (markers / 'interrupted-signature').read_text()
        inspect(self.configuration, stages[0], signature)
        self.assertEqual(self.fixture.path.read_bytes(), before)
        self.assertEqual(self.fixture.fixture.memory.get(native_fixture.OWNER, self.saved['reference'])['status'], 'ok')
        self.snapshot()
        self.assertTrue(stages[0].is_dir())

    def test_inventory_refuses_a_pipe_before_any_file_reader_can_block(self):
        pipe = self.profile / 'unsupported-owner-pipe'
        os.mkfifo(pipe, 0o600)
        with self.assertRaises(MemoryUnavailable):
            _entries(self.profile, self.fixture.fixture.home / '.config/LIFEOS/USER')

    def test_new_database_alias_is_refused_before_a_direct_reader_can_drop_locks(self):
        import lifeos_hook_bridge.profile_backup as backup
        linked, reads = False, []
        alias = self.profile / 'database-alias'
        def trace(frame, event, argument):
            nonlocal linked
            if event == 'call' and frame.f_code.co_name == '_read':
                reads.append(frame.f_locals.get('path'))
            if (not linked and event == 'call' and frame.f_code.co_filename == backup.__file__
                    and frame.f_code.co_name == '_collect_profile'):
                linked = True
                os.link(self.database, alias)
            return trace
        sys.settrace(trace)
        try:
            with self.assertRaises(MemoryUnavailable):
                create(self.configuration, self.destination)
        finally:
            sys.settrace(None)
        self.assertNotIn(alias, reads)

    def test_native_database_alias_is_refused_without_opening_its_locked_inode(self):
        from lifeos_hook_bridge.memory_backup import create as create_native
        alias = self.fixture.fixture.memory.database.resolve().with_name('database-alias')
        os.link(self.fixture.fixture.memory.database, alias)
        reads = []
        def trace(frame, event, argument):
            if event == 'call' and frame.f_code.co_name == '_read':
                reads.append(frame.f_locals.get('path'))
            return trace
        sys.settrace(trace)
        try:
            with self.assertRaises(MemoryUnavailable):
                create_native(self.fixture.fixture.memory, native_fixture.OWNER, self.destination)
        finally:
            sys.settrace(None)
        self.assertNotIn(alias, reads)

    def test_replaced_database_cannot_borrow_the_prior_connection_snapshot(self):
        import lifeos_hook_bridge.profile_backup as backup
        replaced = False
        def trace(frame, event, argument):
            nonlocal replaced
            if (not replaced and event == 'call' and frame.f_code.co_filename == backup.__file__
                    and frame.f_code.co_name == '_collect_profile'):
                replaced = True
                self.database.rename(self.database.with_name('retained-state.db'))
                with closing(sqlite3.connect(self.database)) as connection:
                    connection.execute('CREATE TABLE sessions (id TEXT PRIMARY KEY, body TEXT)')
                    connection.execute("INSERT INTO sessions VALUES ('replacement','Synthetic replacement history')")
                    connection.commit()
                self.database.chmod(0o600)
            return trace
        sys.settrace(trace)
        try:
            with self.assertRaises(MemoryUnavailable):
                create(self.configuration, self.destination)
        finally:
            sys.settrace(None)
        self.assertTrue(replaced)
        self.assertFalse(self.destination.exists())
