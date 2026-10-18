# ABOUTME: Tests authenticated portability management through actual native sessions and HTTP requests.
# ABOUTME: Refuses client-selected filesystem paths and grants no authority to another dashboard account.
import json
import unittest

import test_release_dashboard as fixture


class PortabilityDashboardTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixture.ReleaseDashboardTests();self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def test_status_requires_current_installation_owner(self):
        self.assertEqual(self.fixture.request(path='/memory-workflows')[0],401)
        self.assertEqual(self.fixture.request(self.fixture.other,path='/memory-workflows')[0],403)
        self.assertEqual(self.fixture.request(self.fixture.owner,path='/memory-workflows'),(200,{'operations':[]}))

    def test_status_before_the_claim_names_the_claim(self):
        (self.fixture.profile/'lifeos-memory.json').unlink()
        code,result=self.fixture.request(self.fixture.owner,path='/memory-workflows')
        self.assertEqual(code,409)
        self.assertIn('Claim this LifeOS installation on the LifeOS Bridge page',result['detail'])

    def test_preparation_refuses_paths_accounts_and_foreign_origin(self):
        for selection in ({'kind':'return','snapshot':'/tmp/private'},
                          {'kind':'activation','account':'dashboard:basic:owner'},
                          {'kind':'remove','command':'true'},
                          {'kind':'return','identifier':'../escape'},
                          {'kind':['return']},[]):
            with self.subTest(selection=selection):
                self.assertEqual(self.fixture.request(self.fixture.owner,path='/memory-workflows',method='POST',
                    body=json.dumps(selection).encode(),origin=self.fixture.origin)[0],400)
        self.assertEqual(self.fixture.request(self.fixture.owner,path='/memory-workflows',method='POST',
            body=b'{}',origin='https://other.invalid')[0],403)
        self.assertFalse((self.fixture.profile/'.lifeos-portability').exists())

    def test_actions_require_server_identifier_and_reviewed_signature(self):
        for action in ('apply','recover','rollback'):
            for identifier in ('bad','a'*32):
                self.assertEqual(self.fixture.request(self.fixture.owner,
                    path='/memory-workflows/'+identifier+'/'+action,method='POST',
                    body=b'{"signature":"forged","account":"owner"}',origin=self.fixture.origin)[0],400)

    def test_retained_removal_owner_still_controls_http_after_active_policy_disappears(self):
        import hashlib
        import os
        import test_removal_state as removal_fixture
        from optional.lifeos_release_manager.release_programs import publish,fingerprint
        state=removal_fixture.RemovalStateTests();state.setUp();self.addCleanup(state.doCleanups)
        policy=json.loads(state.policy);policy['accounts']={'dashboard:basic:owner':'owner'}
        encoded=json.dumps(policy,sort_keys=True,separators=(',',':')).encode();publish(state.stage/'owner-policy.json',encoded)
        state.plan.update(owner='dashboard:basic:owner',owner_policy_sha256=hashlib.sha256(encoded).hexdigest())
        encoded=json.dumps(state.plan,sort_keys=True,separators=(',',':')).encode();signature=hashlib.sha256(encoded).hexdigest()
        publish(state.stage/'plan.json',encoded);publish(state.profile/'.lifeos-removal.json',json.dumps({
            'format':1,'workflow':state.job.name,'signature':signature}).encode())
        state.configuration.path.unlink()
        publish(state.job/'request.json',json.dumps({'version':1,'identifier':state.job.name,'profile':str(state.profile),
            'owner':'dashboard:basic:owner','bridge':fingerprint(state.stage/'recovery-bridge'),
            'selection':{'kind':'removal','identifier':'b'*32,'signature':'c'*64,'disable_discord':True}}).encode())
        publish(state.job/'status.json',json.dumps({'identifier':state.job.name,'state':'interrupted'}).encode())
        publish(state.job/'review.json',json.dumps({'state':'ready','signature':signature}).encode())
        os.environ['HERMES_HOME']=str(state.profile)
        self.assertEqual(self.fixture.request(path='/memory-workflows')[0],401)
        self.assertEqual(self.fixture.request(self.fixture.other,path='/memory-workflows')[0],403)
        code,result=self.fixture.request(self.fixture.owner,path='/memory-workflows')
        self.assertEqual(code,200,result);self.assertEqual(result['operations'][0]['kind'],'removal')
        self.assertFalse(state.configuration.path.exists())
