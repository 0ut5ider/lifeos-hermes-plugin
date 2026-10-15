# ABOUTME: Exercises reverse export through authenticated owner HTTP requests and actual native facts.
# ABOUTME: Checks download integrity, no-store responses, profile binding, and revoked access.
import importlib.util
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from test_memory_dashboard import owner_client
import test_memory_export as fixture


class MemoryExportDashboardTests(unittest.TestCase):
    def test_owner_reviews_exports_and_downloads_portable_memory_without_a_provider_switch(self):
        data=fixture.MemoryExportTests();data.setUp();self.addCleanup(data.doCleanups)
        path=Path(__file__).parents[1]/'lifeos_hook_bridge/dashboard/plugin_api.py'
        with patch.dict(os.environ,{'HOME':str(data.fixture.fixture.home),'HERMES_HOME':str(data.profile)}):
            spec=importlib.util.spec_from_file_location('memory_export_http',path)
            api=importlib.util.module_from_spec(spec);spec.loader.exec_module(api)
            app=FastAPI();app.include_router(api.router,prefix='/api/plugins/lifeos-hook-bridge')
            api.install_memory_cache_headers(app)
            with owner_client(app,data.profile) as client:
                endpoint='/api/plugins/lifeos-hook-bridge/memory/export'
                response=client.post(endpoint+'/preview',json={})
                self.assertEqual(response.status_code,200,response.text)
                review=response.json()
                response=client.post(endpoint+'/snapshot',json={'signature':review['signature']})
                self.assertEqual(response.status_code,200,response.text)
                saved=response.json();binding={'identifier':saved['identifier'],'signature':saved['signature']}
                response=client.post(endpoint+'/plan',json={**binding,'decisions':data.decisions(review)})
                self.assertEqual(response.status_code,200,response.text)
                plan=response.json()
                response=client.post(endpoint+'/apply',json={**binding,'plan_signature':plan['signature']})
                self.assertEqual(response.status_code,200,response.text)
                self.assertEqual(response.json()['state'],'exported')
                response=client.post(endpoint+'/download',json=binding)
                self.assertEqual(response.status_code,200,response.text)
                self.assertEqual(response.json()['format'],'lifeos-portable-memory')
                self.assertEqual(response.headers['cache-control'],'no-store')
                self.assertIn('attachment',response.headers['content-disposition'])
                self.assertFalse(data.configuration.load()['ownership_enabled'])
                data.configuration.update(lambda value:value['accounts'].pop('dashboard:basic:synthetic-owner'))
                self.assertEqual(client.post(endpoint+'/download',json=binding).status_code,403)
