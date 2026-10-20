# ABOUTME: Checks owner workflow recovery after removal deletes active plugins and memory configuration.
# ABOUTME: Uses real retained sources and authenticated grants without claiming installed end-to-end removal.
import hashlib
import json
from pathlib import Path
import unittest

import test_removal_state as fixture
from optional.lifeos_release_manager import memory_workflow
from optional.lifeos_release_manager.release_programs import publish,fingerprint


class MemoryRemovalWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixture.RemovalStateTests();self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        self.profile=self.fixture.profile;self.job=self.fixture.job
        self.selection={'kind':'removal','identifier':'c'*32,'signature':'d'*64,'disable_discord':True}
        self.request={'version':1,'identifier':self.job.name,'profile':str(self.profile),'owner':'dashboard:owner',
            'bridge':fingerprint(self.fixture.stage/'recovery-bridge'),'selection':self.selection}
        publish(self.job/'request.json',json.dumps(self.request).encode())
        publish(self.job/'status.json',json.dumps({'identifier':self.job.name,'state':'interrupted'}).encode())
        publish(self.job/'review.json',json.dumps({'state':'ready','signature':self.fixture.signature}).encode())
        self.fixture.configuration.path.unlink();self.launched=[]

    def launch(self,*args):self.launched.append(args)

    def test_only_a_removal_request_carries_a_login(self):
        login={'username':'owner','password_hash':'scrypt$16384$8$1$c2FsdA==$ZGs='}
        publish(self.job/'request.json',json.dumps({**self.request,'login':login}).encode())
        self.assertEqual(memory_workflow.workflow_job(self.profile,self.job.name)[1]['login'],login)
        other={**self.request,'selection':{'kind':'return','identifier':'c'*32,'signature':'d'*64,
            'plan_signature':'e'*64,'prompt':'Synthetic prompt'},'login':login}
        publish(self.job/'request.json',json.dumps(other).encode())
        with self.assertRaisesRegex(ValueError,'another profile'):memory_workflow.workflow_job(self.profile,self.job.name)
        with self.assertRaisesRegex(ValueError,'Only removal'):
            memory_workflow.queue(self.profile,{'kind':'return','identifier':'c'*32,'signature':'d'*64,
                'plan_signature':'e'*64,'prompt':'Synthetic prompt'},owner='dashboard:owner',launch=self.launch,login=login)

    def test_removal_selection_is_bounded_and_requires_explicit_discord_disablement(self):
        self.assertEqual(memory_workflow.selection(self.selection),self.selection)
        for value in ({**self.selection,'path':'/synthetic/owner'}, {**self.selection,'disable_discord':False},
                      {**self.selection,'disable_discord':1},{**self.selection,'signature':'invalid'}):
            with self.assertRaises(ValueError):memory_workflow.selection(value)

    def test_retained_owner_can_read_status_and_admit_exact_recovery_after_configuration_removal(self):
        result=memory_workflow.status(self.profile,owner='dashboard:owner')
        self.assertEqual(result['operations'][0]['kind'],'removal')
        result=memory_workflow.admit(self.profile,self.job.name,'recover',self.fixture.signature,
            owner='dashboard:owner',launch=self.launch)
        self.assertEqual(result['action'],'recover');self.assertEqual(len(self.launched),1)
        _,configuration=memory_workflow._source(self.profile)
        admission=json.loads((self.job/'admission.json').read_bytes())
        source=memory_workflow._source(self.profile)[0]
        _,scope=source.memory_administration().validate(configuration,admission['authorization'],
            binding=admission['binding'],check_binding=True,purpose='transition')
        self.assertEqual(scope.writer,'dashboard:owner')
        self.assertFalse(self.fixture.configuration.path.exists())

    def test_other_owner_and_other_workflow_cannot_use_retained_removal_authority(self):
        with self.assertRaises(PermissionError):memory_workflow.status(self.profile,owner='dashboard:other')
        with self.assertRaises(PermissionError):memory_workflow.admit(self.profile,self.job.name,'recover',self.fixture.signature,
            owner='dashboard:other',launch=self.launch)
        with self.assertRaises(RuntimeError):memory_workflow.queue(self.profile,self.selection,
            owner='dashboard:owner',launch=self.launch)
        self.assertEqual(self.launched,[])

    def test_recovery_of_completed_preparation_keeps_separate_owner_apply(self):
        from optional.lifeos_release_manager.removal_workflow import execute
        self.fixture.plan.update(return_identifier=self.selection['identifier'],return_signature=self.selection['signature'],disable_discord=True)
        encoded=json.dumps(self.fixture.plan,sort_keys=True,separators=(',',':')).encode()
        signature=hashlib.sha256(encoded).hexdigest();publish(self.fixture.stage/'plan.json',encoded)
        publish(self.fixture.stage/'operation.json',json.dumps({'signature':signature,'state':'ready'}).encode())
        publish(self.job/'review.json',json.dumps({'signature':signature,'state':'ready'}).encode())
        (self.profile/'.lifeos-removal.json').unlink()
        from optional.lifeos_release_manager.removal_state import prepared
        source,configuration,_,_=prepared(self.profile,self.job.name,signature)
        result=execute(self.profile,self.job,self.selection,'recover',signature,owner='dashboard:owner',
            source=source,configuration=configuration,installation_lease=None)
        self.assertEqual(result['state'],'ready');self.assertFalse(result['application_verified'])
        self.assertFalse((self.profile/'.lifeos-removal.json').exists())
