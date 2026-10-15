# ABOUTME: Tests real process exits between durable workflow document publications.
# ABOUTME: Retains safe recovery errors and never accesses production profiles or service units.
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

from optional.lifeos_release_manager import memory_workflow as workflow
import test_profile_services as services_fixture

fixture_module=importlib.import_module(__package__+'.previous_workflow_controls')
OUTPUT=Path(__file__).parent
OWNER='dashboard:owner'


class WriteBoundaryReview(unittest.TestCase):
    def setUp(self):
        self.fixture=fixture_module.WorkflowReview();self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.profile=self.fixture.profile

    def crash(self,phase):
        selected,snapshot=self.fixture.selected()
        if phase=='outer_plan':
            services=services_fixture.ProfileServicesTests()
            services.fixture_home=self.profile.parent;services.fixture_profile=self.profile
            services.setUp();self.addCleanup(services.doCleanups)
            path=self.profile/'plugins/lifeos-hook-bridge/profile_services.py'
            original="UNITS = {'gateway': 'hermes-gateway.service', 'dashboard': 'hermes-dashboard.service',\n         'pulse': 'com.lifeos.pulse.service'}"
            content=path.read_text();self.assertIn(original,content)
            path.write_text(content.replace(original,'UNITS = '+repr(services.units)))
        queued=None if phase=='queue_request' else workflow.queue(self.profile,selected,owner=OWNER,launch=self.fixture.launch)
        code='''import json,os,sys
from pathlib import Path
from optional.lifeos_release_manager import memory_workflow as workflow
settings=json.loads(sys.stdin.read())
def trace(frame,event,arg):
 if event=='return' and frame.f_code.co_name=='publish':
  path=Path(frame.f_locals.get('path','/'))
  phase=settings['phase']
  hit=phase=='queue_request' and path.name=='request.json' and path.parent.parent.name=='.lifeos-portability'
  hit=hit or phase=='inner_copy' and path.name=='0' and path.parent.name=='before' and path.parent.parent.name=='return'
  hit=hit or phase=='inner_plan' and path.name=='plan.json' and path.parent.name=='return'
  hit=hit or phase=='outer_plan' and path.name=='plan.json' and path.parent.name=='.lifeos-memory-transition'
  if hit:os._exit(73)
 return trace
sys.settrace(trace)
if settings['phase']=='queue_request':
 workflow.queue(Path(settings['profile']),settings['selection'],owner='dashboard:owner',launch=lambda *args:None)
else:workflow.execute(Path(settings['profile']),settings['identifier'],'prepare')
'''
        child=subprocess.run([sys.executable,'-c',code],input=json.dumps({'profile':str(self.profile),
            'phase':phase,'selection':selected,'identifier':queued['identifier'] if queued else None}),
            capture_output=True,text=True,timeout=45,env=os.environ.copy())
        self.assertEqual(child.returncode,73,child.stdout+child.stderr)
        observed={'phase':phase,'child_exit':73,'errors':{}}
        if queued is None:
            job=next((self.profile/'.lifeos-portability').iterdir())
            try:workflow.status(self.profile,owner=OWNER)
            except (OSError,RuntimeError,ValueError) as error:observed['errors']['status']=type(error).__name__+': '+str(error)
            try:workflow.queue(self.profile,selected,owner=OWNER,launch=self.fixture.launch)
            except (OSError,RuntimeError,ValueError) as error:observed['errors']['queue']=type(error).__name__+': '+str(error)
            observed['request_exists']=(job/'request.json').exists()
            observed['status_exists']=(job/'status.json').exists()
        else:
            current=workflow.status(self.profile,owner=OWNER)['operations'][0]
            for attempt in range(2):
                try:
                    workflow.admit(self.profile,queued['identifier'],'recover',current['review']['signature'],owner=OWNER,launch=self.fixture.launch)
                    result=self.fixture.worker(queued['identifier'],'recover')
                    observed['recover_'+str(attempt)]={'exit':result.returncode,'stderr':result.stderr}
                except (OSError,RuntimeError,ValueError) as error:observed['errors']['recover_'+str(attempt)]=str(error)
            observed['state']=workflow.status(self.profile,owner=OWNER)['operations'][0]['state']
            observed['inner_plan_exists']=(snapshot/'return/plan.json').exists()
            observed['inner_operation_exists']=(snapshot/'return/operation.json').exists()
            observed['outer_plan_exists']=(self.profile/'.lifeos-memory-transition/plan.json').exists()
            observed['outer_operation_exists']=(self.profile/'.lifeos-memory-transition/operation.json').exists()
            if phase=='inner_copy':
                try:self.fixture.fixture.operation().prepare(snapshot,selected['signature'],selected['plan_signature'],prompt=selected['prompt'],account=OWNER)
                except (RuntimeError,ValueError) as error:observed['errors']['reprepare']=str(error)
        (OUTPUT/(phase+'.json')).write_text(json.dumps(observed,indent=2)+'\n')
        return observed

    def test_queue_request_before_status_can_recover(self):
        result=self.crash('queue_request');self.assertNotIn('status',result['errors'])

    def test_inner_copies_before_plan_can_recover(self):
        result=self.crash('inner_copy');self.assertNotIn('reprepare',result['errors'])

    def test_inner_plan_before_operation_can_recover(self):
        result=self.crash('inner_plan');self.assertEqual(result['recover_0']['exit'],0)

    def test_outer_plan_before_operation_can_recover(self):
        result=self.crash('outer_plan');self.assertEqual(result['recover_0']['exit'],0)

    def test_second_return_cancellation_preserves_first_ready_transition(self):
        services=services_fixture.ProfileServicesTests()
        services.fixture_home=self.profile.parent;services.fixture_profile=self.profile
        services.setUp();self.addCleanup(services.doCleanups)
        path=self.profile/'plugins/lifeos-hook-bridge/profile_services.py'
        original="UNITS = {'gateway': 'hermes-gateway.service', 'dashboard': 'hermes-dashboard.service',\n         'pulse': 'com.lifeos.pulse.service'}"
        content=path.read_text();self.assertIn(original,content)
        path.write_text(content.replace(original,'UNITS = '+repr(services.units)))
        selected,snapshot=self.fixture.selected()
        first=workflow.queue(self.profile,selected,owner=OWNER,launch=self.fixture.launch)
        result=self.fixture.worker(first['identifier'],'prepare');self.assertEqual(result.returncode,0,result.stderr)
        plan=self.profile/'.lifeos-memory-transition/plan.json'
        before=plan.read_bytes()
        second=workflow.queue(self.profile,selected,owner=OWNER,launch=self.fixture.launch)
        result=self.fixture.worker(second['identifier'],'prepare');self.assertEqual(result.returncode,1)
        current=next(item for item in workflow.status(self.profile,owner=OWNER)['operations'] if item['identifier']==second['identifier'])
        workflow.admit(self.profile,second['identifier'],'recover',current['review']['signature'],owner=OWNER,launch=self.fixture.launch)
        result=self.fixture.worker(second['identifier'],'recover');self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(plan.read_bytes(),before)
        values=workflow.status(self.profile,owner=OWNER)['operations']
        observed={'first_state':next(item['state'] for item in values if item['identifier']==first['identifier']),
            'second_state':next(item['state'] for item in values if item['identifier']==second['identifier']),
            'first_plan_unchanged':plan.read_bytes()==before,'provider_still_native':self.fixture.fixture.configuration.load()['ownership_enabled']}
        (OUTPUT/'cross-job-return-control.json').write_text(json.dumps(observed,indent=2)+'\n')
        self.assertEqual(observed['first_state'],'ready')
        self.assertEqual(observed['second_state'],'cancelled')
