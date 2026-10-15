# ABOUTME: Verifies writer exclusion and physical registry identity in the removal-only data barrier.
# ABOUTME: Uses actual child processes and synthetic SQLite files without memory policy or tool bypass.
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import unittest

import test_memory_export as fixture
from optional.lifeos_release_manager.removal_data import barrier

OUTPUT=Path(__file__).parent


class RemovalDataControls(unittest.TestCase):
    def setUp(self):
        self.fixture=fixture.MemoryExportTests();self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        self.memory=self.fixture.native

    def test_actual_native_writer_waits_for_the_shared_lock(self):
        attempted=self.fixture.profile/'writer-attempted';acquired=self.fixture.profile/'writer-acquired'
        settings={'root':str(self.memory.root),'attempted':str(attempted),'acquired':str(acquired)}
        code='''import fcntl,json,os,sys
from pathlib import Path
from lifeos_hook_bridge.memory_access import NativeMemory
settings=json.load(sys.stdin)
memory=NativeMemory(Path(settings['root']))
descriptor=os.open(memory.transaction.state/'memory-access.lock',os.O_RDWR)
try:
 try:fcntl.flock(descriptor,fcntl.LOCK_EX|fcntl.LOCK_NB)
 except BlockingIOError:Path(settings['attempted']).write_text('actual-lock-refused')
 else:raise AssertionError('The removal barrier does not hold the native writer lock')
finally:os.close(descriptor)
with memory._transaction() as connection:
 Path(settings['acquired']).write_text('acquired')
 print(json.dumps({'records':connection.execute('SELECT count(*) FROM records').fetchone()[0]}))
'''
        child=None
        try:
            with barrier(self.memory):
                child=subprocess.Popen([sys.executable,'-B','-c',code],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                    text=True,env=os.environ.copy())
                child.stdin.write(json.dumps(settings));child.stdin.close();child.stdin=None
                deadline=time.monotonic()+5
                while not attempted.exists() and time.monotonic()<deadline:time.sleep(0.01)
                self.assertTrue(attempted.exists())
                self.assertIsNone(child.poll());self.assertFalse(acquired.exists())
            out,err=child.communicate(timeout=10)
            self.assertEqual(child.returncode,0,err);self.assertEqual(err,'');self.assertTrue(acquired.exists())
            observed={'writer_blocked_while_barrier_held':True,'writer_acquired_after_release':True,
                'child_exit':child.returncode,'records':json.loads(out)['records']}
            (OUTPUT/'shared-writer-lock.json').write_text(json.dumps(observed,indent=2)+'\n')
        finally:
            if child is not None:
                if child.poll() is None:child.kill();child.wait()
                if child.stdout is not None:child.stdout.close()
                if child.stderr is not None:child.stderr.close()

    def test_same_bytes_registry_replacement_is_refused(self):
        database=self.memory.database.resolve()
        original=database.read_bytes();replacement=database.with_name('synthetic-replacement.sqlite')
        replacement.write_bytes(original);replacement.chmod(0o600)
        with self.assertRaisesRegex(ValueError,'physical identity|changes during'):
            with barrier(self.memory):os.replace(replacement,database)
        self.assertEqual(database.read_bytes(),original)
        (OUTPUT/'registry-replacement.json').write_text(json.dumps({'replacement_refused':True,'content_unchanged':True},indent=2)+'\n')

    def test_missing_registry_is_not_created(self):
        database=self.memory.database.resolve();database.unlink()
        with self.assertRaises(FileNotFoundError):
            with barrier(self.memory):pass
        self.assertFalse(database.exists())
        (OUTPUT/'missing-registry.json').write_text(json.dumps({'missing_registry_refused':True,'database_created':False},indent=2)+'\n')
