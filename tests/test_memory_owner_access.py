# ABOUTME: Verifies route-bound local owner access after a fresh dashboard claim and reviewed activation.
# ABOUTME: Keeps other accounts and model routes denied while preserving existing destination grants.
import json
import os
import unittest

from lifeos_hook_bridge.memory_context import host_context,route_identity
from lifeos_hook_bridge.memory_policy import MemoryPolicy,CATEGORIES
from lifeos_hook_bridge.memory_access import MemoryUnavailable
from lifeos_hook_bridge.profile_backup import create
import test_memory_ownership as fixture_module


class MemoryOwnerAccessTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixture_module.MemoryOwnershipTests();self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        self.configuration=self.fixture.configuration;self.profile=self.fixture.profile
        self.configuration.update(lambda value:value.update(accounts={'dashboard:owner':'owner'},destinations={}))
        self.model={'default':'synthetic-model','provider':'custom','base_url':'http://127.0.0.1:9/v1','api_key':'synthetic-key'}
        self.path=self.profile/'config.yaml'
        self.path.write_text(json.dumps({'memory':{'memory_enabled':True,'user_profile_enabled':True},'model':self.model}))
        self.route=route_identity('custom','synthetic-model','http://127.0.0.1:9/v1','chat_completions')

    def review(self):
        destination=self.fixture.fixture.fixture.fixture.home/'local-owner-backup'
        self.fixture.backup=create(self.configuration,destination,account='dashboard:owner')
        return self.fixture.preview()

    def scope(self,*,route=None,author=None):
        selected=self.configuration.load()
        context=host_context(selected,{'HERMES_SESSION_PLATFORM':'cli'},
            model_route=route or self.route,hermes_home=str(self.profile))
        if author is not None:
            from dataclasses import replace
            context=replace(context,author=author)
        return MemoryPolicy(selected).resolve(context)

    def test_review_discloses_and_apply_admits_only_current_local_owner_route(self):
        before=self.configuration.path.read_bytes();review=self.review()
        self.assertEqual(self.configuration.path.read_bytes(),before)
        self.assertEqual(review['local_owner_access'],{'account':'terminal:'+str(os.getuid()),
            'destination':'terminal:'+str(self.profile),'model':'synthetic-model','provider':'custom','model_route':self.route})
        self.fixture.apply(review)
        scope=self.scope();self.assertEqual(scope.reason,'');self.assertEqual(set(scope.read),CATEGORIES)
        self.assertTrue(self.scope(author='unknown').reason)
        self.assertTrue(self.scope(route=route_identity('custom','synthetic-model','https://example.invalid/v1','chat_completions')).reason)

    def test_conflicting_local_identity_is_not_replaced(self):
        self.configuration.update(lambda value:value['accounts'].update({'terminal:'+str(os.getuid()):'another-owner'}))
        before=self.configuration.path.read_bytes()
        with self.assertRaises(MemoryUnavailable):self.review()
        self.assertEqual(self.configuration.path.read_bytes(),before)

    def test_restricted_local_grant_is_not_expanded(self):
        self.configuration.update(lambda value:value['destinations'].update({'terminal:'+str(self.profile):{
            'visibility':'private','participants':['owner'],'read':['project'],'write':[],
            'projects':['lab'],'model_routes':[self.route]}}))
        before=self.configuration.path.read_bytes()
        with self.assertRaises(MemoryUnavailable):self.review()
        self.assertEqual(self.configuration.path.read_bytes(),before)

    def test_model_route_change_invalidates_review_without_owner_publication(self):
        reviewed=self.review();before=self.configuration.path.read_bytes()
        current=json.loads(self.path.read_bytes());current['model']['base_url']='http://127.0.0.1:10/v1'
        self.path.write_text(json.dumps(current))
        with self.assertRaises(MemoryUnavailable):self.fixture.apply(reviewed)
        self.assertEqual(self.configuration.path.read_bytes(),before)

    def test_existing_other_grants_and_local_permissions_are_preserved(self):
        old_route=route_identity('custom','synthetic-previous-model','http://127.0.0.1:9/v1','chat_completions')
        grant={'visibility':'private','participants':['owner'],'read':sorted(CATEGORIES),
            'write':sorted(CATEGORIES),'projects':['*'],'model_routes':[old_route],'proposals':['review']}
        foreign={'visibility':'private','participants':['foreign'],'read':['project'],'write':[],
            'projects':['foreign-project'],'model_routes':['foreign-route']}
        self.configuration.update(lambda value:value.update(accounts={**value['accounts'],'terminal:'+str(os.getuid()):'owner',
            'other:account':'foreign'},destinations={'terminal:'+str(self.profile):grant,'other:destination':foreign}))
        self.fixture.apply(self.review());current=self.configuration.load()
        self.assertEqual(current['accounts']['other:account'],'foreign')
        self.assertEqual(current['destinations']['other:destination'],foreign)
        local=current['destinations']['terminal:'+str(self.profile)]
        self.assertEqual(local['proposals'],['review']);self.assertEqual(set(local['model_routes']),{old_route,self.route})

    def test_unknown_endpoint_refuses_before_provider_publication(self):
        self.model['base_url']='file:///synthetic/not-a-model-endpoint'
        self.path.write_text(json.dumps({'model':self.model}))
        before=self.configuration.path.read_bytes()
        with self.assertRaises(MemoryUnavailable):self.review()
        self.assertEqual(self.configuration.path.read_bytes(),before)
