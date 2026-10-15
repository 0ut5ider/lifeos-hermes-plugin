# ABOUTME: Verifies current-state return to Hermes with actual native facts and private file journals.
# ABOUTME: Exercises preserved settings, writer barriers, changed targets, and process-exit recovery.
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

from ruamel.yaml import YAML
from lifeos_hook_bridge.memory_access import MemoryUnavailable
import test_memory_export as fixture


class MemoryReturnTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixture.MemoryExportTests();self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        self.configuration=self.fixture.configuration
        self.profile=self.fixture.profile
        self.configuration.update(lambda value:value.update(ownership_enabled=True))
        (self.profile/'config.yaml').write_text('model: synthetic-model\ncustom: keep-this\nmemory:\n  provider: lifeos-hook-bridge\n  memory_enabled: false\n  user_profile_enabled: false\nplugins:\n  enabled: [lifeos, lifeos-hook-bridge, lifeos-release-manager, other]\n  entries:\n    other: {enabled: true}\nskills:\n  external_dirs: [/synthetic/other]\n')
        (self.profile/'SOUL.md').write_text('Synthetic generated LifeOS prompt.')
        self.original={name:(self.profile/name).read_bytes() for name in ('config.yaml','lifeos-memory.json','SOUL.md','memories/MEMORY.md')}
        review,self.export=self.fixture.prepare()
        self.plan=self.fixture.operation().plan(self.fixture.snapshot,self.export['signature'],self.fixture.decisions(review),account='dashboard:owner')
        self.fixture.operation().apply(self.fixture.snapshot,self.export['signature'],self.plan['signature'],account='dashboard:owner')

    def operation(self, **kwargs):
        from lifeos_hook_bridge.memory_return import MemoryReturn
        return MemoryReturn(self.configuration,**kwargs)

    def prepare(self):
        return self.operation().prepare(self.fixture.snapshot,self.export['signature'],self.plan['signature'],
            prompt='You are Hermes. Use the selected built-in memory.',account='dashboard:owner')

    def test_return_uses_reviewed_exports_and_preserves_unrelated_current_settings(self):
        prepared=self.prepare()
        result=self.operation(verify_writers=lambda:None).apply(self.fixture.snapshot,prepared['signature'],account='dashboard:owner')
        self.assertEqual(result['state'],'configured')
        self.assertTrue(result['restart_required'])
        self.assertFalse(result['application_verified'])
        config=YAML(typ='safe').load((self.profile/'config.yaml').read_bytes())
        self.assertEqual(config['memory']['provider'],'builtin')
        self.assertTrue(config['memory']['memory_enabled'])
        self.assertTrue(config['memory']['user_profile_enabled'])
        self.assertEqual(config['model'],'synthetic-model')
        self.assertEqual(config['custom'],'keep-this')
        self.assertEqual(config['plugins']['enabled'],['lifeos-release-manager','other'])
        self.assertEqual(config['skills']['external_dirs'],['/synthetic/other'])
        self.assertFalse(self.configuration.load()['ownership_enabled'])
        self.assertIn('Synthetic newer LifeOS fact.',(self.profile/'memories/MEMORY.md').read_text())
        self.assertEqual((self.profile/'SOUL.md').read_text(),'You are Hermes. Use the selected built-in memory.')
        self.assertEqual(self.fixture.native.get(self.fixture.scope,self.fixture.saved['reference'])['status'],'ok')

    def test_shared_nested_yaml_values_do_not_change_unrelated_selections_or_plugins(self):
        data=b'''other_selection: &shared [lifeos, other]
other_entry: &entry {enabled: true, custom: keep}
plugins:
  enabled: *shared
  entries:
    lifeos: *entry
    other: *entry
memory:
  provider: lifeos-hook-bridge
'''
        result=YAML(typ='safe').load(self.operation()._configuration(data))
        self.assertEqual(result['other_selection'],['lifeos','other'])
        self.assertTrue(result['other_entry']['enabled'])
        self.assertTrue(result['plugins']['entries']['other']['enabled'])
        self.assertFalse(result['plugins']['entries']['lifeos']['enabled'])

    def test_return_requires_writer_barrier_and_refuses_later_target_edits(self):
        prepared=self.prepare()
        with self.assertRaises(MemoryUnavailable):
            self.operation().apply(self.fixture.snapshot,prepared['signature'],account='dashboard:owner')
        (self.profile/'config.yaml').write_bytes(self.original['config.yaml']+b'owner_later: keep\n')
        with self.assertRaises(MemoryUnavailable):
            self.operation(verify_writers=lambda:None).apply(self.fixture.snapshot,prepared['signature'],account='dashboard:owner')
        self.assertIn(b'owner_later: keep',(self.profile/'config.yaml').read_bytes())
        self.assertTrue(self.configuration.load()['ownership_enabled'])

    def test_return_rollback_restores_exact_bytes_and_refuses_later_builtin_facts(self):
        prepared=self.prepare()
        operation=self.operation(verify_writers=lambda:None)
        operation.apply(self.fixture.snapshot,prepared['signature'],account='dashboard:owner')
        path=self.profile/'memories/MEMORY.md'
        exported=path.read_bytes();path.write_bytes(exported+b'\nLater built-in fact.')
        with self.assertRaises(MemoryUnavailable):
            operation.rollback(self.fixture.snapshot,prepared['signature'],account='dashboard:owner')
        path.write_bytes(exported)
        self.assertEqual(operation.rollback(self.fixture.snapshot,prepared['signature'],account='dashboard:owner')['state'],'rolled_back')
        for name,data in self.original.items():self.assertEqual((self.profile/name).read_bytes(),data)
        self.assertFalse((self.profile/'memories/USER.md').exists())

    def test_real_process_exit_after_first_publication_resumes_current_state_journal(self):
        prepared=self.prepare()
        settings={'configuration':str(self.configuration.path),'snapshot':str(self.fixture.snapshot),'signature':prepared['signature']}
        code='''import json,os,sys
from pathlib import Path
from lifeos_hook_bridge.memory_service import MemoryConfiguration
from lifeos_hook_bridge.memory_return import MemoryReturn
settings=json.loads(sys.stdin.read())
def trace(frame,event,arg):
 if event=='return' and frame.f_code.co_name=='_publish_target' and frame.f_code.co_filename.endswith('/memory_return.py'):
  os._exit(73)
 return trace
sys.settrace(trace)
MemoryReturn(MemoryConfiguration(Path(settings['configuration'])),verify_writers=lambda:None).apply(Path(settings['snapshot']),settings['signature'],account='dashboard:owner')
'''
        child=subprocess.run([sys.executable,'-c',code],input=json.dumps(settings),text=True,capture_output=True,env=os.environ.copy(),timeout=45)
        self.assertEqual(child.returncode,73,child.stdout+child.stderr)
        self.assertEqual(child.stdout+child.stderr,'')
        result=self.operation(verify_writers=lambda:None).apply(self.fixture.snapshot,prepared['signature'],account='dashboard:owner')
        self.assertEqual(result['state'],'configured')
        self.assertIn('Synthetic newer LifeOS fact.',(self.profile/'memories/MEMORY.md').read_text())
