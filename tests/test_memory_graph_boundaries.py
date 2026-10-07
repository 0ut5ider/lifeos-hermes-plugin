# ABOUTME: Probes durable managed-mode detection and native duplicate-slug selection.
# ABOUTME: Uses real graph commands, native note creation, and reviewed adoption.
import json
import os
from pathlib import Path
import unittest

import test_memory_graph as graph_fixture
from test_memory_native import OWNER


class MemoryGraphBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.case = graph_fixture.MemoryGraphTests()
        self.case.setUp()
        self.case._testMethodName = self._testMethodName
        self.addCleanup(self.case.doCleanups)

    def test_artifact_alias_to_the_locked_registry_refuses_before_journal_collection(self):
        self.case.output.mkdir(mode=0o700)
        artifact = self.case.output / 'graph.json'
        os.link(self.case.native.memory.database, artifact)
        before = self.case.native.memory.database.read_bytes()
        result = self.case.call('build')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.case.native.memory.database.read_bytes(), before)
        self.assertTrue(artifact.samefile(self.case.native.memory.database))
        self.assertFalse(self.case.native.memory.transaction.journal.exists())

    def test_persistent_managed_marker_refuses_connector_loss_in_a_new_cli_process(self):
        marker = self.case.fixture.root / 'LIFEOS/USER/CONFIG/memory-http.json'
        marker.write_text(json.dumps({'version': 1}))
        marker.chmod(0o600)
        (marker.parent / 'memory-access.json').unlink()
        for command in self.case.commands:
            with self.subTest(command=command):
                result = self.case.call(*command)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn('Synthetic current target', result.stdout + result.stderr)
        self.assertFalse(self.case.output.exists())

    def test_persistent_marker_also_refuses_connector_loss_in_knowledge_navigation(self):
        marker = self.case.fixture.root / 'LIFEOS/USER/CONFIG/memory-http.json'
        marker.write_text(json.dumps({'version': 1}))
        marker.chmod(0o600)
        (marker.parent / 'memory-access.json').unlink()
        self.case.module = self.case.fixture.root / 'LIFEOS/TOOLS/KnowledgeGraph.ts'
        for command in [('stats',), ('hubs',), ('find', 'untagged'),
                        ('related', 'synthetic-lab-routing'), ('traverse', 'synthetic-lab-routing')]:
            with self.subTest(command=command):
                result = self.case.call(*command)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn('Synthetic current target', result.stdout + result.stderr)

    def test_duplicate_slug_preserves_native_first_domain_selection(self):
        for entity, content in [('person', 'Synthetic first domain body'),
                                ('company', 'Synthetic second domain body')]:
            created = self.case.native.memory._native('add', item={'type': 'knowledge', 'entity_type': entity,
                'name': 'Synthetic duplicate graph', 'content': content})
            self.assertTrue(created['ok'], created)
        preview = self.case.native.memory.preview_adoption(OWNER)
        adopted = self.case.native.memory.adopt(OWNER, preview['signature'], {}, 'graph-adopt-duplicates')
        self.assertEqual(adopted['status'], 'committed', adopted)
        managed = self.case.call('build')
        self.assertEqual(managed.returncode, 0, managed.stderr)
        self.assertIn('duplicate node id', managed.stderr)
        graph = json.loads((self.case.output / 'graph.json').read_text())
        selected = next(node for node in graph['nodes'] if node['id'] == 'synthetic-duplicate-graph')
        self.assertEqual(selected['type'], 'person')
        (self.case.fixture.root / 'LIFEOS/USER/CONFIG/memory-access.json').unlink()
        result = self.case.call('build', context=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('duplicate node id', result.stderr)
        self.assertEqual(managed.stderr, result.stderr)
        standalone = json.loads((self.case.output / 'graph.json').read_text())
        selected = next(node for node in standalone['nodes'] if node['id'] == 'synthetic-duplicate-graph')
        self.assertEqual(selected['type'], 'person')
