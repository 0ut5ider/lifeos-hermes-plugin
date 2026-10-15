# ABOUTME: Verifies import review through actual Hermes password sessions and native operations.
# ABOUTME: Refuses profile overrides and revoked owners without publishing facts or changing ownership.
import importlib.util
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from test_memory_dashboard import owner_client
from test_memory_import import MemoryImportTests


class MemoryImportDashboardTests(unittest.TestCase):
    def test_owner_uploads_original_source_bytes_without_replacing_profile_memory(self):
        import base64
        fixture=MemoryImportTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
        path=Path(__file__).parents[1]/'lifeos_hook_bridge/dashboard/plugin_api.py'
        with patch.dict(os.environ,{'HOME':str(fixture.fixture.home),'HERMES_HOME':str(fixture.profile)}):
            spec=importlib.util.spec_from_file_location('memory_import_upload_http',path)
            api=importlib.util.module_from_spec(spec);spec.loader.exec_module(api)
            app=FastAPI();app.include_router(api.router,prefix='/api/plugins/lifeos-hook-bridge')
            api.install_memory_cache_headers(app)
            with owner_client(app,fixture.profile) as client:
                endpoint='/api/plugins/lifeos-hook-bridge/memory/import'
                raw=b'\xef\xbb\xbf Synthetic external HTTP fact.\r\n'
                response=client.post(endpoint+'/upload',json={'label':'Synthetic external Hermes',
                    'files':{'MEMORY.md':base64.b64encode(raw).decode()}})
                self.assertEqual(response.status_code,200,response.text)
                source=response.json()
                response=client.post(endpoint+'/preview',json={'source_identifier':source['identifier']})
                self.assertEqual(response.status_code,200,response.text)
                review=response.json()
                response=client.post(endpoint+'/snapshot',json={'signature':review['signature'],'source_identifier':source['identifier']})
                self.assertEqual(response.status_code,200,response.text)
                saved=response.json()
                self.assertEqual((Path(saved['snapshot'])/'sources/MEMORY.md').read_bytes(),raw)
                request={'identifier':saved['identifier'],'snapshot_signature':saved['snapshot_signature']}
                response=client.post(endpoint+'/status',json=request)
                self.assertEqual(response.status_code,200,response.text)
                self.assertEqual(response.json()['review']['source_origin']['label'],'Synthetic external Hermes')
                self.assertEqual((fixture.sources/'MEMORY.md').read_bytes(),fixture.raw)

    def test_owner_plans_applies_and_inspects_import_without_path_overrides(self):
        fixture=MemoryImportTests();fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        (fixture.sources/'MEMORY.md').write_text('Synthetic HTTP import marker.')
        path=Path(__file__).parents[1]/'lifeos_hook_bridge/dashboard/plugin_api.py'
        with patch.dict(os.environ,{'HOME':str(fixture.fixture.home),'HERMES_HOME':str(fixture.profile)}):
            spec=importlib.util.spec_from_file_location('memory_import_apply_http',path)
            api=importlib.util.module_from_spec(spec);spec.loader.exec_module(api)
            app=FastAPI();app.include_router(api.router,prefix='/api/plugins/lifeos-hook-bridge')
            api.install_memory_cache_headers(app)
            with owner_client(app,fixture.profile) as client:
                endpoint='/api/plugins/lifeos-hook-bridge/memory/import'
                review=client.post(endpoint+'/preview',json={}).json()
                snapshot=client.post(endpoint+'/snapshot',json={'signature':review['signature']}).json()
                self.assertIn('identifier',snapshot)
                chunk=review['sources'][0]['chunks'][0]
                request={'identifier':snapshot['identifier'],'snapshot_signature':snapshot['snapshot_signature']}
                decision={'id':chunk['id'],'action':'import','required':True,'category':'project',
                    'project':'lab','content':chunk['content'],'title':'Synthetic HTTP import'}
                response=client.post(endpoint+'/plan',json={**request,'decisions':[decision]})
                self.assertEqual(response.status_code,200,response.text)
                plan=response.json()
                response=client.post(endpoint+'/apply',json={**request,'plan_signature':plan['signature']})
                self.assertEqual(response.status_code,200,response.text)
                self.assertEqual(response.json()['state'],'published',response.text)
                self.assertEqual(response.headers['cache-control'],'no-store')
                response=client.post(endpoint+'/status',json=request)
                self.assertEqual(response.status_code,200,response.text)
                self.assertEqual(response.json()['publication']['state'],'published')
                self.assertEqual(response.json()['plan']['signature'],plan['signature'])
                for suffix,body in (('/status',{**request,'identifier':'../other'}),
                        ('/apply',{**request,'plan_signature':plan['signature'],'snapshot':'/other'}),
                        ('/plan',{**request,'decisions':[decision],'account':'dashboard:owner'})):
                    self.assertEqual(client.post(endpoint+suffix,json=body).status_code,400)
                fixture.configuration.update(lambda value:value['accounts'].pop('dashboard:basic:synthetic-owner'))
                self.assertEqual(client.post(endpoint+'/status',json=request).status_code,403)

    def test_verified_owner_reviews_and_captures_private_source_snapshot(self):
        fixture=MemoryImportTests();fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        path=Path(__file__).parents[1]/'lifeos_hook_bridge/dashboard/plugin_api.py'
        with patch.dict(os.environ,{'HOME':str(fixture.fixture.home),'HERMES_HOME':str(fixture.profile)}):
            spec=importlib.util.spec_from_file_location('memory_import_dashboard_http',path)
            api=importlib.util.module_from_spec(spec);spec.loader.exec_module(api)
            app=FastAPI();app.include_router(api.router,prefix='/api/plugins/lifeos-hook-bridge')
            api.install_memory_cache_headers(app)
            with owner_client(app,fixture.profile) as client:
                endpoint='/api/plugins/lifeos-hook-bridge/memory/import'
                response=client.post(endpoint+'/preview',json={})
                self.assertEqual(response.status_code,200,response.text)
                self.assertEqual(response.headers['cache-control'],'no-store')
                review=response.json()
                self.assertEqual(review['sources'][0]['chunks'][0]['content'],'synthetic A')
                response=client.post(endpoint+'/snapshot',json={'signature':review['signature']})
                self.assertEqual(response.status_code,200,response.text)
                saved=response.json()
                snapshot=Path(saved['snapshot'])
                self.assertEqual((snapshot/'sources/MEMORY.md').read_bytes(),fixture.raw)
                self.assertFalse(fixture.configuration.load()['ownership_enabled'])
                self.assertEqual((fixture.sources/'MEMORY.md').read_bytes(),fixture.raw)
                for body in ({'profile':'/other'},{'account':'dashboard:owner'},{'root':'/other'}):
                    self.assertEqual(client.post(endpoint+'/preview',json=body).status_code,400)
                self.assertEqual(client.post(endpoint+'/snapshot',json={'signature':review['signature'],'destination':'/other'}).status_code,400)
                self.assertEqual(client.post(endpoint+'/preview',json={},headers={'Origin':'https://other.invalid'}).status_code,403)
                fixture.configuration.update(lambda value:value['accounts'].pop('dashboard:basic:synthetic-owner'))
                response=client.post(endpoint+'/preview',json={})
                self.assertEqual(response.status_code,403,response.text)
                self.assertEqual(response.headers['cache-control'],'no-store')
