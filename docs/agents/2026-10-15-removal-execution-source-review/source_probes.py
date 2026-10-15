# ABOUTME: Checks real owner grants and selection changes around retained-source admission.
# ABOUTME: Uses actual copied bridge namespaces and fixed synthetic services without mocking a complete removal.
import hashlib
import json
from pathlib import Path
import shutil
import sys
import unittest

import test_removal_execution_source as fixtures
from optional.lifeos_release_manager import memory_workflow
from optional.lifeos_release_manager.release_programs import publish

OUTPUT=Path(__file__).parent

class SourceAdmissionReview(unittest.TestCase):
    def fixture(self):
        fixture=fixtures.RemovalExecutionSourceTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
        plan=fixture.fixture.policy.plan
        request=json.loads((fixture.job/'request.json').read_bytes());selected=request['selection']
        plan.update(return_identifier=selected['identifier'],return_signature=selected['signature'],disable_discord=True)
        data=json.dumps(plan,sort_keys=True,separators=(',',':')).encode();fixture.signature=hashlib.sha256(data).hexdigest()
        publish(fixture.stage/'plan.json',data);publish(fixture.stage/'operation.json',json.dumps({'signature':fixture.signature,'state':'ready'}).encode())
        publish(fixture.job/'review.json',json.dumps({'state':'ready','signature':fixture.signature}).encode())
        source,configuration=memory_workflow._source(fixture.profile)
        binding={'action':'rollback','workflow':fixture.job.name,'request':hashlib.sha256(memory_workflow._encoded(request)).hexdigest(),'signature':fixture.signature}
        grant=source.memory_administration().issue(configuration,'dashboard:owner',ttl=600,binding=binding,purpose='transition')
        publish(fixture.job/'admission.json',json.dumps({'binding':binding,'authorization':str(grant)}).encode())
        publish(fixture.job/'status.json',json.dumps({'identifier':fixture.job.name,'state':'rolling_back'}).encode())
        return fixture

    def mutation_after_selection(self,fixture,mutation):
        changed=False
        def trace(frame,event,arg):
            nonlocal changed
            if event=='return' and frame.f_code is memory_workflow._source.__code__ and arg is not None and not changed:
                changed=True;mutation()
            return trace
        sys.settrace(trace)
        try:
            with self.assertRaises((ValueError,RuntimeError,PermissionError)) as caught:
                memory_workflow.execute(fixture.profile,fixture.job.name,'rollback')
        finally:sys.settrace(None)
        self.assertTrue(changed);self.assertTrue(fixture.fixture.program.exists())
        self.assertTrue(fixture.fixture.policy.configuration.path.exists())
        return caught.exception

    def test_real_active_source_grant_completes_ready_cancellation_with_retained_source(self):
        fixture=self.fixture();memory=(fixture.profile/'memories/MEMORY.md').read_bytes()
        result=memory_workflow.execute(fixture.profile,fixture.job.name,'rollback')
        self.assertEqual(result['state'],'cancelled');self.assertFalse((fixture.profile/'.lifeos-removal.json').exists())
        self.assertTrue(fixture.fixture.program.exists());self.assertEqual((fixture.profile/'memories/MEMORY.md').read_bytes(),memory)
        self.assertEqual(json.loads((fixture.job/'status.json').read_bytes())['state'],'cancelled')
        admission=json.loads((fixture.job/'admission.json').read_bytes());self.assertFalse(Path(admission['authorization']).exists())
        (OUTPUT/'authenticated-cancellation.json').write_text(json.dumps({'actual_manager_execute':True,'grant_issued_by_active_source':True,
            'reviewed_retained_source_selected':True,'result':'cancelled','grant_revoked':True,'memory_and_software_unchanged':True},indent=2)+'\n')

    def test_owner_revocation_after_grant_issue_refuses_under_retained_selection(self):
        fixture=self.fixture();fixture.fixture.policy.configuration.update(lambda value:value['accounts'].pop('dashboard:owner'))
        with self.assertRaises(PermissionError):memory_workflow.execute(fixture.profile,fixture.job.name,'rollback')
        self.assertFalse((fixture.profile/'.lifeos-removal.json').exists());self.assertTrue(fixture.fixture.program.exists())
        (OUTPUT/'revoked-grant-refusal.json').write_text(json.dumps({'grant_precedes_revocation':True,'revoked_owner_refused':True,
            'marker_absent':True,'software_retained':True},indent=2)+'\n')

    def test_review_signature_change_after_selection_refuses_existing_grant(self):
        fixture=self.fixture()
        error=self.mutation_after_selection(fixture,lambda:publish(fixture.job/'review.json',json.dumps({'state':'ready','signature':'f'*64}).encode()))
        self.assertIn('binding changed',str(error));self.assertFalse((fixture.profile/'.lifeos-removal.json').exists())
        (OUTPUT/'review-race-refusal.json').write_text(json.dumps({'changed_after_source_selection':True,'exact_grant_binding_refused':True,
            'software_and_policy_retained':True},indent=2)+'\n')

    def test_retained_source_change_after_selection_refuses_before_action(self):
        fixture=self.fixture();path=fixture.stage/'recovery-bridge/profile_services.py';data=path.read_bytes()
        error=self.mutation_after_selection(fixture,lambda:path.write_bytes(data+b'\n# Synthetic later source change\n'))
        self.assertIn('code changes',str(error));self.assertFalse((fixture.profile/'.lifeos-removal.json').exists())
        (OUTPUT/'source-race-refusal.json').write_text(json.dumps({'changed_after_source_selection':True,'request_bridge_identity_refused':True,
            'software_and_policy_retained':True},indent=2)+'\n')

    def test_other_job_marker_after_selection_cannot_borrow_selected_authority(self):
        fixture=self.fixture();other=fixture.job.with_name('e'*32);shutil.copytree(fixture.job,other)
        plan=json.loads((other/'removal/plan.json').read_bytes());plan['identifier']=other.name
        data=json.dumps(plan,sort_keys=True,separators=(',',':')).encode();signature=hashlib.sha256(data).hexdigest();publish(other/'removal/plan.json',data)
        marker={'format':1,'workflow':other.name,'signature':signature}
        error=self.mutation_after_selection(fixture,lambda:publish(fixture.profile/'.lifeos-removal.json',json.dumps(marker).encode()))
        self.assertIn('selected software removal',str(error));self.assertEqual(json.loads((fixture.profile/'.lifeos-removal.json').read_bytes()),marker)
        (OUTPUT/'other-job-race-refusal.json').write_text(json.dumps({'changed_after_source_selection':True,'other_job_marker_refused':True,
            'other_marker_retained':True,'software_and_policy_retained':True},indent=2)+'\n')
