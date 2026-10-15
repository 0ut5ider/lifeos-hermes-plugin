# ABOUTME: Verifies the removal-only retained data barrier without installed native tools.
# ABOUTME: Uses actual SQLite and writer locks while forbidding schema changes and pending recovery.
import json
from contextlib import closing
from pathlib import Path
import shutil
import sqlite3
import unittest

import test_memory_export as fixture


class RemovalDataBarrierTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixture.MemoryExportTests();self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        self.memory=self.fixture.native;self.data=self.memory.database.read_bytes()
        self.tools=self.memory.root/'LIFEOS/TOOLS';self.tools.unlink()

    def barrier(self):
        from optional.lifeos_release_manager.removal_data import barrier
        return barrier(self.memory)

    def test_retained_registry_verification_works_without_tools_and_changes_no_data(self):
        with self.barrier() as connection:
            count=connection.execute('SELECT count(*) FROM records').fetchone()[0]
            self.assertGreater(count,0)
            with self.assertRaises(sqlite3.OperationalError):connection.execute('DELETE FROM records')
        self.assertEqual(self.memory.database.read_bytes(),self.data)
        with self.assertRaisesRegex(RuntimeError,'tools are unavailable'):
            with self.memory._transaction():pass

    def test_pending_native_publication_and_unknown_schema_refuse_without_recovery(self):
        pending=self.memory.transaction.journal;pending.write_text('{"synthetic":"unresolved"}')
        with self.assertRaises(ValueError):
            with self.barrier():pass
        self.assertEqual(json.loads(pending.read_text()),{'synthetic':'unresolved'})
        pending.unlink()
        with closing(sqlite3.connect(self.memory.database)) as connection,connection:
            connection.execute('PRAGMA user_version=99')
        before=self.memory.database.read_bytes()
        with self.assertRaises(ValueError):
            with self.barrier():pass
        self.assertEqual(self.memory.database.read_bytes(),before)

    def test_replaced_native_data_link_refuses_the_barrier(self):
        memory=self.memory.root/'LIFEOS/MEMORY';memory.unlink();memory.mkdir()
        with self.assertRaises(RuntimeError):
            with self.barrier():pass
