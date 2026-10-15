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
