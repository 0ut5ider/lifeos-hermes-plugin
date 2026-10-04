# ABOUTME: Exercises native Knowledge graph navigation with current governed notes and real connector processes.
# ABOUTME: Checks standalone parity, admission refusal, retirement, source integrity, and linked-note effects.
from contextlib import closing
from dataclasses import asdict
import json
import os
from pathlib import Path
import subprocess
import unittest

import test_memory_delegation as delegation
from test_memory_native import OWNER


class KnowledgeGraphTests(unittest.TestCase):
    def setUp(self):
        self.fixture = delegation.MemoryDelegationTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.native = self.fixture.fixture
        self.reference = self.native.remember('Synthetic current graph source [[synthetic-current-target]]',
                                             'graph-source')['reference']
        self.target = self.native.memory.remember(OWNER, category='project',
            content='Synthetic current graph target', title='Synthetic current target', project='lab',
            request_id='graph-target')['reference']
        self.module = self.fixture.root / 'LIFEOS/TOOLS/KnowledgeGraph.ts'
        self.commands = [('stats',), ('hubs',), ('find', 'synthetic'),
                         ('related', 'synthetic-lab-routing'), ('traverse', 'synthetic-lab-routing'),
                         ('find', 'untagged')]

    def call(self, *arguments, context=True):
        environment = dict(os.environ, HOME=str(self.native.home),
                           LIFEOS_DIR=str(self.fixture.root / 'LIFEOS'), BUN_CONFIG_NO_AUTO_INSTALL='1')
        environment.pop('LIFEOS_MEMORY_INTERNAL', None)
        environment.pop('LIFEOS_MEMORY_CONTEXT', None)
        if context:
            environment['LIFEOS_MEMORY_CONTEXT'] = json.dumps(asdict(self.fixture.context))
        result = subprocess.run(['bun', '--no-install', str(self.module), *arguments],
            env=environment, capture_output=True, text=True, timeout=30)
        directory = os.environ.get('LIFEOS_KNOWLEDGE_GRAPH_EVIDENCE_DIR')
        if directory:
            destination = Path(directory) / self._testMethodName
            destination.mkdir(parents=True, exist_ok=True)
            name = '-'.join(arguments) + ('-bound' if context else '-unbound')
            (destination / (name + '.json')).write_text(json.dumps({'arguments': arguments,
                'context': context, 'status': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr}, indent=2) + '\n')
        return result

    def source(self, reference):
        with self.native.memory._transaction() as database:
            path = database.execute('SELECT path FROM records WHERE id=?', (reference['id'],)).fetchone()[0]
        return self.native.memory._path(path)

    def test_owner_navigation_preserves_the_native_link_and_all_command_outputs(self):
        managed = []
        for command in self.commands:
            result = self.call(*command)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stderr, '')
            managed.append(result.stdout)
        self.assertIn('Nodes: 2', managed[0])
        self.assertIn('wikilink: 1', managed[0])
        self.assertIn('synthetic-current-target', managed[3])
        self.assertIn('Synthetic current target', managed[3])
        self.assertIn('Synthetic current target', managed[5])
        self.assertIn('Synthetic lab routing', managed[5])
        (self.fixture.root / 'LIFEOS/USER/CONFIG/memory-access.json').unlink()
        for command, expected in zip(self.commands, managed):
            with self.subTest(command=command):
                result = self.call(*command, context=False)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stderr, '')
                self.assertEqual(result.stdout, expected)

    def test_owner_typed_relationships_preserve_native_labels_and_weight(self):
        created = self.native.memory._native('add', item={'type': 'knowledge', 'entity_type': 'research',
            'name': 'Synthetic typed source', 'content': 'Synthetic typed graph source',
            'related': [{'slug': 'synthetic-current-target', 'type': 'supports'}]})
        self.assertTrue(created['ok'], created)
        source = Path(created['path'])
        before = source.read_bytes()
        preview = self.native.memory.preview_adoption(OWNER)
        receipt = self.native.memory.adopt(OWNER, preview['signature'],
            {source.relative_to(self.native.memory.root).as_posix(): 'lab'}, 'graph-adopt-typed-source')
        self.assertEqual(receipt['status'], 'committed', receipt)
        self.assertEqual(receipt['facts_adopted'], 1)
        self.assertEqual(source.read_bytes(), before)
        related = self.call('related', 'synthetic-typed-source')
        self.assertEqual(related.returncode, 0, related.stderr)
        self.assertEqual(related.stderr, '')
        self.assertIn('Typed relationships', related.stdout)
        self.assertIn('supports', related.stdout)
        traversed = self.call('traverse', 'synthetic-typed-source')
        self.assertEqual(traversed.returncode, 0, traversed.stderr)
        self.assertEqual(traversed.stderr, '')
        self.assertIn('weight: 5', traversed.stdout)
        (self.fixture.root / 'LIFEOS/USER/CONFIG/memory-access.json').unlink()
        for command, expected in [(('related', 'synthetic-typed-source'), related.stdout),
                                  (('traverse', 'synthetic-typed-source'), traversed.stdout)]:
            with self.subTest(command=command):
                native = self.call(*command, context=False)
                self.assertEqual(native.returncode, 0, native.stderr)
                self.assertEqual(native.stderr, '')
                self.assertEqual(native.stdout, expected)

    def test_every_graph_command_refuses_missing_context_before_any_note_delivery(self):
        for command in self.commands:
            with self.subTest(command=command):
                result = self.call(*command, context=False)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn('Synthetic current target', result.stdout + result.stderr)
                self.assertNotIn('synthetic-current-target', result.stdout + result.stderr)
                self.assertNotIn('Nodes: 2', result.stdout)

    def test_revoked_author_cannot_navigate_current_notes(self):
        self.fixture.configuration.update(lambda config: config['accounts'].pop('chat-a:100'))
        result = self.call('related', 'synthetic-lab-routing')
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('Synthetic current target', result.stdout + result.stderr)

    def test_project_only_context_cannot_borrow_unclassified_note_metadata(self):
        self.fixture.configuration.update(lambda config: config['destinations']['chat-a:200'].update(
            read=['project'], projects=['lab']))
        result = self.call('related', 'synthetic-lab-routing')
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('Synthetic current target', result.stdout + result.stderr)

    def test_forgotten_note_and_its_edge_leave_current_graph_navigation(self):
        before = self.source(self.target).read_bytes()
        self.native.memory.forget(OWNER, self.target, 'graph-forget-target')
        result = self.call('related', 'synthetic-lab-routing')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        self.assertNotIn('Synthetic current target', result.stdout)
        self.assertNotIn('synthetic-current-target', result.stdout)
        self.assertEqual(self.source(self.target).read_bytes(), before)
        self.assertIn('Nodes: 1', self.call('stats').stdout)

    def test_correction_removes_the_superseded_wikilink_from_the_current_graph(self):
        self.native.memory.correct(OWNER, self.reference, 'Synthetic corrected graph source without a link', 'graph-correct')
        result = self.call('related', 'synthetic-lab-routing')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        self.assertNotIn('Wikilink references', result.stdout)
        self.assertIn('wikilink: 0', self.call('stats').stdout)
        self.assertIn('Tag co-occurrence', result.stdout)
        self.assertIn('Synthetic current target', result.stdout)

    def test_unregistered_note_does_not_enter_the_managed_graph(self):
        self.native.memory._native('add', item={'type': 'knowledge', 'entity_type': 'research',
            'name': 'SyntheticUnregisteredGraphTitle', 'content': 'Synthetic unregistered graph claim'})
        result = self.call('stats')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        self.assertIn('Nodes: 2', result.stdout)
        self.assertNotIn('SyntheticUnregisteredGraphTitle', result.stdout)

    def test_changed_registered_note_refuses_before_graph_metadata_delivery(self):
        path = self.source(self.target)
        path.write_text(path.read_text().replace('Synthetic current graph target', 'Synthetic outside graph mutation'))
        result = self.call('related', 'synthetic-lab-routing')
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('Synthetic current target', result.stdout + result.stderr)
        self.assertNotIn('Synthetic outside graph mutation', result.stdout + result.stderr)

    def test_redirected_note_refuses_instead_of_reading_foreign_graph_content(self):
        path = self.source(self.target)
        foreign = self.native.home / 'foreign-graph-note.md'
        foreign.write_bytes(path.read_bytes())
        path.unlink()
        path.symlink_to(foreign)
        result = self.call('related', 'synthetic-lab-routing')
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('Synthetic current target', result.stdout + result.stderr)

    def test_invalid_connector_has_no_raw_graph_fallback(self):
        (self.fixture.root / 'LIFEOS/USER/CONFIG/memory-access.json').write_text('{invalid')
        result = self.call('related', 'synthetic-lab-routing')
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('Synthetic current target', result.stdout + result.stderr)
