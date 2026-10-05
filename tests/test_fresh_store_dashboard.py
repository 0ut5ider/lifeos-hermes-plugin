# ABOUTME: Verifies named-store preparation through actual Hermes password authentication.
# ABOUTME: Refuses request path overrides and preserves existing data during native preparation.
import importlib.util
import json
import os
from pathlib import Path
import shutil
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from test_memory_dashboard import owner_client
import test_memory_import as import_fixture


@unittest.skipUnless(os.environ.get('LIFEOS_FRESH_SOURCE') and shutil.which('bun'),
                     'The complete native candidate and Bun are required')
class FreshStoreDashboardTests(unittest.TestCase):
    def test_verified_owner_prepares_fixed_source_and_preserves_current_profile(self):
        fixture=import_fixture.MemoryImportTests();fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        originals={path:path.read_bytes() for path in (fixture.profile/'config.yaml',
            fixture.sources/'MEMORY.md')}
        self.assertFalse((fixture.sources/'USER.md').exists())
        path=Path(__file__).parents[1]/'lifeos_hook_bridge/dashboard/plugin_api.py'
        with patch.dict(os.environ,{'HOME':str(fixture.fixture.home),'HERMES_HOME':str(fixture.profile)}):
            spec=importlib.util.spec_from_file_location('fresh_store_dashboard_http',path)
            api=importlib.util.module_from_spec(spec);spec.loader.exec_module(api)
            api.INSTALL_CANDIDATE=Path(os.environ['LIFEOS_FRESH_SOURCE'])
            app=FastAPI();app.include_router(api.router,prefix='/api/plugins/lifeos-hook-bridge')
            api.install_memory_cache_headers(app)
            endpoint='/api/plugins/lifeos-hook-bridge/memory/fresh/prepare'
            body={'principal_name':'Adrian','assistant_name':'Cerebo'}
            with owner_client(app,fixture.profile) as client:
                with TestClient(app) as guest:
                    response=guest.post(endpoint,json=body)
                    self.assertEqual(response.status_code,401,response.text)
                    self.assertNotIn('principal',response.text)
                for key in ('candidate','destination','profile','root','account'):
                    response=client.post(endpoint,json=body|{key:'/other'})
                    self.assertEqual(response.status_code,400,response.text)
                    self.assertEqual(response.headers['cache-control'],'no-store')
                self.assertEqual(client.post(endpoint,json=body,headers={'Origin':'https://other.invalid'}).status_code,403)
                api.INSTALL_CANDIDATE=Path('/missing-synthetic-lifeos-candidate')
                response=client.post(endpoint,json=body)
                self.assertEqual(response.status_code,409,response.text)
                self.assertNotIn('/missing-synthetic',response.text)
                api.INSTALL_CANDIDATE=Path(os.environ['LIFEOS_FRESH_SOURCE'])
                response=client.post(endpoint,json=body)
                self.assertEqual(response.status_code,200,response.text)
                self.assertEqual(response.headers['cache-control'],'no-store')
                result=response.json()
                self.assertEqual(result['names'],{'principal':'Adrian','assistant':'Cerebo'})
                self.assertEqual(result['state'],'review')
                self.assertEqual(result['active_facts'],0)
                self.assertFalse(result['activation_ready'])
                self.assertFalse(fixture.configuration.load()['ownership_enabled'])
                self.assertEqual(fixture.configuration.load()['root'],str(fixture.fixture.root))
                for target,data in originals.items():self.assertEqual(target.read_bytes(),data)
                self.assertFalse((fixture.sources/'USER.md').exists())
                fixture.configuration.update(lambda value:value['accounts'].pop('dashboard:basic:synthetic-owner'))
                response=client.post(endpoint,json=body)
                self.assertEqual(response.status_code,403,response.text)
                self.assertEqual(response.headers['cache-control'],'no-store')
                evidence=os.environ.get('LIFEOS_FRESH_HTTP_EVIDENCE')
                if evidence:
                    output=Path(evidence);output.mkdir(parents=True,exist_ok=True)
                    (output/'authenticated-fresh-review.json').write_text(json.dumps(result,indent=2)+'\n')
