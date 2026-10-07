# ABOUTME: Verifies the owner listing of prepared fresh stores and their preparation state.
# ABOUTME: Separates reviewed, running, interrupted, and altered preparations without native installation.
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from lifeos_hook_bridge.installation_lock import installation_lock
from lifeos_hook_bridge.memory_access import MemoryUnavailable
import test_memory_import as import_fixture


class FreshStoreStatusTests(unittest.TestCase):
    def setUp(self):
        self.fixture=import_fixture.MemoryImportTests();self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.profile=self.fixture.profile
        os.chmod(self.profile,0o700)
        identity=hashlib.sha256(str(self.profile).encode()).hexdigest()[:24]
        self.base=self.profile.parent/'.local/state/lifeos-hook-bridge/fresh-stores'/identity

    def operation(self):
        from lifeos_hook_bridge.fresh_store import FreshStore
        return FreshStore(self.fixture.configuration)

    def store(self,identifier,state,*,names=('Adrian','Cerebo'),profile=None,modified=None):
        folder=self.base/identifier
        folder.mkdir(parents=True,mode=0o700)
        for parent in (self.base,self.base.parent,self.base.parent.parent):os.chmod(parent,0o700)
        document={'version':1,'state':state,'profile':str(profile or self.profile),
            'retained_installation':str(self.fixture.fixture.root),
            'source':{'lifeos_commit':'synthetic-revision'},
            'names':{'principal':names[0],'assistant':names[1]},'ownership_enabled':False,
            'sharing_enabled':False,'services_started':False}
        if state=='review':
            document.update(installed=str(folder/'home/.claude'),data=str(folder/'home/.config/LIFEOS/USER'),
                active_facts=0,activation_ready=False,return_installation=str(self.fixture.fixture.root))
            document['signature']=hashlib.sha256((json.dumps(document,sort_keys=True,indent=2)+'\n').encode()).hexdigest()
        path=folder/'review.json'
        path.write_text(json.dumps(document,sort_keys=True,indent=2)+'\n')
        os.chmod(path,0o600)
        if modified:os.utime(path,(modified,modified))
        return path

    def status(self):
        return self.operation().status(account='dashboard:owner')

    def test_profile_without_preparations_reports_an_empty_idle_listing(self):
        self.assertEqual(self.status(),{'busy':False,'stores':[]})

    def test_signed_review_reports_names_and_inactive_selection(self):
        self.store('a'*32,'review')
        self.assertEqual(self.status(),{'busy':False,'stores':[{
            'identifier':'a'*32,'state':'review','names':{'principal':'Adrian','assistant':'Cerebo'},
            'active_facts':0,'activation_ready':False,'source':{'lifeos_commit':'synthetic-revision'},
            'retained_installation':str(self.fixture.fixture.root)}]})

    def test_altered_review_is_reported_without_its_unverified_content(self):
        path=self.store('b'*32,'review')
        path.write_text(path.read_text().replace('Adrian','Other'))
        self.store('c'*32,'review',profile=self.profile.parent/'other-profile')
        self.assertEqual(self.status()['stores'],[{'identifier':'c'*32,'state':'invalid'},
                                                  {'identifier':'b'*32,'state':'invalid'}])

    def test_unfinished_preparation_is_interrupted_when_no_installation_operation_runs(self):
        self.store('d'*32,'preparing')
        self.assertEqual(self.status(),{'busy':False,'stores':[{
            'identifier':'d'*32,'state':'interrupted','names':{'principal':'Adrian','assistant':'Cerebo'}}]})

    def test_unfinished_preparation_is_running_while_the_installation_lock_is_held(self):
        self.store('e'*32,'preparing')
        self.store('f'*32,'review')
        with installation_lock(self.profile):
            result=self.status()
        self.assertTrue(result['busy'])
        self.assertEqual({row['identifier']:row['state'] for row in result['stores']},
                         {'e'*32:'preparing','f'*32:'review'})

    def test_listing_orders_the_latest_preparation_first(self):
        self.store('1'*32,'review',modified=1_000_000)
        self.store('2'*32,'review',modified=3_000_000)
        self.store('3'*32,'preparing',modified=2_000_000)
        self.assertEqual([row['identifier'][0] for row in self.status()['stores']],['2','3','1'])

    def test_listing_requires_the_installation_owner(self):
        self.store('a'*32,'review')
        with self.assertRaises(PermissionError):
            self.operation().status(account='dashboard:guest')
        with self.assertRaises(PermissionError):
            self.operation().status(account=None)

    def test_listing_refuses_a_linked_store_and_preserves_every_file(self):
        path=self.store('a'*32,'review')
        original=path.read_bytes()
        (self.base/('9'*32)).symlink_to(self.base/('a'*32),target_is_directory=True)
        with self.assertRaises(MemoryUnavailable):
            self.status()
        self.assertEqual(path.read_bytes(),original)


class FreshStoreStatusRouteTests(unittest.TestCase):
    def test_owner_reads_the_listing_and_other_requests_are_refused(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from test_memory_dashboard import owner_client
        fixture=FreshStoreStatusTests();fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        fixture.store('a'*32,'review')
        path=Path(__file__).parents[1]/'lifeos_hook_bridge/dashboard/plugin_api.py'
        with patch.dict(os.environ,{'HOME':str(fixture.fixture.fixture.home),'HERMES_HOME':str(fixture.profile)}):
            spec=importlib.util.spec_from_file_location('fresh_store_status_http',path)
            api=importlib.util.module_from_spec(spec);spec.loader.exec_module(api)
            app=FastAPI();app.include_router(api.router,prefix='/api/plugins/lifeos-hook-bridge')
            api.install_memory_cache_headers(app)
            endpoint='/api/plugins/lifeos-hook-bridge/memory/fresh/status'
            with owner_client(app,fixture.profile) as client:
                with TestClient(app) as guest:
                    response=guest.get(endpoint)
                    self.assertEqual(response.status_code,401,response.text)
                    self.assertNotIn('Adrian',response.text)
                response=client.get(endpoint)
                self.assertEqual(response.status_code,200,response.text)
                self.assertEqual(response.headers['cache-control'],'no-store')
                self.assertEqual([(row['identifier'],row['state']) for row in response.json()['stores']],[('a'*32,'review')])
                response=client.get(endpoint,params={'profile':'/other'})
                self.assertEqual(response.status_code,400,response.text)
                self.assertEqual(response.headers['cache-control'],'no-store')
                fixture.fixture.configuration.update(lambda value:value['accounts'].pop('dashboard:basic:synthetic-owner'))
                response=client.get(endpoint)
                self.assertEqual(response.status_code,403,response.text)
                self.assertNotIn('Adrian',response.text)
