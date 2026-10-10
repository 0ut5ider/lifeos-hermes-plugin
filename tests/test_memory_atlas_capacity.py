# ABOUTME: Rejects over-capacity native Atlas plans before live publication.
# ABOUTME: Exercises real reconciliation history, capacity reporting, and exact artifact preservation.
from contextlib import closing
import json
import os
import sqlite3
import subprocess
import unittest

import test_memory_atlas_sync as sync_fixture
import test_memory_owner_job_command as command_fixture
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading
from lifeos_hook_bridge.memory_context import route_identity


class MemoryAtlasCapacityTests(unittest.TestCase):
    setUp = sync_fixture.MemoryAtlasSyncTests.setUp
    call = sync_fixture.MemoryAtlasSyncTests.call
    sync = sync_fixture.MemoryAtlasSyncTests.sync
    graph = sync_fixture.MemoryAtlasSyncTests.graph

    def inventory(self, gear, projects):
        (self.root/'LIFEOS/USER/GEAR.md').write_text('## Computing\n'+''.join(
            f'| **Device {index}** | Synthetic Machine 0-{index} | daily |\n' for index in range(gear)))
        (self.root/'LIFEOS/USER/PROJECTS.md').write_text(
            '| Name | Path | URL | Deploy |\n| --- | --- | --- | --- |\n'+''.join(
                f'| Synthetic Project 0-{index} | /synthetic/project-{index} github.com/synthetic/repo-0-{index} '
                f'| app-0-{index}.example.invalid | local |\n' for index in range(projects)))

    def artifact_bytes(self):
        paths = (self.graph(), self.graph().with_name('snapshot.json'), self.cache)
        return {path.name: path.read_bytes() if path.exists() else None for path in paths}

    def seed_runs(self, count):
        module = self.root/'LIFEOS/ATLAS/Store.ts'
        script = ('import {Store} from '+json.dumps(str(module))+';const store=new Store();'
            f'for(let index=0;index<{count};index++)'
            'store.applyRun("gear","full",{complete:false,assets:[],edges:[]});'
            'store.db.exec("PRAGMA wal_checkpoint(TRUNCATE)");'
            'store.db.exec("PRAGMA journal_mode=DELETE");store.close();')
        result = subprocess.run(['bun','--no-install','-e',script], capture_output=True, text=True,
            env=dict(os.environ,HOME=str(self.root.parent),LIFEOS_MEMORY_INTERNAL='1'),timeout=30)
        self.assertEqual((result.returncode,result.stdout,result.stderr),(0,'',''))

    def test_retained_history_refuses_before_any_live_publication(self):
        self.inventory(50,20)
        self.assertTrue(self.sync()['ok'])
        self.seed_runs(398)
        near = self.sync()
        self.assertTrue(near['ok'],near)
        before = self.artifact_bytes()
        result = self.sync()
        self.assertFalse(result['ok'],result)
        self.assertIn('capacity',result['message'].lower())
        self.assertIn('10026',result['message'])
        self.assertEqual(self.artifact_bytes(),before)
        self.assertFalse(self.owner.fixture.memory.transaction.journal.exists())
        with closing(sqlite3.connect(self.graph())) as connection:
            self.assertEqual(connection.execute('SELECT COUNT(*) FROM sync_run').fetchone()[0],402)

    def test_fresh_inventory_above_projection_capacity_creates_no_live_artifacts(self):
        self.inventory(0,85)
        before = self.artifact_bytes()
        result = self.sync()
        self.assertFalse(result['ok'],result)
        self.assertIn('capacity',result['message'].lower())
        self.assertEqual(self.artifact_bytes(),before)
        self.assertFalse(self.owner.fixture.memory.transaction.journal.exists())

    def test_success_reports_bounded_capacity_and_warning_without_source_text(self):
        self.inventory(100,50)
        result = self.sync()
        self.assertTrue(result['ok'],result)
        capacity = result['capacity']
        self.assertEqual(capacity['graph_fields'],{'used':9136,'limit':10000})
        self.assertEqual(capacity['tables']['sync_run'],{'used':2,'limit':2048})
        self.assertIn('graph_fields',capacity['warnings'])
        self.assertNotIn('Synthetic',json.dumps(capacity))
        self.assertEqual(capacity['database_bytes']['used'],self.graph().stat().st_size)

    def test_table_limit_refuses_before_publication_and_preserves_previous_graph(self):
        self.inventory(0,0)
        self.assertTrue(self.sync()['ok'])
        self.seed_runs(2046)
        before = self.artifact_bytes()
        result = self.sync()
        self.assertFalse(result['ok'],result)
        self.assertEqual(self.artifact_bytes(),before)
        self.assertFalse(self.owner.fixture.memory.transaction.journal.exists())

    def test_empty_graph_reader_does_not_request_automatic_generation(self):
        self.inventory(0,0)
        self.assertTrue(self.sync()['ok'])
        from lifeos_hook_bridge.memory_atlas import view
        result = view(self.owner.fixture.memory,self.service.scope(self.owner.context),
            target='/api/atlas/insights')
        self.assertTrue(result['body']['available'])
        self.assertFalse(result['body']['stale'])
        self.assertIsNone(result['body']['narrative'])

    def test_private_planned_graph_is_refused_without_publishing_public_snapshot(self):
        self.inventory(1,1)
        memory = self.owner.fixture.memory
        from lifeos_hook_bridge.memory_access import NativeMemory
        original = NativeMemory._native
        seen = []
        def changed(instance, action, **arguments):
            result = original(instance,action,**arguments)
            if action == 'atlas_sync_plan':
                seen.append(action)
                result['graph']['graph']['sync_run'][0]['stats'] = '<private>Synthetic planned secret</private>'
            return result
        NativeMemory._native = changed
        try:
            result = self.sync()
        finally:
            NativeMemory._native = original
        self.assertEqual(seen,['atlas_sync_plan'])
        self.assertFalse(result['ok'],result)
        self.assertNotIn('Synthetic planned secret',json.dumps(result))
        self.assertFalse(self.graph().exists())
        self.assertFalse(self.graph().with_name('snapshot.json').exists())
        self.assertFalse(memory.transaction.journal.exists())


