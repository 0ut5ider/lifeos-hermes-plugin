# ABOUTME: Executes actual PULSE adapter children under native derivative synchronization.
# ABOUTME: Checks generated pages, cache reuse, missing sources, and revoked child authority.
from dataclasses import asdict
import json
import os
from pathlib import Path
import subprocess
import sys
import shutil
import unittest

import test_memory_pulse_adapter_inference as inference_fixture


class MemoryDerivedSyncAdapterTests(unittest.TestCase):
    def setUp(self):
        self.fixture = inference_fixture.MemoryPulseAdapterInferenceTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.adapter = self.fixture.fixture
        self.root = self.adapter.root
        self.state = self.root / 'LIFEOS/MEMORY/STATE/derived-sync.json'
        self.log = self.root / 'LIFEOS/MEMORY/OBSERVABILITY/derived-sync.jsonl'

    def call(self, *args):
        root = Path(__file__).resolve().parents[1]
        environment = {**os.environ, 'HOME': str(self.adapter.fixture.fixture.home),
            'HERMES_HOME': str(self.fixture.configuration.path.parent),
            'LIFEOS_MEMORY_CONFIGURATION': str(self.fixture.configuration.path),
            'LIFEOS_MEMORY_CONTEXT': json.dumps(asdict(self.fixture.runtime.context())),
            'LIFEOS_MEMORY_SESSION': 'native-session', 'LIFEOS_CHILD_PROVIDER': '',
            'LIFEOS_HOOK_MODEL_ENV': str(self.fixture.model_environment), 'BUN_CONFIG_NO_AUTO_INSTALL': '1',
            'PATH': os.pathsep.join([str(root / 'lifeos_hook_bridge/bin'), str(Path(sys.executable).parent),
                                   str(self.adapter.bin), '/usr/bin', '/bin'])}
        environment.pop('LIFEOS_MEMORY_INTERNAL', None)
        return subprocess.run(['bun', '--no-install', str(self.root / 'LIFEOS/TOOLS/DerivedSync.ts'), *args],
            env=environment, capture_output=True, text=True, timeout=90)

    def successful(self, *args):
        result = self.call(*args)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        return result

    def tracking(self):
        self.assertTrue(self.state.is_file())
        self.assertTrue(self.log.is_file())
        for path in (self.state, self.log, self.adapter.log, self.adapter.data / '_index.json'):
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        line = json.loads(self.log.read_text().splitlines()[-1])
        self.assertEqual(len(line['actions']), 1)
        self.assertIn('AdapterCli.ts synthetic', line['actions'][0]['cmd'])
        self.assertEqual(line['actions'][0]['exit'], 0)
        self.assertFalse((self.state.parent / 'derived-sync.lock').exists())

    def test_actual_child_generation_publishes_page_and_tracking(self):
        self.successful()
        self.assertEqual(len(self.fixture.received), 1)
        page = json.loads((self.adapter.data / 'synthetic.json').read_text())
        self.assertEqual(page['data']['title'], 'Synthetic generated collection')
        self.tracking()
        self.assertEqual(self.successful().stdout, '')
        self.assertEqual(len(self.fixture.received), 1)

    def test_actual_cached_child_preserves_page_and_publishes_tracking(self):
        self.adapter.cached()
        before = (self.adapter.data / 'synthetic.json').read_bytes()
        self.successful()
        self.assertEqual((self.adapter.data / 'synthetic.json').read_bytes(), before)
        self.assertEqual(self.fixture.received, [])
        self.assertEqual(json.loads(self.adapter.log.read_text().splitlines()[-1])['status'], 'cached')
        self.tracking()

    def test_native_missing_source_child_retains_successful_sync_contract(self):
        self.adapter.source.unlink()
        self.successful()
        self.assertEqual(self.fixture.received, [])
        self.assertFalse((self.adapter.data / 'synthetic.json').exists())
        self.assertEqual(json.loads((self.adapter.data / 'synthetic.error.json').read_text())['kind'], 'no-sources')
        self.assertEqual(json.loads(self.adapter.log.read_text().splitlines()[-1])['status'], 'no-sources')
        self.tracking()

    def test_revocation_during_child_refuses_page_and_tracking(self):
        self.fixture.on_request = lambda: self.fixture.configuration.update(lambda value: value['accounts'].pop('chat-a:100'))
        result = self.call()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('[DerivedSync] action failed:', result.stderr)
        self.assertEqual(len(self.fixture.received), 1)
        self.assertFalse((self.adapter.data / 'synthetic.json').exists())
        self.assertFalse(self.state.exists())
        self.assertFalse(self.log.exists())
        self.assertFalse((self.state.parent / 'derived-sync.lock').exists())

    def test_original_native_cached_sync_matches_selected_child_effects(self):
        self.adapter.cached()
        page = (self.adapter.data / 'synthetic.json').read_bytes()
        self.successful()
        hashes = json.loads(self.state.read_text())['fileHashes']
        line = json.loads(self.log.read_text().splitlines()[-1])
        index = json.loads((self.adapter.data / '_index.json').read_text())['pages']
        self.state.unlink()
        self.log.unlink()
        tools = self.root / 'LIFEOS/TOOLS'
        source = tools.resolve()
        tools.unlink()
        tools.mkdir()
        for path in source.iterdir():
            if path.name != 'DerivedSync.ts':
                (tools / path.name).symlink_to(path)
        control = Path(os.environ['LIFEOS_FRESHNESS_CONTROL_SOURCE']) / 'LIFEOS/TOOLS/DerivedSync.ts'
        shutil.copyfile(control, tools / 'DerivedSync.ts')
        self.successful()
        self.assertEqual(json.loads(self.state.read_text())['fileHashes'], hashes)
        original = json.loads(self.log.read_text().splitlines()[-1])
        self.assertEqual(original['changed'], line['changed'])
        self.assertEqual(original['actions'][0]['cmd'], line['actions'][0]['cmd'])
        self.assertEqual(original['actions'][0]['exit'], line['actions'][0]['exit'])
        self.assertEqual(json.loads((self.adapter.data / '_index.json').read_text())['pages'], index)
        self.assertEqual((self.adapter.data / 'synthetic.json').read_bytes(), page)
        self.assertEqual(self.fixture.received, [])
        self.assertEqual(self.successful().stdout, '')
