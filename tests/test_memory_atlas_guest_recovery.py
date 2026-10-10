# ABOUTME: Restores grouped synthetic guest state with Atlas artifacts and governance metadata.
# ABOUTME: Verifies exact crash recovery and later-edit preservation after an offline filesystem restore.
from contextlib import closing
from dataclasses import asdict
import json
from pathlib import Path
import shutil
import sqlite3
import stat
import subprocess
import sys
import tempfile
import unittest

import test_memory_atlas_sync as sync_fixture
import test_memory_atlas_insight as insight_fixture
from lifeos_hook_bridge.memory_access import MemoryUnavailable


class MemoryAtlasGuestRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.fixture = sync_fixture.MemoryAtlasSyncTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.sources()
        self.assertTrue(self.fixture.sync()['ok'])
        prepared = insight_fixture.MemoryAtlasInsightTests.prepare(self.fixture)
        self.assertTrue(self.fixture.call('atlas_insight_publish',signature=prepared['signature'],
            value=insight_fixture.MemoryAtlasInsightTests.value(self.fixture,prepared))['ok'])
        self.memory = self.fixture.owner.fixture.memory
        self.artifacts = (self.fixture.graph(),self.fixture.graph().with_name('snapshot.json'),self.fixture.cache)
        self.originals = {path:path.read_bytes() for path in self.artifacts}
        archive = tempfile.TemporaryDirectory(prefix='atlas-guest-restore-')
        self.addCleanup(archive.cleanup)
        self.archive = Path(archive.name)

    def roots(self):
        paths = {self.fixture.root.parent,self.fixture.configuration.path.parent}
        return sorted((path for path in paths if not any(path != other and path.is_relative_to(other)
            for other in paths)),key=str)

    def offline_round_trip(self):
        def volatile(directory, names):
            return [name for name in names if stat.S_ISSOCK((Path(directory)/name).lstat().st_mode)]
        paths = self.roots()
        # The disposable fixture has no scheduler or running write operation.
        for index,path in enumerate(paths):
            shutil.copytree(path,self.archive/('backup-'+str(index)),symlinks=True,ignore=volatile)
        for index,path in enumerate(paths):
            path.rename(self.archive/('retained-'+str(index)))
            shutil.copytree(self.archive/('backup-'+str(index)),path,symlinks=True)

    def interrupt(self):
        process = Path(__file__).with_name('memory_atlas_sync_process.py')
        result = subprocess.run([sys.executable,str(process),str(self.fixture.configuration.path),
            json.dumps(asdict(self.fixture.owner.context)),'interrupt'],
            capture_output=True,text=True,timeout=45)
        self.assertEqual((result.returncode,result.stdout,result.stderr),(73,'',''))
        self.assertTrue(self.memory.transaction.journal.exists())

    def test_offline_restore_preserves_graph_sources_cache_and_current_views(self):
        policy = self.fixture.configuration.path.read_bytes()
        self.offline_round_trip()
        self.assertEqual({path:path.read_bytes() for path in self.artifacts},self.originals)
        self.assertEqual(self.fixture.configuration.path.read_bytes(),policy)
        with closing(sqlite3.connect(self.fixture.graph())) as connection:
            self.assertEqual(connection.execute('PRAGMA integrity_check').fetchall(),[('ok',)])
        from lifeos_hook_bridge.memory_atlas import view
        scope = self.fixture.service.scope(self.fixture.owner.context)
        result = view(self.memory,scope,target='/api/atlas/insights')
        self.assertEqual(result['status'],200)
        self.assertFalse(result['body']['stale'])
        self.assertTrue(all(path.stat().st_mode & 0o777==0o600 for path in self.artifacts))

    def test_restored_interrupted_group_recovers_exact_prior_artifacts(self):
        self.interrupt()
        journal = self.memory.transaction.journal.read_bytes()
        self.offline_round_trip()
        self.assertEqual(self.memory.transaction.journal.read_bytes(),journal)
        with self.memory._transaction():
            pass
        self.assertEqual({path:path.read_bytes() for path in self.artifacts},self.originals)
        self.assertFalse(self.memory.transaction.journal.exists())

    def test_restored_later_edit_blocks_every_member_of_recovery(self):
        self.interrupt()
        snapshot = self.fixture.graph().with_name('snapshot.json')
        value = json.loads(snapshot.read_text())
        value['generated_at'] = 'Synthetic retained later owner version'
        snapshot.write_text(json.dumps(value))
        before = {path:path.read_bytes() for path in self.artifacts}
        self.offline_round_trip()
        with self.assertRaisesRegex(MemoryUnavailable,'later artifact edit'):
            with self.memory._transaction():
                pass
        self.assertEqual({path:path.read_bytes() for path in self.artifacts},before)
        self.assertTrue(self.memory.transaction.journal.exists())


if __name__ == '__main__':
    unittest.main()
