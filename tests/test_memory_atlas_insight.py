# ABOUTME: Exercises native Atlas insight preparation and fixed owner publication.
# ABOUTME: Uses real graph state to reject changed authority, excluded output, and later destination edits.
from datetime import datetime, timezone
import json
from dataclasses import asdict
import os
from pathlib import Path
import subprocess
import unittest
import test_memory_manual_state as state_fixture
from lifeos_hook_bridge.memory_service import MemoryService


class MemoryAtlasInsightTests(unittest.TestCase):
    def setUp(self):
        self.fixture = state_fixture.MemoryManualStateTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        self.owner = self.fixture.fixture
        self.configuration = self.owner.configuration
        self.service = MemoryService(self.configuration)
        source = Path(os.environ['LIFEOS_MEMORY_SOURCE'])
        for name in ('PULSE', 'ATLAS'):
            (self.root / 'LIFEOS' / name).symlink_to(source / 'LIFEOS' / name)
        self.cache = self.root / 'LIFEOS/MEMORY/STATE/atlas-insights.json'

    def seed(self):
        module = self.root / 'LIFEOS/ATLAS/Store.ts'
        script = ('import {Store} from ' + json.dumps(str(module)) + ';const store=new Store();'
            'store.applyRun("gear","full",{complete:true,assets:[{kind:"device",key:"gear:synthetic",'
            'name:"SyntheticAtlasCurrent",attrs:{}}],edges:[]});store.close();')
        result = subprocess.run(['bun', '--no-install', '-e', script], capture_output=True, text=True,
            timeout=10, env=dict(os.environ, HOME=str(self.owner.fixture.home), LIFEOS_MEMORY_INTERNAL="1"))
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, '', ''))

    def call(self, operation, **arguments):
        return self.service.native(self.owner.context, operation, arguments)

    def prepare(self):
        result = self.call('atlas_insight_prepare')
        self.assertTrue(result['ok'], result)
        return result

    def value(self, prepared):
        return {'hash': prepared['plan']['hash'], 'narrative': 'Synthetic counted device narrative.',
            'generated_at': datetime.now(timezone.utc).isoformat()}

    def test_current_graph_prepare_and_fixed_private_publication(self):
        self.seed()
        prepared = self.prepare()
        self.assertIsInstance(prepared['plan']['metrics'], dict)
        self.assertRegex(prepared['plan']['hash'], '^[0-9a-f]{16}$')
        value = self.value(prepared)
        result = self.call('atlas_insight_publish', signature=prepared['signature'], value=value)
        self.assertTrue(result['ok'], result)
        self.assertEqual(json.loads(self.cache.read_text()), value)
        self.assertEqual(self.cache.stat().st_mode & 0o777, 0o600)

    def test_absent_graph_prepare_has_no_generated_cache_or_model_effect(self):
        prepared = self.prepare()
        self.assertEqual(prepared['plan'], {'metrics': None, 'hash': None})
        self.assertFalse(self.cache.exists())

    def test_current_revision_check_refuses_changed_graph_and_later_cache(self):
        self.seed()
        prepared = self.prepare()
        self.cache.parent.mkdir(parents=True, exist_ok=True)
        self.cache.write_text('{"hash":"later","narrative":"Synthetic later edit","generated_at":"later"}')
        before = self.cache.read_bytes()
        result = self.call('atlas_insight_publish', signature=prepared['signature'], value=self.value(prepared))
        self.assertFalse(result['ok'], result)
        self.assertEqual(self.cache.read_bytes(), before)

    def test_wrong_metadata_and_private_generated_text_cannot_publish(self):
        self.seed()
        prepared = self.prepare()
        for change in ({'hash': '0' * 16}, {'narrative': '<private>SyntheticAtlasHidden</private>'},
                {'generated_at': True}, {'extra': 'undeclared'}):
            with self.subTest(change=change):
                result = self.call('atlas_insight_publish', signature=prepared['signature'], value={**self.value(prepared), **change})
                self.assertFalse(result['ok'], result)
                self.assertFalse(self.cache.exists())

    def test_read_only_and_revoked_owners_cannot_prepare_generation(self):
        self.seed()
        self.configuration.update(lambda value: value['destinations']['chat-a:200'].update(write=[]))
        self.assertFalse(self.call('atlas_insight_prepare')['ok'])
        self.configuration.update(lambda value: value['accounts'].clear())
        self.assertFalse(self.call('atlas_insight_prepare')['ok'])
        self.assertFalse(self.cache.exists())

    def test_graph_metadata_changes_invalidate_prepared_sources(self):
        self.seed()
        path = self.root.parent / '.local/state/lifeos/atlas/atlas.db'
        prepared = self.prepare()
        os.utime(path, ns=(path.stat().st_atime_ns, path.stat().st_mtime_ns + 1_000_000))
        self.assertFalse(self.call('atlas_insight_check', signature=prepared['signature'])['ok'])
        self.assertFalse(self.cache.exists())

    def test_private_collector_sources_refuse_generation(self):
        self.seed()
        path = self.root / 'LIFEOS/USER/GEAR.md'
        path.write_text('<private>SyntheticAtlasHidden</private>')
        result = self.call('atlas_insight_prepare')
        self.assertFalse(result['ok'], result)
        self.assertNotIn('SyntheticAtlasHidden', json.dumps(result))
        self.assertFalse(self.cache.exists())

    def test_actual_post_render_changes_and_process_death_preserve_recovery(self):
        self.seed()
        for mode in ('source', 'destination', 'authority', 'projection-source', 'projection-authority', 'interrupt'):
            with self.subTest(mode=mode):
                result = subprocess.run([os.environ.get('PYTHON', '/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python'),
                    str(Path(__file__).with_name('memory_atlas_insight_process.py')), str(self.configuration.path), mode,
                    json.dumps(asdict(self.owner.context))], capture_output=True, text=True, timeout=30)
                self.assertEqual(result.stderr, '')
                if mode == 'interrupt':
                    self.assertEqual(result.returncode, 73, result.stdout)
                    self.assertTrue(self.cache.exists())
                    self.prepare()
                    self.assertFalse(self.cache.exists())
                else:
                    self.assertEqual(result.returncode, 0, result.stdout)
                    self.assertFalse(json.loads(result.stdout)['ok'])
                    if mode == 'destination':
                        self.assertEqual(self.cache.read_text(), '{"hash":"later","narrative":"Synthetic later edit","generated_at":"later"}')
                        self.cache.unlink()
                    else: self.assertFalse(self.cache.exists())
                path = self.root / 'LIFEOS/USER/GEAR.md'
                if path.exists(): path.unlink()
                if mode.endswith('authority'):
                    self.configuration.update(lambda value: value['accounts'].update({'chat-a:100': 'owner'}))
