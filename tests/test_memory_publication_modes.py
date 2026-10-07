# ABOUTME: Verifies native recovery permissions for prepared and dynamically discovered files.
# ABOUTME: Runs actual Bun publication observation with synthetic files and SQLite metadata.
from pathlib import Path
import json
import os
import sqlite3
import subprocess
import unittest

from lifeos_hook_bridge.memory_access import MemoryUnavailable
import test_memory_native as fixture


class MemoryPublicationModeTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixture.NativeMemoryTests();self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.memory=self.fixture.memory
        self.target=self.memory._path('LIFEOS/USER/PRINCIPAL/PRINCIPAL_MEMORY.md')
        self.original=self.target.read_bytes()
        self.target.chmod(0o640)

    def test_prepared_recovery_preserves_exact_original_mode(self):
        with self.memory._transaction() as connection:
            self.memory.transaction.prepare('synthetic','mode-test',['LIFEOS/USER/PRINCIPAL/PRINCIPAL_MEMORY.md'])
            connection.execute('INSERT INTO operations VALUES (?,?,?,?)',('synthetic','mode-test','synthetic',json.dumps({'status':'unknown'})))
            connection.commit()
            self.target.write_text('Synthetic interrupted publication')
            self.target.chmod(0o600)
            self.memory.transaction.recover(connection)
        self.assertEqual(self.target.read_bytes(),self.original)
        self.assertEqual(self.target.stat().st_mode & 0o777,0o640)

    def test_invalid_recovery_mode_refuses_before_any_publication(self):
        with self.memory._transaction() as connection:
            self.memory.transaction.prepare('synthetic','bad-mode',['LIFEOS/USER/PRINCIPAL/PRINCIPAL_MEMORY.md'])
            original=json.loads(self.memory.transaction.journal.read_text())
            for mode in (True,-1,0o1777,[],None):
                with self.subTest(mode=mode):
                    document=json.loads(json.dumps(original));document['copies'][0]['mode']=mode
                    self.memory.transaction.journal.write_text(json.dumps(document))
                    with self.assertRaises(MemoryUnavailable):self.memory.transaction.recover(connection)
                    self.assertEqual(self.target.read_bytes(),self.original)
            self.memory.transaction.journal.unlink()

    def test_actual_bun_observer_records_existing_upgrade_permissions(self):
        directory=self.fixture.root/'LIFEOS/MEMORY/UPGRADES'
        directory.mkdir()
        target=directory/'synthetic-upgrade.md'
        target.write_bytes(b'Synthetic retained upgrade');target.chmod(0o640)
        self.memory.transaction.prepare('synthetic','dynamic-mode',[])
        program=self.fixture.home/'observe.ts'
        observer=Path(__file__).parents[1]/'lifeos_hook_bridge/memory_publication.ts'
        program.write_text('// ABOUTME: Observes one real native publication under a synthetic journal.\n'
            '// ABOUTME: Uses the exact prepared source function and owner paths.\n'
            'import {observePublication} from '+json.dumps(str(observer))+';\n'
            'observePublication(process.argv[2],process.argv[3],process.argv[4]);\n')
        child=subprocess.run([self.memory.bun,'--no-install',str(program),str(self.fixture.root),str(self.memory.transaction.journal),str(target)],text=True,capture_output=True,timeout=15)
        self.assertEqual(child.returncode,0,child.stdout+child.stderr)
        self.assertEqual(child.stdout+child.stderr,'')
        document=json.loads(self.memory.transaction.journal.read_text())
        self.assertEqual(document['copies'][0]['mode'],0o640)
        target.write_bytes(b'Synthetic interrupted upgrade');target.chmod(0o600)
        with self.memory._transaction():pass
        self.assertEqual(target.read_bytes(),b'Synthetic retained upgrade')
        self.assertEqual(target.stat().st_mode & 0o777,0o640)
