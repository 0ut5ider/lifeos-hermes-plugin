# ABOUTME: Exercises software removal publication with actual native data and user services.
# ABOUTME: Verifies interrupted resume and software rollback preserve later built-in memory.
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
import unittest

import test_removal_state as policy_fixture
import test_removal_services as services_fixture
from optional.lifeos_release_manager.release_programs import ProgramTransaction,publish


class RemovalPublicationTests(unittest.TestCase):
    def setUp(self):
        self.policy=policy_fixture.RemovalStateTests();self.policy.setUp();self.addCleanup(self.policy.doCleanups)
        self.profile=self.policy.profile;self.stage=self.policy.stage
        root=Path(self.policy.configuration.load()['root'])
        self.service=services_fixture.RemovalServicesTests()
        self.service.fixture_home=root.parent;self.service.fixture_profile=self.profile
        self.service.setUp();self.addCleanup(self.service.doCleanups)
        self.controller=self.service.operation()
        service_signature=self.controller.prepare(removed=[self.service.installed_pulse])
        self.program=root/'SyntheticRemoval.ts';self.program.write_text('// Synthetic selected program\n')
        self.programs=ProgramTransaction(self.stage/'programs')
        self.programs.prepare(directories={},files={self.program:None,self.policy.configuration.path:None,self.service.installed_pulse:None})
        self.policy.plan.update(program_entries_sha256=self.programs.entries_digest(),service_signature=service_signature)
        from optional.lifeos_release_manager.removal_state import retained
        source,configuration,_,_=retained(self.profile)
        importer=source.memory_module('memory_import').MemoryImport(configuration)
        with importer.memory._transaction() as connection:self.policy.plan['native_signature']=importer._target_signature(connection)
        data=json.dumps(self.policy.plan,sort_keys=True,separators=(',',':')).encode()
        self.signature=hashlib.sha256(data).hexdigest();publish(self.stage/'plan.json',data)
        publish(self.profile/'.lifeos-removal.json',json.dumps({'format':1,'workflow':self.policy.job.name,'signature':self.signature}).encode())
        publish(self.stage/'operation.json',json.dumps({'signature':self.signature,'state':'ready'}).encode())
        self.original_memory=(self.profile/'memories/MEMORY.md').read_bytes()

    def operation(self):
        from optional.lifeos_release_manager.removal_publication import RemovalPublication
        return RemovalPublication(self.profile,self.signature,services=self.controller)

    def test_current_software_removal_preserves_data_and_later_builtin_memory_on_rollback(self):
        result=self.operation().apply(account='dashboard:owner')
        self.assertEqual(result['state'],'verification_required');self.assertFalse(result['application_verified'])
        self.assertFalse(self.program.exists());self.assertFalse(self.policy.configuration.path.exists())
        self.assertEqual((self.profile/'memories/MEMORY.md').read_bytes(),self.original_memory)
        self.assertEqual(self.service.fixture.properties('pulse')['MainPID'],'0')
        path=self.profile/'memories/MEMORY.md';later=self.original_memory+b'\nSynthetic later builtin fact.';path.write_bytes(later)
        result=self.operation().rollback(account='dashboard:owner')
        self.assertEqual(result['state'],'rolled_back');self.assertTrue(self.program.exists())
        self.assertEqual(path.read_bytes(),later);self.assertTrue(self.policy.configuration.path.exists())
        self.assertEqual(self.service.fixture.properties('pulse')['MainPID'],'0')

    def test_interruption_after_programs_can_resume_without_repeating_data_publication(self):
        def checkpoint(point):
            if point=='programs-published':raise InterruptedError('Synthetic removal interruption')
        with self.assertRaises(InterruptedError):self.operation().apply(account='dashboard:owner',checkpoint=checkpoint)
        self.assertFalse(self.program.exists())
        result=self.operation().apply(account='dashboard:owner')
        self.assertEqual(result['state'],'verification_required')
        self.assertEqual((self.profile/'memories/MEMORY.md').read_bytes(),self.original_memory)

    def test_real_process_exit_after_first_target_resumes_without_losing_data(self):
        path=self.stage/'recovery-bridge/profile_services.py'
        text=path.read_text()
        original="UNITS = {'gateway': 'hermes-gateway.service', 'dashboard': 'hermes-dashboard.service',\n         'pulse': 'com.lifeos.pulse.service'}"
        self.assertIn(original,text);path.write_text(text.replace(original,'UNITS = '+repr(self.service.fixture.units)))
        self.policy.plan['bridge_files'][str(path.relative_to(self.stage/'recovery-bridge'))]=hashlib.sha256(path.read_bytes()).hexdigest()
        data=json.dumps(self.policy.plan,sort_keys=True,separators=(',',':')).encode()
        self.signature=hashlib.sha256(data).hexdigest();publish(self.stage/'plan.json',data)
        publish(self.profile/'.lifeos-removal.json',json.dumps({'format':1,'workflow':self.policy.job.name,'signature':self.signature}).encode())
        publish(self.stage/'operation.json',json.dumps({'signature':self.signature,'state':'ready'}).encode())
        publish(self.stage/'services.json',self.controller.journal.read_bytes())
        code='''import json,os,sys
from pathlib import Path
from optional.lifeos_release_manager.removal_publication import RemovalPublication
settings=json.load(sys.stdin)
def checkpoint(point):
 if point=='artifact-published':os._exit(73)
RemovalPublication(Path(settings['profile']),settings['signature']).apply(account='dashboard:owner',checkpoint=checkpoint)
'''
        result=subprocess.run([sys.executable,'-B','-c',code],input=json.dumps({'profile':str(self.profile),'signature':self.signature}),
            env=os.environ.copy(),capture_output=True,text=True,timeout=45)
        self.assertEqual(result.returncode,73,result.stdout+result.stderr);self.assertEqual(result.stdout+result.stderr,'')
        self.assertFalse(self.program.exists());self.assertTrue(self.policy.configuration.path.exists())
        result=self.operation().apply(account='dashboard:owner')
        self.assertEqual(result['state'],'verification_required')
        self.assertEqual((self.profile/'memories/MEMORY.md').read_bytes(),self.original_memory)

    def test_other_owner_or_later_target_edit_refuses_before_service_stop(self):
        pids={role:self.service.fixture.properties(role)['MainPID'] for role in self.service.fixture.units}
        with self.assertRaises(PermissionError):self.operation().apply(account='dashboard:other')
        self.program.write_text('// Synthetic later program edit\n')
        with self.assertRaises(ValueError):self.operation().apply(account='dashboard:owner')
        self.assertEqual({role:self.service.fixture.properties(role)['MainPID'] for role in self.service.fixture.units},pids)
        self.assertTrue(self.policy.configuration.path.exists())
