# ABOUTME: Exercises actual process exits after publishing complete workflow directories.
# ABOUTME: Verifies post-rename recovery and inactive preparation retention on synthetic owner profiles.
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

from optional.lifeos_release_manager import memory_workflow as workflow
import test_profile_services as service_fixture

fixture_module=importlib.import_module(__package__+'.previous_workflow_controls')
OUTPUT=Path(__file__).parent
OWNER='dashboard:owner'


class RenameControls(unittest.TestCase):
    def setUp(self):
        self.fixture=fixture_module.WorkflowReview();self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.profile=self.fixture.profile

    def run_boundary(self,phase):
        if phase=='outer':
            services=service_fixture.ProfileServicesTests()
            services.fixture_home=self.profile.parent;services.fixture_profile=self.profile
            services.setUp();self.addCleanup(services.doCleanups)
            path=self.profile/'plugins/lifeos-hook-bridge/profile_services.py'
            original="UNITS = {'gateway': 'hermes-gateway.service', 'dashboard': 'hermes-dashboard.service',\n         'pulse': 'com.lifeos.pulse.service'}"
            content=path.read_text();self.assertIn(original,content)
            path.write_text(content.replace(original,'UNITS = '+repr(services.units)))
        selected,snapshot=self.fixture.selected()
        queued=None if phase=='queue' else workflow.queue(self.profile,selected,owner=OWNER,launch=self.fixture.launch)
        code='''import json,os,sys
from pathlib import Path
from optional.lifeos_release_manager import memory_workflow as workflow
settings=json.loads(sys.stdin.read())
def trace(frame,event,arg):
 if event=='line':
  phase=settings['phase'];name=frame.f_code.co_name;filename=frame.f_code.co_filename
  if phase=='queue' and name=='queue' and filename.endswith('/memory_workflow.py'):
   job=frame.f_locals.get('job')
   if job is not None and not job.exists() and (Path(settings['profile'])/'.lifeos-portability'/job.name/'status.json').is_file():os._exit(73)
  if phase=='inner' and name=='prepare' and filename.endswith('/memory_return.py'):
   state=frame.f_locals.get('state');final=frame.f_locals.get('final')
   if state is not None and final is not None and not state.exists() and (final/'operation.json').is_file():os._exit(73)
  if phase=='outer' and name=='prepare_return' and filename.endswith('/memory_transition.py'):
   stage=frame.f_locals.get('stage');operation=frame.f_locals.get('self')
   if stage is not None and not stage.exists() and (operation.directory/'operation.json').is_file():os._exit(73)
 return trace
sys.settrace(trace)
if settings['phase']=='queue':workflow.queue(Path(settings['profile']),settings['selection'],owner='dashboard:owner',launch=lambda *args:None)
else:workflow.execute(Path(settings['profile']),settings['identifier'],'prepare')
'''
        child=subprocess.run([sys.executable,'-c',code],input=json.dumps({'profile':str(self.profile),'phase':phase,
            'selection':selected,'identifier':queued['identifier'] if queued else None}),
            capture_output=True,text=True,timeout=45,env=os.environ.copy())
        self.assertEqual(child.returncode,73,child.stdout+child.stderr)
        current=workflow.status(self.profile,owner=OWNER)['operations'][0]
        workflow.admit(self.profile,current['identifier'],'recover',current['review']['signature'],owner=OWNER,launch=self.fixture.launch)
        result=self.fixture.worker(current['identifier'],'recover');self.assertEqual(result.returncode,0,result.stderr)
        cancelled=workflow.status(self.profile,owner=OWNER)['operations'][0]
        self.assertEqual(cancelled['state'],'cancelled')
        self.assertFalse((snapshot/'return').exists())
        self.assertFalse((self.profile/'.lifeos-memory-transition/plan.json').exists())
        observed={'phase':phase,'child_exit':child.returncode,'recovery_exit':result.returncode,'state':cancelled['state'],
            'inner_history':len(list((snapshot/'return-history').iterdir())) if (snapshot/'return-history').exists() else 0,
            'outer_history':len(list((self.profile/'.lifeos-memory-transition-history').iterdir())) if (self.profile/'.lifeos-memory-transition-history').exists() else 0}
        if phase!='queue':
            review=self.fixture.fixture.operation().prepare(snapshot,selected['signature'],selected['plan_signature'],prompt=selected['prompt'],account=OWNER)
            self.assertEqual(review['state'],'ready');observed['same_export_reusable']=True
        (OUTPUT/('renamed-'+phase+'.json')).write_text(json.dumps(observed,indent=2)+'\n')

    def test_complete_queue_rename_recovers(self):self.run_boundary('queue')
    def test_complete_inner_rename_recovers(self):self.run_boundary('inner')
    def test_complete_outer_rename_recovers(self):self.run_boundary('outer')
