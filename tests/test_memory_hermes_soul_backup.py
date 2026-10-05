# ABOUTME: Checks native backup admission after actual interrupted soul publication.
# ABOUTME: Prevents a verified backup from carrying an unfinished external output journal.
import unittest

import test_memory_hermes_soul_writer as soul_fixture
from test_memory_native import OWNER
from lifeos_hook_bridge.memory_access import MemoryUnavailable
from lifeos_hook_bridge.memory_backup import create


class MemoryHermesSoulBackupTests(unittest.TestCase):
    def setUp(self):
        self.fixture = soul_fixture.MemoryHermesSoulWriterTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.memory = self.fixture.fixture.fixture.fixture.fixture.memory

    def test_native_backup_refuses_pending_soul_pair_then_succeeds_after_recovery(self):
        self.fixture.previous()
        self.assertEqual(self.fixture.process('interrupt').returncode, 73)
        destination = self.fixture.home / 'soul-backups/refused'
        with self.assertRaises(MemoryUnavailable):
            create(self.memory, OWNER, destination)
        self.assertFalse(destination.exists())
        self.fixture.successful('--stdout')
        result = create(self.memory, OWNER, self.fixture.home / 'soul-backups/recovered')
        self.assertEqual(result['status'], 'committed', result)
