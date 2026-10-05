# ABOUTME: Characterizes actual PULSE adapter cache and no-source publication paths.
# ABOUTME: Uses synthetic manifests, sources, and cache files without calling a model.
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest

import test_memory_delegation as delegation_fixture


class MemoryPulseAdapterTests(unittest.TestCase):
    def setUp(self):
        self.fixture = delegation_fixture.MemoryDelegationTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        source = Path(os.environ['LIFEOS_MEMORY_SOURCE'])
        pulse = self.root / 'LIFEOS/PULSE'
        pulse.mkdir()
        for directory in ('adapters', 'lib', 'Schema', 'Tools'):
            shutil.copytree(source / 'LIFEOS/PULSE' / directory, pulse / directory)
        (pulse / 'node_modules').symlink_to(source / 'LIFEOS/PULSE/node_modules')
        (self.root / 'node_modules').symlink_to(source / 'node_modules')
        (pulse / 'pages').mkdir()
        self.manifest = pulse / 'pages/synthetic.manifest.toml'
        self.manifest.write_text('id = "synthetic"\ntitle = "Synthetic fixture"\n'
            'dataType = "CollectionPageSchema"\nsourceGlobs = ["LIFEOS/USER/TELOS/BOOKS.md"]\n'
            'adapterPromptFile = "LIFEOS/PULSE/pages/synthetic.adapter.md"\nmodel = "haiku"\n'
            'rebuildButton = true\norder = 1\nadapterVersion = "1.0.0"\n')
        (pulse / 'pages/synthetic.adapter.md').write_text('Render the declared synthetic collection as JSON.\n')
        self.source = self.root / 'LIFEOS/USER/TELOS/BOOKS.md'
        self.source.parent.mkdir(parents=True)
        self.data = self.root / 'LIFEOS/MEMORY/PULSE_DATA'
        self.log = self.root / 'LIFEOS/MEMORY/OBSERVABILITY/adapter-runs.jsonl'

    def call(self, *, context=True):
        environment = dict(os.environ, HOME=str(self.fixture.fixture.home), BUN_CONFIG_NO_AUTO_INSTALL='1')
        environment.pop('LIFEOS_MEMORY_INTERNAL', None)
        environment.pop('LIFEOS_MEMORY_CONTEXT', None)
        if context:
            environment['LIFEOS_MEMORY_CONTEXT'] = json.dumps(asdict(self.fixture.context))
        return subprocess.run(['bun', '--no-install', str(self.root / 'LIFEOS/PULSE/Tools/AdapterCli.ts'), 'synthetic'],
            env=environment, capture_output=True, text=True, timeout=40)

    def cached(self, content='# Synthetic collection\nA synthetic book.\n'):
        self.source.write_text(content)
        digest = hashlib.sha256(self.source.read_bytes()).hexdigest()
        key = hashlib.sha256(f'{self.source}:{digest}|adapter:1.0.0|model:haiku|schema:1.0.0'.encode()).hexdigest()
        meta = {'schemaVersion': '1.0.0', 'pageId': 'synthetic', 'lastBuildAt': '2026-10-04T00:00:00.000Z',
            'sourceHashes': {str(self.source): digest}, 'adapterVersion': '1.0.0', 'model': 'haiku',
            'costUSD': 0, 'latencyMs': 0, 'provenance': 'customized', 'warnings': [], 'cacheKey': key}
        page = {'schemaVersion': '1.0.0', 'data': {'kind': 'collection', 'title': 'Synthetic fixture',
            'category': 'taste', 'items': [{'name': 'A synthetic book', 'private': False}], 'meta': meta}, '_meta': meta}
        self.data.mkdir(parents=True)
        (self.data / 'synthetic.meta.json').write_text(json.dumps(meta))
        (self.data / 'synthetic.json').write_text(json.dumps(page))

    def test_owner_cache_hit_retains_native_result_without_a_model_call(self):
        self.cached()
        before = (self.data / 'synthetic.json').read_bytes()
        result = self.call()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        value = json.loads(result.stdout)
        self.assertEqual(value['status'], 'cached')
        self.assertEqual(value['sourceCount'], 1)
        self.assertEqual((self.data / 'synthetic.json').read_bytes(), before)

    def test_no_sources_retains_native_status_and_private_publications(self):
        result = self.call()
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(result.stderr, '')
        self.assertEqual(json.loads(result.stdout)['status'], 'no-sources')
        for path in (self.data / 'synthetic.error.json', self.data / '_index.json', self.log):
            with self.subTest(path=path.name):
                self.assertTrue(path.exists())
                self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_missing_context_refuses_before_error_index_or_log_publication(self):
        result = self.call(context=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.data.exists())
        self.assertFalse(self.log.exists())
        self.assertNotIn('Synthetic fixture', result.stdout)

    def test_read_only_owner_cannot_publish_error_index_or_log(self):
        self.fixture.configuration.update(lambda value: value['destinations']['chat-a:200'].update(write=[]))
        self.assertNotEqual(self.call().returncode, 0)
        self.assertFalse(self.data.exists())
        self.assertFalse(self.log.exists())

    def test_private_source_cannot_reuse_raw_source_cache(self):
        self.cached('<private>Synthetic hidden collection.</private>\n')
        result = self.call()
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('"status": "cached"', result.stdout)

    def test_foreign_source_refuses_before_log_or_index_publication(self):
        self.cached()
        foreign = self.fixture.fixture.home / 'foreign-adapter-source.md'
        foreign.write_text('Synthetic foreign collection.\n')
        self.source.unlink(); self.source.symlink_to(foreign)
        result = self.call()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.data / '_index.json').exists())
        self.assertFalse(self.log.exists())

    def test_foreign_error_destination_refuses_before_any_publication(self):
        self.data.mkdir(parents=True)
        foreign = self.fixture.fixture.home / 'foreign-adapter-error.json'
        before = b'{"synthetic_foreign":"preserved"}\n'
        foreign.write_bytes(before)
        target = self.data / 'synthetic.error.json'
        target.symlink_to(foreign)
        self.assertNotEqual(self.call().returncode, 0)
        self.assertTrue(target.is_symlink())
        self.assertEqual(foreign.read_bytes(), before)
        self.assertFalse((self.data / '_index.json').exists())
        self.assertFalse(self.log.exists())
