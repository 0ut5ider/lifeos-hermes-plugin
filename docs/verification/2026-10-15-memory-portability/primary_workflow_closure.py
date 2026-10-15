# ABOUTME: Exercises detached workflow admission and failed preparation on synthetic owner profiles.
# ABOUTME: Uses actual private grants and child workers without claiming successful end-to-end acceptance.
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unittest

from optional.lifeos_release_manager import memory_workflow as workflow
from optional.lifeos_release_manager.release_stage import load_bridge
import test_memory_return as fixture
from test_profile_services import service_manager_fixture
import test_profile_services as services_fixture
import test_memory_activation as activation_fixture

OUTPUT=Path(__file__).parent
OWNER='dashboard:owner'


class WorkflowReview(unittest.TestCase):
    def setUp(self):
        self.fixture=fixture.MemoryReturnTests();self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.profile=self.fixture.profile
        shutil.copytree(Path(__file__).resolve().parents[3]/'lifeos_hook_bridge',
            self.profile/'plugins/lifeos-hook-bridge',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        self.calls=[]

    def launch(self,job,unit,action):self.calls.append((job,unit,action))

    def selected(self):
        source=load_bridge(self.profile/'plugins/lifeos-hook-bridge')
        paths=source.memory_module('memory_import_sources')
        identifier='a'*32
        snapshot=paths.directory(self.profile,identifier)
        snapshot.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
        shutil.move(self.fixture.fixture.snapshot,snapshot)
        return {'kind':'return','identifier':identifier,'signature':self.fixture.export['signature'],
                'plan_signature':self.fixture.plan['signature'],'prompt':'You are the synthetic Hermes owner agent.'},snapshot

    def worker(self,identifier,action):
        command=[sys.executable,str(Path(workflow.__file__).with_name('memory_workflow_worker.py')),
            str(self.profile/'.lifeos-portability'/identifier),action]
        return subprocess.run(command,text=True,capture_output=True,timeout=45,env=os.environ.copy())

    def test_exit_before_admission_is_recoverable(self):
        selected,_=self.selected()
        code='''import json,os,sys
from pathlib import Path
from optional.lifeos_release_manager import memory_workflow as workflow
settings=json.loads(sys.stdin.read())
def trace(frame,event,arg):
 if event=='call' and frame.f_code.co_name=='admit' and frame.f_code.co_filename.endswith('/memory_workflow.py') and frame.f_locals.get('action')=='prepare':
  os._exit(73)
 return trace
sys.settrace(trace)
workflow.queue(Path(settings['profile']),settings['selection'],owner='dashboard:owner',launch=lambda *args:None)
'''
        result=subprocess.run([sys.executable,'-c',code],input=json.dumps({'profile':str(self.profile),'selection':selected}),
            text=True,capture_output=True,timeout=45,env=os.environ.copy())
        self.assertEqual(result.returncode,73,result.stdout+result.stderr)
        current=workflow.status(self.profile,owner=OWNER)['operations'][0]
        observed={'exit':73,'state':current['state'],'errors':{}}
        for action in ('recover','rollback'):
            try:workflow.admit(self.profile,current['identifier'],action,current['review']['signature'],owner=OWNER,launch=self.launch)
            except (ValueError,RuntimeError) as error:observed['errors'][action]=str(error)
        try:workflow.queue(self.profile,selected,owner=OWNER,launch=self.launch)
        except (ValueError,RuntimeError) as error:observed['errors']['new_queue']=str(error)
        (OUTPUT/'queued-before-admission.json').write_text(json.dumps(observed,indent=2)+'\n')
        self.assertNotIn('recover',observed['errors'])

    def test_failed_return_prepare_can_recover_then_reuse_export(self):
        self.enterContext(service_manager_fixture())
        selected,snapshot=self.selected()
        queued=workflow.queue(self.profile,selected,owner=OWNER,launch=self.launch)
        first=self.worker(queued['identifier'],'prepare')
        self.assertEqual(first.returncode,1)
        self.assertTrue((snapshot/'return/plan.json').is_file())
        current=workflow.status(self.profile,owner=OWNER)['operations'][0]
        self.assertEqual(current['state'],'interrupted')
        workflow.admit(self.profile,current['identifier'],'recover',current['review']['signature'],owner=OWNER,launch=self.launch)
        recovered=self.worker(current['identifier'],'recover')
        self.assertEqual(recovered.returncode,0,recovered.stderr)
        recovered_state=workflow.status(self.profile,owner=OWNER)['operations'][0]['state']
        self.assertFalse((snapshot/'return').exists())
        self.assertTrue(any((snapshot/'return-history').iterdir()))
        services=services_fixture.ProfileServicesTests()
        services.fixture_home=self.profile.parent;services.fixture_profile=self.profile
        services.setUp();self.addCleanup(services.doCleanups)
        path=self.profile/'plugins/lifeos-hook-bridge/profile_services.py'
        original="UNITS = {'gateway': 'hermes-gateway.service', 'dashboard': 'hermes-dashboard.service',\n         'pulse': 'com.lifeos.pulse.service'}"
        text=path.read_text();self.assertIn(original,text)
        path.write_text(text.replace(original,'UNITS = '+repr(services.units)))
        second=workflow.queue(self.profile,selected,owner=OWNER,launch=self.launch)
        retried=self.worker(second['identifier'],'prepare')
        self.assertEqual(retried.returncode,0,retried.stderr)
        current=next(item for item in workflow.status(self.profile,owner=OWNER)['operations'] if item['identifier']==second['identifier'])
        self.assertEqual(current['state'],'ready')
        self.assertTrue(self.fixture.configuration.load()['ownership_enabled'])

    def test_exit_after_outer_return_plan_does_not_lose_recovery_binding(self):
        services=services_fixture.ProfileServicesTests()
        services.fixture_home=self.profile.parent;services.fixture_profile=self.profile
        services.setUp();self.addCleanup(services.doCleanups)
        path=self.profile/'plugins/lifeos-hook-bridge/profile_services.py'
        original="UNITS = {'gateway': 'hermes-gateway.service', 'dashboard': 'hermes-dashboard.service',\n         'pulse': 'com.lifeos.pulse.service'}"
        text=path.read_text();self.assertIn(original,text)
        path.write_text(text.replace(original,'UNITS = '+repr(services.units)))
        selected,snapshot=self.selected()
        queued=workflow.queue(self.profile,selected,owner=OWNER,launch=self.launch)
        code='''import json,os,sys
from pathlib import Path
from optional.lifeos_release_manager import memory_workflow as workflow
settings=json.loads(sys.stdin.read())
def trace(frame,event,arg):
 if event=='return' and frame.f_code.co_name=='prepare_return' and frame.f_code.co_filename.endswith('/memory_transition.py'):
  os._exit(73)
 return trace
sys.settrace(trace)
workflow.execute(Path(settings['profile']),settings['identifier'],'prepare')
'''
        first=subprocess.run([sys.executable,'-c',code],input=json.dumps({'profile':str(self.profile),'identifier':queued['identifier']}),
            text=True,capture_output=True,timeout=45,env=os.environ.copy())
        self.assertEqual(first.returncode,73,first.stdout+first.stderr)
        current=workflow.status(self.profile,owner=OWNER)['operations'][0]
        self.assertEqual(current['review']['state'],'preparation')
        workflow.admit(self.profile,current['identifier'],'recover',current['review']['signature'],owner=OWNER,launch=self.launch)
        recovered=self.worker(current['identifier'],'recover')
        self.assertEqual(recovered.returncode,0,recovered.stderr)
        state=workflow.status(self.profile,owner=OWNER)['operations'][0]['state']
        self.assertEqual(state,'cancelled')
        self.assertFalse((self.profile/'.lifeos-memory-transition/plan.json').exists())
        self.assertFalse((snapshot/'return').exists())
        self.assertTrue(any((self.profile/'.lifeos-memory-transition-history').iterdir()))
        self.assertTrue(any((snapshot/'return-history').iterdir()))
        second=workflow.queue(self.profile,selected,owner=OWNER,launch=self.launch)
        retried=self.worker(second['identifier'],'prepare')
        self.assertEqual(retried.returncode,0,retried.stderr)
        current=next(item for item in workflow.status(self.profile,owner=OWNER)['operations'] if item['identifier']==second['identifier'])
        self.assertEqual(current['state'],'ready')


class ActivationJobReview(unittest.TestCase):
    def test_recovery_of_failed_second_job_does_not_return_first_provider(self):
        fixture=activation_fixture.MemoryActivationTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
        profile=fixture.configuration.path.parent
        bridge=profile/'plugins/lifeos-hook-bridge'
        shutil.copytree(Path(__file__).resolve().parents[3]/'lifeos_hook_bridge',bridge,
            ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        path=bridge/'profile_services.py'
        original="UNITS = {'gateway': 'hermes-gateway.service', 'dashboard': 'hermes-dashboard.service',\n         'pulse': 'com.lifeos.pulse.service'}"
        text=path.read_text();self.assertIn(original,text)
        path.write_text(text.replace(original,'UNITS = '+repr(fixture.setup.services.units)))
        connector=Path(fixture.configuration.load()['root'])/'LIFEOS/USER/CONFIG/memory-access.json'
        configured=json.loads(connector.read_text());configured['command'][1]=str(bridge/'memory_rpc.py')
        connector.write_text(json.dumps(configured));connector.chmod(0o600)
        fixture.publish()
        source=load_bridge(bridge);paths=source.memory_module('memory_import_sources')
        identifier='a'*32;snapshot=paths.directory(profile,identifier)
        snapshot.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
        shutil.move(fixture.snapshot,snapshot)
        from optional.lifeos_release_manager.release_programs import publish
        publish(snapshot/'source-binding.json',b'{"source_identifier":null}')
        selection={'kind':'activation','identifier':identifier,'snapshot_signature':fixture.captured['snapshot_signature'],
            'plan_signature':fixture.plan['signature']}
        def launch(*args):pass
        def worker(job,action):
            return subprocess.run([sys.executable,str(Path(workflow.__file__).with_name('memory_workflow_worker.py')),
                str(profile/'.lifeos-portability'/job),action],text=True,capture_output=True,timeout=60,env=os.environ.copy())
        first=workflow.queue(profile,selection,owner=OWNER,launch=launch)
        prepared=worker(first['identifier'],'prepare');self.assertEqual(prepared.returncode,0,prepared.stderr)
        first_current=workflow.status(profile,owner=OWNER)['operations'][0]
        workflow.admit(profile,first['identifier'],'apply',first_current['review']['signature'],owner=OWNER,launch=launch)
        applied=worker(first['identifier'],'apply');self.assertEqual(applied.returncode,0,applied.stderr)
        self.assertTrue(fixture.configuration.load()['ownership_enabled'])
        second=workflow.queue(profile,selection,owner=OWNER,launch=launch)
        failed=worker(second['identifier'],'prepare');self.assertEqual(failed.returncode,1)
        second_current=next(item for item in workflow.status(profile,owner=OWNER)['operations'] if item['identifier']==second['identifier'])
        workflow.admit(profile,second['identifier'],'recover',second_current['review']['signature'],owner=OWNER,launch=launch)
        recovered=worker(second['identifier'],'recover');self.assertEqual(recovered.returncode,0,recovered.stderr)
        observed={'first_apply_exit':applied.returncode,'second_prepare_exit':failed.returncode,
            'second_recover_exit':recovered.returncode,'ownership_after_second_recovery':fixture.configuration.load()['ownership_enabled'],
            'workflow_states':{item['identifier']:item['state'] for item in workflow.status(profile,owner=OWNER)['operations']}}
        (OUTPUT/'activation-cross-job-recovery.json').write_text(json.dumps(observed,indent=2)+'\n')
        self.assertTrue(observed['ownership_after_second_recovery'],'The second failed job must not return the first configured provider')
