# ABOUTME: Reviews fresh ownership connector recovery against synthetic native data and real services.
# ABOUTME: Checks owner refusal, later edits, and process interruption without changing product source.
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

from lifeos_hook_bridge.memory_access import MemoryUnavailable
from test_memory_activation import MemoryActivationTests
import test_memory_native as native_fixture


class ConnectorControls(unittest.TestCase):
    def setUp(self):
        self.fixture=MemoryActivationTests(); self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.configuration=self.fixture.configuration
        self.path=Path(self.configuration.load()['root']).parent/'.config/LIFEOS/USER/CONFIG/memory-access.json'
        self.path.unlink(); self.fixture.publish(); self.review=self.fixture.prepare()
        self.operation=self.fixture.operation

    def apply(self):
        return self.operation().apply(self.review['signature'],account='dashboard:owner')

    def test_wrong_owner_cannot_publish_or_stop_services(self):
        before=self.fixture.setup.pids()
        with self.assertRaises(PermissionError):
            self.operation().apply(self.review['signature'],account='dashboard:other')
        self.assertFalse(self.path.exists())
        self.assertEqual(self.fixture.setup.pids(),before)
        self.assertFalse(self.configuration.load()['ownership_enabled'])

    def test_return_refuses_later_connector_content(self):
        self.apply(); changed=b'Synthetic later connector owner edit\n'; self.path.write_bytes(changed)
        before={name:(self.configuration.path.parent/name).read_bytes() for name in ('config.yaml','lifeos-memory.json')}
        with self.assertRaisesRegex(MemoryUnavailable,'later native memory connector'):
            self.operation().recover(account='dashboard:owner')
        self.assertEqual(self.path.read_bytes(),changed)
        for name,data in before.items():self.assertEqual((self.configuration.path.parent/name).read_bytes(),data)

    def test_return_refuses_later_connector_mode(self):
        self.apply(); data=self.path.read_bytes();self.path.chmod(0o640)
        with self.assertRaisesRegex(MemoryUnavailable,'later native memory connector'):
            self.operation().recover(account='dashboard:owner')
        self.assertEqual(self.path.read_bytes(),data);self.assertEqual(self.path.stat().st_mode & 0o777,0o640)

    def test_return_keeps_later_native_fact_and_forget(self):
        self.apply(); fixture=self.fixture.setup.backup.fixture.fixture
        saved=fixture.remember('Synthetic fresh connector later fact','review-fresh-connector-later')
        original=self.fixture.setup.backup.saved['reference']
        fixture.memory.forget(native_fixture.OWNER,original,'review-fresh-connector-forget')
        returned=self.operation().recover(account='dashboard:owner')
        self.assertEqual(returned['state'],'returned');self.assertFalse(self.path.exists())
        self.assertEqual(fixture.memory.get(native_fixture.OWNER,saved['reference'])['content'],'Synthetic fresh connector later fact')
        self.assertEqual(fixture.memory.recall(native_fixture.OWNER,'coherent profile backup'),[])

    def test_exit_after_connector_deletion_can_recover(self):
        self.apply()
        code='''import json,os,sys
from pathlib import Path
from lifeos_hook_bridge.memory_service import MemoryConfiguration
from lifeos_hook_bridge.memory_activation import MemoryActivation
settings=json.load(sys.stdin)
def trace(frame,event,arg):
 if event=='return' and frame.f_code.co_name=='unlink' and frame.f_locals.get('self')==Path(settings['connector']):os._exit(73)
 return trace
sys.settrace(trace)
MemoryActivation(MemoryConfiguration(Path(settings['configuration'])),units=settings['units']).recover(account='dashboard:owner')
'''
        settings={'configuration':str(self.configuration.path),'connector':str(self.path),'units':self.fixture.setup.services.units}
        child=subprocess.run([sys.executable,'-c',code],input=json.dumps(settings),text=True,capture_output=True,env=os.environ.copy(),timeout=30)
        self.assertEqual(child.returncode,73,child.stdout+child.stderr);self.assertEqual(child.stdout+child.stderr,'')
        self.assertFalse(self.path.exists());self.assertFalse(self.configuration.load()['ownership_enabled'])
        result=self.operation().recover(account='dashboard:owner')
        self.assertEqual(result['state'],'returned');self.assertFalse(self.path.exists())
        self.assertTrue(all(pid!='0' for pid in self.fixture.setup.pids().values()))

    def test_return_preserves_connector_edit_during_final_writer_check(self):
        self.apply(); calls=0; edited=False
        def trace(frame,event,arg):
            nonlocal calls,edited
            caller=frame.f_back
            if (event=='return' and frame.f_code.co_name=='verify_stopped' and caller is not None
                    and caller.f_code.co_name=='rollback' and caller.f_code.co_filename.endswith('/memory_ownership.py')):
                calls+=1
                if calls==3:
                    self.path.write_bytes(b'Synthetic later connector during final writer check\n');edited=True
            return trace
        sys.settrace(trace)
        try:
            try:self.operation().recover(account='dashboard:owner')
            except MemoryUnavailable:pass
        finally:sys.settrace(None)
        self.assertTrue(edited);self.assertTrue(self.path.exists(),'Recovery deletes a connector edit made during the final actual writer check')
        self.assertEqual(self.path.read_bytes(),b'Synthetic later connector during final writer check\n')

    def test_application_preserves_connector_created_during_final_writer_check(self):
        edited=False
        def trace(frame,event,arg):
            nonlocal edited
            caller=frame.f_back
            if (not edited and event=='return' and frame.f_code.co_name=='verify_stopped' and caller is not None
                    and caller.f_code.co_name=='apply' and caller.f_code.co_filename.endswith('/memory_ownership.py')):
                self.path.write_bytes(b'Synthetic owner connector created during final writer check\n');edited=True
            return trace
        sys.settrace(trace)
        try:
            try:self.apply()
            except MemoryUnavailable:pass
        finally:sys.settrace(None)
        self.assertTrue(edited)
        self.assertEqual(self.path.read_bytes(),b'Synthetic owner connector created during final writer check\n',
            'Application overwrites a connector created during the final actual writer check')
