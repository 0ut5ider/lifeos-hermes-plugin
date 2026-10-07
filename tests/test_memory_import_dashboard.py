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