class MemoryAtlasRefreshJobTests(unittest.TestCase):
    def setUp(self):
        self.fixture = command_fixture.MemoryOwnerJobCommandTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.native.root
        source = Path(os.environ['LIFEOS_MEMORY_SOURCE'])
        for name in ('ATLAS','PULSE'):
            target = self.root/'LIFEOS'/name
            if not target.exists():
                target.symlink_to(source/'LIFEOS'/name,target_is_directory=True)
        self.requests = []
        requests = self.requests
        class Gateway(BaseHTTPRequestHandler):
            def do_POST(self):
                requests.append(json.loads(self.rfile.read(int(self.headers['Content-Length']))))
                content = json.dumps({'id':'synthetic-atlas-response','type':'message','role':'assistant',
                    'model':'synthetic-atlas-model','content':[{'type':'text','text':'Synthetic Atlas metrics narrative.'}],
                    'stop_reason':'end_turn','usage':{'input_tokens':10,'output_tokens':5}}).encode()
                self.send_response(200)
                self.send_header('Content-Type','application/json')
                self.send_header('Content-Length',str(len(content)))
                self.end_headers()
                self.wfile.write(content)
            def log_message(self, *arguments):
                pass
        gateway = ThreadingHTTPServer(('127.0.0.1',0),Gateway)
        threading.Thread(target=gateway.serve_forever,daemon=True).start()
        self.addCleanup(gateway.server_close)
        self.addCleanup(gateway.shutdown)
        route = {'provider':'lifeos-local-gateway','model':'synthetic-atlas-model',
            'base_url':f'http://127.0.0.1:{gateway.server_port}','api_mode':'anthropic'}
        profile = self.fixture.fixture.home
        self.fixture.configuration.update(lambda value: value['destinations']['terminal:'+str(profile)]
            ['model_routes'].append(route_identity(**route)))
        environment = self.fixture.native.home/'.config/lifeos-hook-bridge/model.env'
        environment.parent.mkdir(parents=True,exist_ok=True)
        environment.write_text('ANTHROPIC_BASE_URL='+route['base_url']+'\n'
            'ANTHROPIC_AUTH_TOKEN=synthetic-token\nLIFEOS_CHILD_INFERENCE_DIRECT=1\n'
            "LIFEOS_MODEL_TIER_MAP='"+json.dumps({'pin':'none','opus':{'model':route['model'],'effort':'xhigh'}})+"'\n")
        environment.chmod(0o600)

    def job(self, name):
        result = self.fixture.call(name)
        self.assertEqual(result.stderr,'')
        return result,json.loads(result.stdout)

    def test_regeneration_reconciles_changed_sources_before_actual_model_request(self):
        gear = self.root/'LIFEOS/USER/GEAR.md'
        gear.write_text('## Computing\n| **Laptop** | Synthetic original device | daily |\n')
        result, receipt = self.job('atlas-sync')
        self.assertEqual(result.returncode,0,receipt)
        result, receipt = self.job('atlas-insights')
        self.assertEqual(result.returncode,0,receipt)
        cache = self.root/'LIFEOS/MEMORY/STATE/atlas-insights.json'
        self.assertTrue(cache.exists(),receipt)
        before = json.loads(cache.read_text())
        gear.write_text('## Computing\n| **Laptop** | Synthetic changed device | daily |\n')
        result, receipt = self.job('atlas-insights')
        self.assertEqual(result.returncode,0,receipt)
        graph = self.root.parent/'.local/state/lifeos/atlas/atlas.db'
        with closing(sqlite3.connect(graph)) as connection:
            names = [row[0] for row in connection.execute('SELECT display_name FROM asset')]
        self.assertIn('Synthetic changed device',names)
        self.assertNotEqual(json.loads(cache.read_text())['hash'],before['hash'])
        self.assertEqual(len(self.requests),2)

    def test_empty_regeneration_initializes_graph_and_remains_idle(self):
        MemoryAtlasCapacityTests.inventory(self,0,0)
        result, receipt = self.job('atlas-insights')
        self.assertEqual(result.returncode,0,receipt)
        graph = self.root.parent/'.local/state/lifeos/atlas/atlas.db'
        self.assertTrue(graph.exists(),receipt)
        self.assertFalse(self.requests)
        self.assertFalse((self.root/'LIFEOS/MEMORY/STATE/atlas-insights.json').exists())

    def test_owner_command_reports_capacity_refusal_without_inference(self):
        MemoryAtlasCapacityTests.inventory(self,0,85)
        result, receipt = self.job('atlas-sync')
        self.assertNotEqual(result.returncode,0)
        self.assertEqual(receipt['status'],'failed')
        self.assertIn('capacity',receipt['output'].lower())
        self.assertIn('10066',receipt['output'])
        self.assertFalse((self.root.parent/'.local/state/lifeos/atlas/atlas.db').exists())
        self.assertEqual(self.fixture.fixture.fixture.received,[])


if __name__ == '__main__':
    unittest.main()
