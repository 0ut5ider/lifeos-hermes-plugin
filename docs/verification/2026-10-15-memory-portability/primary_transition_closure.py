# ABOUTME: Reproduces provider transition crash and lifecycle boundaries with synthetic actual services.
# ABOUTME: Keeps independent review probes separate from product and acceptance tests.
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

import test_memory_transition as transition_fixture
import test_memory_activation as activation_fixture
from lifeos_hook_bridge.memory_access import MemoryUnavailable

OUTPUT=Path(__file__).parent


class TransitionReview(unittest.TestCase):
    def setUp(self):
        self.fixture=transition_fixture.MemoryTransitionTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def test_exit_between_transition_intent_and_service_intent(self):
        review=self.fixture.prepare()
        settings={'configuration':str(self.fixture.returned.configuration.path),
                  'units':self.fixture.services.units,'signature':review['signature']}
        code='''import json,os,sys
from pathlib import Path
from lifeos_hook_bridge.memory_service import MemoryConfiguration
from lifeos_hook_bridge.memory_transition import MemoryTransition
settings=json.loads(sys.stdin.read())
def trace(frame,event,arg):
 if event=='return' and frame.f_code.co_name=='_state' and frame.f_code.co_filename.endswith('/memory_transition.py') and frame.f_locals.get('state')=='draining':
  os._exit(73)
 return trace
sys.settrace(trace)
MemoryTransition(MemoryConfiguration(Path(settings['configuration'])),units=settings['units']).apply(settings['signature'],account='dashboard:owner')
'''
        child=subprocess.run([sys.executable,'-c',code],input=json.dumps(settings),text=True,capture_output=True,timeout=45,env=os.environ.copy())
        self.assertEqual(child.returncode,73,child.stdout+child.stderr)
        self.assertEqual(child.stdout+child.stderr,'')
        observed={'exit':child.returncode,'status':self.fixture.operation().status(review['signature'],account='dashboard:owner'),'errors':{}}
        for action in ('apply','rollback'):
            try:getattr(self.fixture.operation(),action)(review['signature'],account='dashboard:owner')
            except MemoryUnavailable as error:observed['errors'][action]=str(error)
        observed['pids']={role:self.fixture.services.properties(role)['MainPID'] for role in self.fixture.services.units}
        (OUTPUT/'crash-before-service-journal.json').write_text(json.dumps(observed,indent=2)+'\n')
        self.assertEqual(observed['errors'],{},'Both recovery choices must work after durable transition intent')

    def test_enabled_runtime_pulse_returns_and_rolls_back(self):
        fixture=self.fixture.services
        definition=fixture.home/'units'/fixture.units['pulse']
        definition.write_text(definition.read_text()+'[Install]\nWantedBy=default.target\n')
        fixture.command('systemctl','--user','--quiet','enable','--runtime',fixture.units['pulse'])
        fixture.command('systemctl','--user','daemon-reload')
        self.assertEqual(self.fixture.operation()._enablement(),'enabled-runtime')
        pids={role:fixture.properties(role)['MainPID'] for role in fixture.units}
        with self.assertRaisesRegex(MemoryUnavailable,'regular installed user service'):
            self.fixture.prepare()
        self.assertEqual(self.fixture.operation()._enablement(),'enabled-runtime')
        self.assertEqual({role:fixture.properties(role)['MainPID'] for role in fixture.units},pids)
        self.assertTrue(self.fixture.returned.configuration.load()['ownership_enabled'])
        self.assertFalse((self.fixture.operation().directory/'plan.json').exists())


class ActivationReview(unittest.TestCase):
    def setUp(self):
        self.fixture=activation_fixture.MemoryActivationTests()
        self.addCleanup(self.fixture.doCleanups)
        try:self.fixture.setUp()
        except ValueError as error:
            self.assertIn('native import destination',str(error))
            review=self.fixture.importer.preview(account='dashboard:owner')
            decisions=[{'id':item['id'],'action':'import','required':True,
                'category':'principal' if source['path'].endswith('USER.md') else 'project',
                'project':'lab','title':'Synthetic activation review','content':item['content']}
                for source in review['sources'] for item in source['chunks'] if item['content']]
            self.fixture.plan=self.fixture.importer.plan(self.fixture.snapshot,
                self.fixture.captured['snapshot_signature'],decisions,account='dashboard:owner')

    def test_cancelled_activation_can_be_prepared_again(self):
        self.fixture.publish()
        review=self.fixture.prepare()
        recovered=self.fixture.operation().recover(account='dashboard:owner')
        self.assertEqual(recovered['state'],'cancelled')
        destination=self.fixture.setup.backup.destination.with_name('second-activation-backup')
        observed={'first':review,'recovered':recovered}
        try:
            observed['second']=self.fixture.operation().prepare(self.fixture.snapshot,self.fixture.captured['snapshot_signature'],self.fixture.plan['signature'],destination,account='dashboard:owner')
        except MemoryUnavailable as error:observed['error']=str(error)
        (OUTPUT/'cancelled-activation-retry.json').write_text(json.dumps(observed,indent=2)+'\n')
        self.assertNotIn('error',observed,'An explicitly recovered cancellation must permit a new review')

    def test_reference_changed_after_final_admission_does_not_activate(self):
        from test_memory_native import OWNER
        publication=self.fixture.publish()
        review=self.fixture.prepare()
        changed=False
        def trace(frame,event,arg):
            nonlocal changed
            if not changed and event=='call' and frame.f_code.co_name=='apply' and frame.f_code.co_filename.endswith('/memory_ownership.py'):
                changed=True
                self.fixture.importer.memory.correct(OWNER,publication['items'][0]['receipt']['reference'],
                    'Synthetic correction inside ownership publication admission.','activation-race-probe')
            return trace
        observed={}
        sys.settrace(trace)
        try:
            try:observed['result']=self.fixture.operation().apply(review['signature'],account='dashboard:owner')
            except MemoryUnavailable as error:observed['error']=str(error)
        finally:sys.settrace(None)
        observed['changed']=changed
        observed['ownership_enabled']=self.fixture.configuration.load()['ownership_enabled']
        (OUTPUT/'activation-changed-reference-boundary.json').write_text(json.dumps(observed,indent=2)+'\n')
        self.assertTrue(changed)
        self.assertFalse(observed['ownership_enabled'],'Changed required references must not enable ownership')
