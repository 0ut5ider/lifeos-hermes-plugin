# ABOUTME: Exercises software removal publication with actual native data and user services.
# ABOUTME: Verifies interrupted resume and software rollback preserve later built-in memory.
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest
from unittest import mock

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

    def host(self):
        """Bind the plan to a disposable Hermes Git checkout so that removal runs as an in-place removal."""
        directory=tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR'));self.addCleanup(directory.cleanup)
        source=Path(directory.name)/'hermes';source.mkdir()
        subprocess.run(['git','init','-q',str(source)],check=True,capture_output=True)
        self.policy.plan['host']={'source':str(source),'commit':'b'*40}
        data=json.dumps(self.policy.plan,sort_keys=True,separators=(',',':')).encode()
        self.signature=hashlib.sha256(data).hexdigest();publish(self.stage/'plan.json',data)
        publish(self.profile/'.lifeos-removal.json',json.dumps({'format':1,'workflow':self.policy.job.name,'signature':self.signature}).encode())
        publish(self.stage/'operation.json',json.dumps({'signature':self.signature,'state':'ready'}).encode())
        environment=mock.patch.dict(os.environ,{'HERMES_HOME':str(self.profile)});environment.start();self.addCleanup(environment.stop)
        from hermes_cli.update_lock import checkout_lock_held
        events=[]
        def synchronize(stage,plan,label):
            events.append((label,checkout_lock_held(source)))
            return {}
        synchronizer=mock.patch('optional.lifeos_release_manager.inplace_removal.synchronize',synchronize)
        synchronizer.start();self.addCleanup(synchronizer.stop)
        resume=self.controller.resume
        def restart(*arguments,**options):
            events.append(('resume',checkout_lock_held(source)))
            return resume(*arguments,**options)
        self.controller.resume=restart
        return source,events

    def other_update(self, source):
        """Hold the Hermes checkout update lock from another process, as a concurrent hermes update does."""
        code='import sys\nfrom hermes_cli.update_lock import UpdateLock\nlock=UpdateLock(install_root=sys.argv[1])\nprint(lock.acquire(),flush=True)\nsys.stdin.read()\n'
        process=subprocess.Popen([sys.executable,'-B','-c',code,str(source)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True)
        def finish():
            if process.poll() is None:process.stdin.close();process.wait(timeout=30);process.stdout.close()
        self.addCleanup(finish)
        self.assertEqual(process.stdout.readline(),'True\n')
        return finish

    def test_in_place_removal_holds_the_update_lock_until_the_services_restart(self):
        source,events=self.host()
        from hermes_cli.update_lock import checkout_lock_held
        def checkpoint(point):events.append((point,checkout_lock_held(source)))
        result=self.operation().apply(account='dashboard:owner',checkpoint=checkpoint)
        self.assertEqual(result['state'],'verification_required')
        self.assertIn(('drained',True),events);self.assertIn(('programs-published',True),events)
        self.assertIn(('dependency-removal',True),events);self.assertIn(('dependencies-synchronized',True),events)
        self.assertIn(('resume',False),events);self.assertNotIn(('resume',True),events)
        self.assertFalse(checkout_lock_held(source))
        events.clear()
        result=self.operation().rollback(account='dashboard:owner',checkpoint=checkpoint)
        self.assertEqual(result['state'],'rolled_back')
        self.assertIn(('drained',True),events);self.assertIn(('programs-restored',True),events)
        self.assertIn(('dependency-restore',True),events)
        self.assertIn(('resume',False),events);self.assertNotIn(('resume',True),events)
        self.assertFalse(checkout_lock_held(source))

    def test_running_hermes_update_refuses_removal_rollback_and_recovery_before_service_stop(self):
        source,events=self.host()
        from hermes_cli.update_lock import checkout_lock_held
        pids={role:self.service.fixture.properties(role)['MainPID'] for role in self.service.fixture.units}
        finish=self.other_update(source)
        for action in (self.operation().apply,self.operation().rollback):
            with self.assertRaisesRegex(ValueError,'A Hermes update is running'):action(account='dashboard:owner')
        self.assertEqual({role:self.service.fixture.properties(role)['MainPID'] for role in self.service.fixture.units},pids)
        self.assertEqual(json.loads((self.stage/'operation.json').read_bytes())['state'],'ready')
        self.assertTrue(self.program.exists());self.assertEqual(events,[])
        finish()
        def checkpoint(point):
            if point=='programs-published':raise InterruptedError('Synthetic removal interruption')
        with self.assertRaises(InterruptedError):self.operation().apply(account='dashboard:owner',checkpoint=checkpoint)
        self.assertFalse(checkout_lock_held(source))
        self.other_update(source);events.clear()
        for action in (self.operation().apply,self.operation().rollback):
            with self.assertRaisesRegex(ValueError,'A Hermes update is running'):action(account='dashboard:owner')
        self.assertEqual(json.loads((self.stage/'operation.json').read_bytes())['state'],'publishing')
        self.assertFalse(self.program.exists());self.assertEqual(events,[])

    def test_removed_software_verifies_through_actual_fresh_stock_constructor(self):
        runtime=Path(os.environ.get('LIFEOS_STOCK_RUNTIME','/home/outsider/.cache/lifeos-memory-portability-20261015/stock-full-9b204dad/runtime'))
        if not (runtime/'runtime.json').is_file():self.skipTest('Constructed stock runtime is required')
        publish(self.profile/'config.yaml',b'model: {default: synthetic-model, provider: custom, base_url: "http://127.0.0.1:9/v1", api_key: "synthetic-test-key"}\nmemory: {memory_enabled: true, user_profile_enabled: true}\nplugins: {enabled: []}\nplatforms: {discord: {enabled: false}}\n')
        publish(self.profile/'memories/USER.md',b'Synthetic reviewed user entry.')
        publish(self.profile/'SOUL.md',b'Synthetic ordinary Hermes prompt.')
        self.operation().apply(account='dashboard:owner')
        from optional.lifeos_release_manager.memory_workflow import run_transition_probe
        source=self.policy.stage/'recovery-bridge'
        from optional.lifeos_release_manager.release_stage import load_bridge
        loaded=load_bridge(source)
        result=self.operation().verify(lambda expected:run_transition_probe(self.profile,loaded,expected,
            runtime=json.loads((runtime/'runtime.json').read_bytes())),account='dashboard:owner')
        self.assertEqual(result['state'],'verified');self.assertTrue(result['application_verified'])
        self.assertNotIn('lifeos-release-manager',result['verification']['active_plugins'])
        self.assertFalse(result['verification']['model_turn_executed'])
