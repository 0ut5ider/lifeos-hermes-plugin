# ABOUTME: Checks real removal rollback exits and concurrent later built-in edits during verification.
# ABOUTME: Uses actual synthetic native data, unique user services, and fresh stock Python children.
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

import test_removal_publication as fixtures
from optional.lifeos_release_manager.release_programs import publish

OUTPUT=Path(__file__).parent
STOCK=Path('/home/outsider/.cache/lifeos-memory-portability-20261015/stock-full-9b204dad/runtime')

class FinalRecoveryReview(unittest.TestCase):
    def fixture(self):
        fixture=fixtures.RemovalPublicationTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
        return fixture

    def child_binding(self,fixture):
        source=fixture.stage/'recovery-bridge/profile_services.py';text=source.read_text()
        old="UNITS = {'gateway': 'hermes-gateway.service', 'dashboard': 'hermes-dashboard.service',\n         'pulse': 'com.lifeos.pulse.service'}"
        self.assertIn(old,text);source.write_text(text.replace(old,'UNITS = '+repr(fixture.service.fixture.units)))
        fixture.policy.plan['bridge_files'][str(source.relative_to(fixture.stage/'recovery-bridge'))]=hashlib.sha256(source.read_bytes()).hexdigest()
        data=json.dumps(fixture.policy.plan,sort_keys=True,separators=(',',':')).encode()
        fixture.signature=hashlib.sha256(data).hexdigest();publish(fixture.stage/'plan.json',data)
        publish(fixture.profile/'.lifeos-removal.json',json.dumps({'format':1,'workflow':fixture.policy.job.name,'signature':fixture.signature}).encode())
        publish(fixture.stage/'operation.json',json.dumps({'signature':fixture.signature,'state':'ready'}).encode())
        publish(fixture.stage/'services.json',fixture.controller.journal.read_bytes())

    def rollback_exit(self,point):
        fixture=self.fixture();self.child_binding(fixture)
        fixture.operation().apply(account='dashboard:owner')
        path=fixture.profile/'memories/MEMORY.md';before=path.read_bytes()+b'\nSynthetic before-rollback edit.';path.write_bytes(before)
        code='''import json,os,sys
from pathlib import Path
from optional.lifeos_release_manager.removal_publication import RemovalPublication
s=json.load(sys.stdin)
def checkpoint(point):
 if point==s['point']:os._exit(74)
RemovalPublication(Path(s['profile']),s['signature']).rollback(account='dashboard:owner',checkpoint=checkpoint)
'''
        result=subprocess.run([sys.executable,'-B','-c',code],input=json.dumps({'profile':str(fixture.profile),'signature':fixture.signature,'point':point}),
            capture_output=True,text=True,timeout=45,env=os.environ.copy())
        self.assertEqual(result.returncode,74,result.stdout+result.stderr);self.assertEqual(result.stdout+result.stderr,'')
        self.assertEqual(path.read_bytes(),before)
        later=before+b'\nSynthetic post-exit builtin edit.';path.write_bytes(later)
        first=fixture.operation().rollback(account='dashboard:owner');second=fixture.operation().rollback(account='dashboard:owner')
        self.assertEqual(first['state'],'rolled_back');self.assertEqual(second['state'],'rolled_back')
        self.assertEqual(path.read_bytes(),later);self.assertTrue(fixture.program.is_file());self.assertTrue(fixture.policy.configuration.path.is_file())
        self.assertEqual(fixture.service.fixture.properties('pulse')['MainPID'],'0')
        self.assertEqual(fixture.service.fixture.properties('gateway')['ActiveState'],'active')
        self.assertEqual(fixture.service.fixture.properties('dashboard')['ActiveState'],'active')
        observed={'real_exit':74,'point':point,'repeated_rollback':'rolled_back','later_builtin_bytes_retained':True,
            'software_restored':True,'owner_policy_restored':True,'pulse_stopped':True,'hermes_services_active':True}
        (OUTPUT/('rollback-'+point+'.json')).write_text(json.dumps(observed,indent=2)+'\n')

    def test_real_exit_after_rollback_drain_resumes_and_preserves_later_builtin(self):self.rollback_exit('drained')
    def test_real_exit_after_program_restore_resumes_and_preserves_later_builtin(self):self.rollback_exit('programs-restored')

    @unittest.skipUnless((STOCK/'runtime.json').is_file(),'Actual stock runtime is required')
    def test_builtin_edit_after_fresh_probe_refuses_then_reverifies_current_bytes(self):
        fixture=self.fixture()
        publish(fixture.profile/'config.yaml',b'model: {default: synthetic-model, provider: custom, base_url: "http://127.0.0.1:9/v1", api_key: "synthetic-test-key"}\nmemory: {memory_enabled: true, user_profile_enabled: true}\nplugins: {enabled: []}\nplatforms: {discord: {enabled: false}}\n')
        publish(fixture.profile/'memories/USER.md',b'Synthetic retained user entry.')
        publish(fixture.profile/'SOUL.md',b'Synthetic retained prompt.')
        fixture.operation().apply(account='dashboard:owner')
        from optional.lifeos_release_manager.memory_workflow import _probe
        from optional.lifeos_release_manager.release_stage import load_bridge
        source=load_bridge(fixture.stage/'recovery-bridge');runtime=json.loads((STOCK/'runtime.json').read_bytes())
        path=fixture.profile/'memories/MEMORY.md';later=path.read_bytes()+b'\n\n---\n\nSynthetic later verification edit.'
        def actual_probe_then_edit(expected):
            proof=_probe(fixture.profile,source,expected,runtime=runtime);path.write_bytes(later);return proof
        with self.assertRaisesRegex(ValueError,'files change'):
            fixture.operation().verify(actual_probe_then_edit,account='dashboard:owner')
        self.assertEqual(path.read_bytes(),later);self.assertEqual(fixture.operation()._load(),'verification_required')
        result=fixture.operation().verify(lambda expected:_probe(fixture.profile,source,expected,runtime=runtime),account='dashboard:owner')
        self.assertTrue(result['application_verified']);self.assertEqual(result['state'],'verified');self.assertEqual(path.read_bytes(),later)
        (OUTPUT/'late-builtin-verification.json').write_text(json.dumps({'first_verification':'refused-current-file-change',
            'retry':'verified','later_builtin_bytes_retained':True,'fresh_actual_constructor':True,'model_turn_executed':False},indent=2)+'\n')
