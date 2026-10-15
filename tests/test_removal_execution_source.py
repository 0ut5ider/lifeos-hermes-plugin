# ABOUTME: Checks first removal application uses its retained bridge before issuing an installation lease.
# ABOUTME: Exercises actual source namespaces and user services without weakening lease type or owner admission.
import hashlib
import json
from pathlib import Path
import shutil
import unittest

import test_removal_publication as fixtures
from optional.lifeos_release_manager import memory_workflow
from optional.lifeos_release_manager.release_programs import fingerprint, publish
from optional.lifeos_release_manager.removal_publication import RemovalPublication


class RemovalExecutionSourceTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixtures.RemovalPublicationTests();self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        self.profile=self.fixture.profile;self.job=self.fixture.policy.job;self.stage=self.fixture.stage
        path=self.stage/'recovery-bridge/profile_services.py';text=path.read_text()
        original="UNITS = {'gateway': 'hermes-gateway.service', 'dashboard': 'hermes-dashboard.service',\n         'pulse': 'com.lifeos.pulse.service'}"
        self.assertIn(original,text);path.write_text(text.replace(original,'UNITS = '+repr(self.fixture.service.fixture.units)))
        self.fixture.policy.plan['bridge_files']['profile_services.py']=hashlib.sha256(path.read_bytes()).hexdigest()
        encoded=json.dumps(self.fixture.policy.plan,sort_keys=True,separators=(',',':')).encode()
        self.signature=hashlib.sha256(encoded).hexdigest();publish(self.stage/'plan.json',encoded)
        publish(self.stage/'operation.json',json.dumps({'signature':self.signature,'state':'ready'}).encode())
        publish(self.stage/'services.json',self.fixture.controller.journal.read_bytes())
        self.active=self.profile/'plugins/lifeos-hook-bridge';self.active.parent.mkdir(mode=0o700,exist_ok=True)
        shutil.copytree(self.stage/'recovery-bridge',self.active)
        request={'version':1,'identifier':self.job.name,'profile':str(self.profile),'owner':'dashboard:owner',
            'bridge':fingerprint(self.active),'selection':{'kind':'removal','identifier':'c'*32,'signature':'d'*64,'disable_discord':True}}
        publish(self.job/'request.json',json.dumps(request).encode())
        publish(self.job/'status.json',json.dumps({'identifier':self.job.name,'state':'ready'}).encode())
        publish(self.job/'review.json',json.dumps({'state':'ready','signature':self.signature}).encode())
        (self.profile/'.lifeos-removal.json').unlink()

    def select(self):
        publish(self.profile/'.lifeos-removal.json',json.dumps({'format':1,'workflow':self.job.name,'signature':self.signature}).encode())

    def test_active_source_lease_cannot_cross_into_retained_publication(self):
        source,_=memory_workflow._source(self.profile)
        with source.memory_module('installation_lock').installation_lock(self.profile) as lease:
            self.select()
            operation=RemovalPublication(self.profile,self.signature,installation_lease=lease)
            with self.assertRaisesRegex(RuntimeError,'issued owner lease'):
                operation.apply(account='dashboard:owner')
        self.assertEqual(json.loads((self.stage/'operation.json').read_bytes())['state'],'ready')
        self.assertTrue(self.fixture.program.exists())

    def test_reviewed_first_apply_issues_retained_lease_and_publishes_with_real_services(self):
        source,configuration=memory_workflow._source(self.profile,workflow=self.job.name)
        self.assertEqual(Path(source.__file__).parent,self.stage/'recovery-bridge')
        configuration.check_owner(configuration.load(),'dashboard:owner')
        with source.memory_module('installation_lock').installation_lock(self.profile) as lease:
            self.select()
            result=RemovalPublication(self.profile,self.signature,installation_lease=lease).apply(account='dashboard:owner')
        self.assertEqual(result['state'],'verification_required')
        self.assertFalse(self.fixture.program.exists());self.assertFalse(self.fixture.policy.configuration.path.exists())
        self.assertEqual((self.profile/'memories/MEMORY.md').read_bytes(),self.fixture.original_memory)
        self.assertEqual(self.fixture.service.fixture.properties('pulse')['MainPID'],'0')
        self.assertEqual(self.fixture.service.fixture.properties('dashboard')['ActiveState'],'active')

    def test_uncompleted_review_keeps_active_source_for_preparation_cancellation(self):
        publish(self.job/'review.json',b'{"state":"preparation","signature":"synthetic-unapplied"}')
        source,_=memory_workflow._source(self.profile,workflow=self.job.name)
        self.assertEqual(Path(source.__file__).parent,self.active)
        self.assertFalse((self.profile/'.lifeos-removal.json').exists())

    def test_changed_retained_source_and_wrong_signature_refuse_before_a_lease(self):
        path=self.stage/'recovery-bridge/profile_services.py';before=path.read_bytes();path.write_bytes(before+b'\n# Synthetic later edit\n')
        with self.assertRaises(ValueError):memory_workflow._source(self.profile,workflow=self.job.name)
        path.write_bytes(before)
        publish(self.job/'review.json',json.dumps({'state':'ready','signature':'f'*64}).encode())
        with self.assertRaises(ValueError):memory_workflow._source(self.profile,workflow=self.job.name)
        self.assertFalse((self.profile/'.lifeos-removal.json').exists())

    def test_live_owner_revocation_still_overrides_retained_policy(self):
        self.fixture.policy.configuration.update(lambda value:value['accounts'].pop('dashboard:owner'))
        _,configuration=memory_workflow._source(self.profile,workflow=self.job.name)
        with self.assertRaises(PermissionError):configuration.check_owner(configuration.load(),'dashboard:owner')

    def test_unknown_workflow_cannot_select_reviewed_retained_sources(self):
        with self.assertRaises(ValueError):memory_workflow._source(self.profile,workflow='b'*32)
        self.assertFalse((self.profile/'.lifeos-removal.json').exists())
