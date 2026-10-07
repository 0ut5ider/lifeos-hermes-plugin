# ABOUTME: Checks current admitted source-health metadata and selected original-native equality.
# ABOUTME: Uses real HTTP listeners to verify edits, retirement, failed credentials, and backend loss.
import json
import os
from pathlib import Path
import subprocess
import unittest

import httpx
import test_memory_freshness_health as health_fixture
from test_memory_native import OWNER


class MemoryFreshnessHealthCurrentTests(unittest.TestCase):
    def setUp(self):
        self.fixture = health_fixture.MemoryFreshnessHealthTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.relay = self.fixture.fixture
        self.native = self.fixture.native
        self.root = self.fixture.root
        self.route = self.fixture.route

    def client(self):
        client = httpx.Client(timeout=30)
        self.addCleanup(client.close)
        self.relay.login(client)
        return client

    def test_later_source_edit_changes_counts_on_the_next_health_request(self):
        client = self.client()
        previous = client.get(self.native+self.route).json()
        self.relay.telos.write_text(self.relay.telos.read_text()+'\n## Goals\nSynthetic later HTTP goal.\n')
        current = client.get(self.native+self.route)
        self.assertEqual(current.status_code, 200, current.text)
        self.assertEqual(current.json()['details']['telos_sections_total'], previous['details']['telos_sections_total']+1)
        self.assertNotIn('Synthetic later HTTP goal', current.text)

    def test_retired_source_cannot_retain_previous_health_counts(self):
        client = self.client()
        self.assertGreater(client.get(self.native+self.route).json()['details']['telos_sections_total'], 0)
        saved = self.relay.memory.remember(OWNER, category='principal',
            content='RULE: Synthetic HTTP freshness mission', title='', project='', request_id='source-health-retirement')
        self.relay.memory.forget(OWNER,saved['reference'],'source-health-forget')
        response=client.get(self.native+self.route)
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(response.json()['details']['telos_sections_total'],0)
        self.assertEqual(response.json()['status'],'degraded')

    def test_invalid_bearer_cannot_borrow_valid_owner_health_cookies(self):
        client=self.client()
        response=client.get(self.native+self.route,headers={'Authorization':'Bearer invalid-synthetic'})
        self.assertEqual(response.status_code,401,response.text)
        self.assertNotIn('telos_sections_total',response.text)

    def test_missing_connector_refuses_without_reusing_health(self):
        client=self.client()
        self.assertEqual(client.get(self.native+self.route).status_code,200)
        (self.root/'LIFEOS/USER/CONFIG/memory-access.json').unlink()
        response=client.get(self.native+self.route)
        self.assertEqual(response.status_code,503,response.text)
        self.assertNotIn('telos_sections_total',response.text)

    def test_backend_loss_refuses_without_reusing_health(self):
        client=self.client()
        self.assertEqual(client.get(self.native+self.route).status_code,200)
        self.relay.server.should_exit=True
        self.relay.thread.join(timeout=10)
        response=client.get(self.native+self.route)
        self.assertEqual(response.status_code,503,response.text)
        self.assertNotIn('telos_sections_total',response.text)

    def test_original_native_health_matches_selected_current_source_metadata(self):
        client=self.client()
        response=client.get(self.native+self.route)
        self.assertEqual(response.status_code,200,response.text)
        current=response.json()
        original=Path(os.environ['LIFEOS_FRESHNESS_CONTROL_SOURCE'])/'LIFEOS/PULSE/modules/telos.ts'
        program='import {start,health} from '+json.dumps(str(original))+';await start();console.log("SYNTHETIC_HEALTH="+JSON.stringify(health()));'
        result=subprocess.run(['bun','--no-install','-e',program],env=self.relay.environment,
            capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(result.stderr,'')
        standalone=json.loads(next(line for line in result.stdout.splitlines() if line.startswith('SYNTHETIC_HEALTH=')).split('=',1)[1])
        self.assertEqual(current['status'],standalone['status'])
        for field in ('telos_file_updated','telos_file_age_days','telos_sections_total','telos_sections_stale',
                      'context_files_total','context_files_stale'):
            with self.subTest(field=field):
                self.assertEqual(current['details'][field],standalone['details'][field])
