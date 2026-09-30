# ABOUTME: Exercises memory preferences through actual FastAPI requests and native records.
# ABOUTME: Verifies strict owner actions and sharing controls in a disposable profile.
import importlib.util
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

HOST = Path(os.environ.get('LIFEOS_HERMES_SOURCE',str(Path.home()/'.cache/lifeos-plugin-memory/source-gate-20260930-native/hermes')))
sys.path.insert(0,str(HOST))
from fastapi import FastAPI
from fastapi.testclient import TestClient
from lifeos_hook_bridge.memory_service import MemoryConfiguration
import test_memory_sharing as sharing_fixture


class MemoryDashboardTests(unittest.TestCase):
    def test_native_proposal_decisions_through_http(self):
        from test_memory_proposals import MemoryProposalTests
        fixture = MemoryProposalTests(); fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        home = fixture.fixture.home
        profile = home / 'hermes'
        MemoryConfiguration(profile/'lifeos-memory.json').save({'version':1,'root':str(fixture.fixture.root),
                                                               'principal':'owner','accounts':{},'destinations':{}})
        api_path = Path(__file__).parents[1]/'lifeos_hook_bridge/dashboard/plugin_api.py'
        with patch.dict(os.environ,{'HOME':str(home),'HERMES_HOME':str(profile)}):
            spec = importlib.util.spec_from_file_location('memory_dashboard_proposal_http',api_path)
            module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
            app = FastAPI(); app.include_router(module.router,prefix='/api/plugins/lifeos-hook-bridge')
            saved = fixture.enqueue()
            with TestClient(app) as client:
                endpoint = '/api/plugins/lifeos-hook-bridge/memory/review'
                response = client.post(endpoint,json={'tool':'lifeos_memory_proposals','arguments':{}})
                self.assertEqual(response.status_code,200,response.text)
                reference = response.json()['results'][0]['reference']
                self.assertEqual(reference,saved['receipt']['proposal_reference'])
                response = client.post(endpoint,json={'tool':'lifeos_memory_decide_proposal','arguments':{
                    'reference':reference,'decision':'edit','request_id':'http-edited',
                    'content':'Always verify the synthetic HTTP edit before publication.'}})
                self.assertEqual(response.status_code,200,response.text)
                self.assertEqual(response.json()['proposal_status'],'edited',response.text)
                self.assertIn('synthetic HTTP edit',fixture.target.read_text())
                response = client.post(endpoint,json={'tool':'lifeos_memory_proposals','arguments':{}})
                self.assertEqual(response.json()['results'],[])

    def test_native_review_and_sharing_through_http(self):
        fixture = sharing_fixture.MemorySharingTests(); fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        home = fixture.fixture.fixture.home
        profile = fixture.fixture.config.parent
        MemoryConfiguration(profile/'lifeos-memory.json').save(fixture.fixture.configuration)
        api_path = Path(__file__).parents[1]/'lifeos_hook_bridge/dashboard/plugin_api.py'
        with patch.dict(os.environ,{'HOME':str(home),'HERMES_HOME':str(profile)}):
            spec = importlib.util.spec_from_file_location('memory_dashboard_http',api_path)
            module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
            app = FastAPI(); app.include_router(module.router,prefix='/api/plugins/lifeos-hook-bridge')
            saved = fixture.fixture.fixture.remember()
            with TestClient(app) as client:
                endpoint = '/api/plugins/lifeos-hook-bridge/memory'
                response = client.get(endpoint)
                self.assertEqual(response.status_code,200,response.text)
                self.assertEqual(response.json()['native_health'],'ok')
                response = client.post(endpoint+'/review',json={'tool':'lifeos_memory_search','arguments':{'query':'synthetic lab'}})
                self.assertEqual(response.status_code,200,response.text)
                self.assertEqual(response.json()['results'][0]['reference'],saved['reference'])
                response = client.post(endpoint+'/review',json={'tool':'lifeos_memory_search','arguments':{'query':'lab'},'caller':'owner'})
                self.assertEqual(response.status_code,400)
                response = client.post(endpoint+'/sharing',json={'enabled':'yes'})
                self.assertEqual(response.status_code,400)
                response = client.post(endpoint+'/connections',json={'client':'httpreader','public_key':sharing_fixture.public_key(62),
                              'projects':['lab'],'model_route':'unknown'})
                self.assertEqual(response.status_code,200,response.text)
                self.assertEqual(response.json()['permissions']['write'],[])
                response = client.delete(endpoint+'/connections/httpreader')
                self.assertEqual(response.status_code,200,response.text)
                self.assertEqual(response.json()['status'],'revoked')
                self.assertEqual(fixture.fixture.fixture.memory.get(__import__('test_memory_native').OWNER,saved['reference'])['status'],'ok')


if __name__ == '__main__':
    unittest.main()
