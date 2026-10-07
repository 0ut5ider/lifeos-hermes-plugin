# ABOUTME: Runs native MemoryGraph algorithms against synthetic current notes and retained memory silos.
# ABOUTME: Checks governed cache publication, retirement, authority changes, and standalone behavior.
from dataclasses import asdict
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

import test_memory_delegation as delegation
from test_memory_native import OWNER


class MemoryGraphTests(unittest.TestCase):
    def setUp(self):
        self.fixture = delegation.MemoryDelegationTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.native = self.fixture.fixture
        self.reference = self.native.remember('Synthetic graph source [[synthetic-current-target]]',
                                             'graph-source')['reference']
        self.target = self.native.memory.remember(OWNER, category='project',
            content='Synthetic current graph target', title='Synthetic current target', project='lab',
            request_id='graph-target')['reference']
        self.module = self.fixture.root / 'LIFEOS/TOOLS/MemoryGraph.ts'
        self.memory = self.fixture.root / 'LIFEOS/MEMORY'
        self.output = self.memory / 'GRAPH'
        self.commands = [('build',), ('build', '--all'), ('validate',), ('stats',),
                         ('patterns',), ('related', 'synthetic-lab-routing')]

    def call(self, *arguments, context=True):
        environment = dict(os.environ, HOME=str(self.native.home),
                           LIFEOS_DIR=str(self.fixture.root / 'LIFEOS'), BUN_CONFIG_NO_AUTO_INSTALL='1')
        environment.pop('LIFEOS_MEMORY_INTERNAL', None)
        environment.pop('LIFEOS_MEMORY_CONTEXT', None)
        if context:
            environment['LIFEOS_MEMORY_CONTEXT'] = json.dumps(asdict(self.fixture.context))
        result = subprocess.run(['bun', '--no-install', str(self.module), *arguments],
            env=environment, capture_output=True, text=True, timeout=45)
        directory = os.environ.get('LIFEOS_MEMORY_GRAPH_EVIDENCE_DIR')
        if directory:
            destination = Path(directory) / self._testMethodName
            destination.mkdir(parents=True, exist_ok=True)
            name = '-'.join(arguments) + ('-bound' if context else '-unbound')
            (destination / (name + '.json')).write_text(json.dumps({'arguments': arguments,
                'context': context, 'status': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr}, indent=2) + '\n')
        return result

    def successful(self, *arguments, context=True):
        result = self.call(*arguments, context=context)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        return result.stdout

    def cache(self):
        return {path.name: path.read_bytes() for path in self.output.iterdir() if path.is_file()}

    def note(self, relative, title, content):
        path = self.memory / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('---\ntitle: "' + title + '"\ntags: [synthetic]\n---\n' + content + '\n')
        return path

    def test_owner_build_preserves_actual_algorithms_and_standalone_graph(self):
        self.note('WORK/synthetic-work/ISA.md', 'Synthetic cross silo work', '[[synthetic-current-target]]')
        self.note('WORK/synthetic-prd/PRD.md', 'Synthetic PRD fallback', '[[synthetic-current-target]]')
        self.note('WISDOM/FRAMES/nested/frame.md', 'Synthetic wisdom frame', '[[synthetic-current-target]]')
        self.note('LEARNING/SYNTHESIS/lesson.md', 'Synthetic synthesis lesson', '[[synthetic-current-target]]')
        self.successful('build')
        managed = json.loads((self.output / 'graph.json').read_text())
        self.assertEqual(managed['nodeCount'], 6)
        self.assertEqual(managed['edgeCount'], 11)
        self.assertEqual({node['silo'] for node in managed['nodes']}, {'knowledge', 'work', 'wisdom', 'synthesis'})
        self.assertTrue(all(isinstance(node['pagerank'], float) for node in managed['nodes']))
        self.assertAlmostEqual(sum(node['pagerank'] for node in managed['nodes']), 1)
        self.assertIn('Synthetic current target', self.successful('related', 'synthetic-lab-routing'))
        self.assertIn('Synthetic wisdom frame', self.successful('patterns'))
        self.assertIn('6 nodes', self.successful('stats'))
        self.successful('validate')
        (self.fixture.root / 'LIFEOS/USER/CONFIG/memory-access.json').unlink()
        self.successful('build', context=False)
        native = json.loads((self.output / 'graph.json').read_text())
        managed.pop('generated'); native.pop('generated')
        directory = os.environ.get('LIFEOS_MEMORY_GRAPH_EVIDENCE_DIR')
        if directory:
            (Path(directory) / 'owner-graph-pair.json').write_text(json.dumps(
                {'managed': managed, 'standalone': native}, indent=2) + '\n')
        self.assertEqual(managed['nodeCount'], native['nodeCount'])
        self.assertEqual(managed['edgeCount'], native['edgeCount'])
        current = {node['id']: node for node in managed['nodes']}
        standalone = {node['id']: node for node in native['nodes']}
        self.assertEqual(set(current), set(standalone))
        for identifier in current:
            left, right = dict(current[identifier]), dict(standalone[identifier])
            self.assertAlmostEqual(left.pop('pagerank'), right.pop('pagerank'))
            left.pop('community'); right.pop('community')
            self.assertEqual(left, right)
        def partition(nodes):
            groups = {}
            for node in nodes:
                groups.setdefault(node['community'], set()).add(node['id'])
            return {frozenset(members) for members in groups.values()}
        self.assertEqual(partition(managed['nodes']), partition(native['nodes']))
        def edges(rows):
            return {tuple(sorted((edge['from'], edge['to']))) +
                    (edge['weight'], edge['kind'], edge.get('label')) for edge in rows}
        self.assertEqual(edges(managed['edges']), edges(native['edges']))

    def test_all_commands_refuse_missing_context_and_preserve_existing_artifacts(self):
        self.successful('build')
        before = self.cache()
        for command in self.commands:
            with self.subTest(command=command):
                result = self.call(*command, context=False)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn('Synthetic current target', result.stdout + result.stderr)
                self.assertEqual(self.cache(), before)

    def test_revocation_refuses_even_fresh_pattern_cache(self):
        self.successful('build')
        before = self.cache()
        self.fixture.configuration.update(lambda config: config['accounts'].pop('chat-a:100'))
        for command in [('patterns',), ('stats',), ('related', 'synthetic-lab-routing')]:
            with self.subTest(command=command):
                result = self.call(*command)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn('Synthetic current target', result.stdout + result.stderr)
                self.assertEqual(self.cache(), before)

    def test_forgotten_target_leaves_fresh_patterns_and_statistics(self):
        self.successful('build')
        self.native.memory.forget(OWNER, self.target, 'graph-forget')
        self.assertNotIn('Synthetic current target', self.successful('patterns'))
        self.assertIn('1 nodes', self.successful('stats'))
        self.assertNotIn('Synthetic current target', self.successful('related', 'synthetic-lab-routing'))

    def test_correction_removes_superseded_wikilink_but_keeps_current_tag_edge(self):
        self.native.memory.correct(OWNER, self.reference, 'Synthetic corrected graph source without a link', 'graph-correct')
        result = self.successful('related', 'synthetic-lab-routing')
        self.assertNotIn('[wikilink]', result)
        self.assertIn('[tag:untagged]', result)

    def test_unregistered_note_does_not_enter_current_graph(self):
        self.native.memory._native('add', item={'type': 'knowledge', 'entity_type': 'research',
            'name': 'Synthetic unregistered graph', 'content': 'Synthetic unregistered graph body'})
        self.successful('build')
        graph = json.loads((self.output / 'graph.json').read_text())
        self.assertEqual(graph['nodeCount'], 2)
        self.assertNotIn('Synthetic unregistered graph', (self.output / 'PATTERNS.md').read_text())

    def test_retired_claim_in_work_history_cannot_enter_current_patterns(self):
        self.note('WORK/synthetic-retired/ISA.md', 'Synthetic retained work', 'Synthetic current graph target')
        self.native.memory.forget(OWNER, self.target, 'graph-forget-history')
        self.successful('build')
        self.assertNotIn('Synthetic retained work', self.successful('patterns'))
        self.assertEqual(json.loads((self.output / 'graph.json').read_text())['nodeCount'], 1)

    def test_changed_registered_source_refuses_before_overwriting_artifacts(self):
        self.successful('build')
        before = self.cache()
        facts = self.native.memory.recall(OWNER, 'Synthetic current graph target')
        path = self.fixture.root / facts[0]['source']['path']
        path.write_text(path.read_text() + '\nSynthetic unrecorded graph mutation\n')
        result = self.call('patterns')
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('Synthetic current target', result.stdout + result.stderr)
        self.assertEqual(self.cache(), before)

    def test_foreign_work_link_refuses_before_delivery_or_publication(self):
        source = self.note('WORK/synthetic-work/ISA.md', 'Synthetic redirected work', 'Synthetic foreign marker')
        foreign = self.native.home / 'foreign-work.md'
        foreign.write_bytes(source.read_bytes())
        source.unlink(); source.symlink_to(foreign)
        result = self.call('build')
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('Synthetic redirected work', result.stdout + result.stderr)
        self.assertFalse(self.output.exists())

    def test_poisoned_cache_is_not_a_current_source(self):
        self.successful('build')
        (self.output / 'PATTERNS.md').write_text('Synthetic foreign cache claim')
        (self.output / 'graph.json').write_text('{invalid')
        self.assertNotIn('Synthetic foreign cache claim', self.successful('patterns'))
        self.assertIn('2 nodes', self.successful('stats'))

    def process(self, mode):
        result = subprocess.run([sys.executable, str(Path(__file__).with_name('memory_graph_process.py')),
            str(self.fixture.configuration.path), mode], capture_output=True, text=True, timeout=45,
            env={**os.environ, 'HOME': str(self.native.home)})
        self.assertEqual(result.stderr, '')
        directory = os.environ.get('LIFEOS_MEMORY_GRAPH_EVIDENCE_DIR')
        if directory:
            destination = Path(directory) / self._testMethodName
            destination.mkdir(parents=True, exist_ok=True)
            (destination / ('process-' + mode + '.json')).write_text(json.dumps(
                {'status': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr}, indent=2) + '\n')
        return result

    def test_source_change_after_real_render_refuses_publication(self):
        self.note('WORK/synthetic-work/ISA.md', 'Synthetic concurrent work', 'Synthetic initial work body')
        self.successful('build')
        before = self.cache()
        process = self.process('source')
        self.assertEqual(process.returncode, 0, process.stdout)
        response = json.loads(process.stdout)['result']
        self.assertFalse(response['ok'], response)
        self.assertEqual(response['stdout'], '')
        self.assertIn('sources changed during rendering', response['receipt']['reason'])
        self.assertEqual(self.cache(), before)

    def test_native_typed_contradiction_keeps_label_weight_and_report(self):
        created = self.native.memory._native('add', item={'type': 'knowledge', 'entity_type': 'research',
            'name': 'Synthetic typed graph source', 'content': 'Synthetic contradictory graph claim',
            'related': [{'slug': 'synthetic-current-target', 'type': 'contradicts'}]})
        self.assertTrue(created['ok'], created)
        path = Path(created['path'])
        preview = self.native.memory.preview_adoption(OWNER)
        receipt = self.native.memory.adopt(OWNER, preview['signature'],
            {path.relative_to(self.native.memory.root).as_posix(): 'lab'}, 'graph-adopt-typed')
        self.assertEqual(receipt['status'], 'committed', receipt)
        related = self.successful('related', 'synthetic-typed-graph-source')
        self.assertIn('[related:contradicts]', related)
        self.successful('build')
        graph = json.loads((self.output / 'graph.json').read_text())
        typed = [edge for edge in graph['edges'] if edge.get('label') == 'contradicts']
        self.assertEqual(len(typed), 1)
        self.assertEqual(typed[0]['weight'], 5)
        self.assertIn('_Synthetic typed graph source_', self.successful('patterns'))
        (self.fixture.root / 'LIFEOS/USER/CONFIG/memory-access.json').unlink()
        self.assertEqual(self.successful('related', 'synthetic-typed-graph-source', context=False), related)

    def test_all_layer_preserves_actual_lexical_inference(self):
        self.note('WORK/synthetic-routing/ISA.md', 'Synthetic lab routing', 'Synthetic routing plan')
        for index in range(15):
            self.note(f'WORK/synthetic-padding-{index}/ISA.md', f'Synthetic filler {index}', 'Synthetic filler body')
        self.successful('build', '--all')
        graph = json.loads((self.output / 'graph.json').read_text())
        inferred = [edge for edge in graph['edges'] if edge['kind'] == 'inferred']
        self.assertTrue(inferred, graph)
        (self.fixture.root / 'LIFEOS/USER/CONFIG/memory-access.json').unlink()
        self.successful('build', '--all', context=False)
        native = json.loads((self.output / 'graph.json').read_text())
        native_inferred = [edge for edge in native['edges'] if edge['kind'] == 'inferred']
        def pairs(edges):
            return {tuple(sorted((edge['from'], edge['to']))) for edge in edges}
        self.assertEqual(pairs(inferred), pairs(native_inferred))

    def test_empty_current_corpus_builds_a_native_empty_graph(self):
        self.native.memory.forget(OWNER, self.reference, 'graph-forget-source')
        self.native.memory.forget(OWNER, self.target, 'graph-forget-target')
        self.successful('build')
        graph = json.loads((self.output / 'graph.json').read_text())
        self.assertEqual(graph['nodeCount'], 0)
        self.assertEqual(graph['edgeCount'], 0)
        self.assertEqual(graph['nodes'], [])
        self.assertNotIn('Synthetic current target', self.successful('patterns'))
        with self.native.memory._transaction() as database:
            paths = [self.native.memory._path(row['path']) for row in database.execute('SELECT path FROM records')]
        for path in paths:
            path.unlink()
        (self.fixture.root / 'LIFEOS/USER/CONFIG/memory-access.json').unlink()
        self.successful('build', context=False)
        self.assertEqual(json.loads((self.output / 'graph.json').read_text())['nodes'], [])

    def test_invalid_graph_arguments_refuse_without_exposing_or_publishing_sources(self):
        from lifeos_hook_bridge.memory_service import MemoryService
        service = MemoryService(self.fixture.configuration)
        arguments = {'root': str(self.memory), 'command': 'stats', 'layer': 'declared', 'target': None}
        for changed in ({'root': str(self.native.home)}, {'command': []}, {'layer': {}},
                        {'command': 'related', 'target': None}, {'target': 'unexpected'}):
            with self.subTest(changed=changed):
                result = service.native(self.fixture.context, 'memory_graph', {**arguments, **changed})
                self.assertFalse(result['ok'], result)
                self.assertNotIn('Synthetic current target', str(result))
                self.assertFalse(self.output.exists())

    def test_authority_change_after_real_render_refuses_publication(self):
        self.successful('build')
        before = self.cache()
        process = self.process('authority')
        self.assertEqual(process.returncode, 0, process.stdout)
        response = json.loads(process.stdout)['result']
        self.assertFalse(response['ok'], response)
        self.assertEqual(response['stdout'], '')
        self.assertIn('authority changed during rendering', response['receipt']['reason'])
        self.assertEqual(self.cache(), before)

    def test_interrupted_artifact_pair_recovers_before_fresh_publication(self):
        self.successful('build')
        before = self.cache()
        self.native.memory.forget(OWNER, self.target, 'graph-forget-interrupted')
        process = self.process('interrupt')
        self.assertEqual(process.returncode, 73, process.stdout)
        self.assertTrue(self.native.memory.transaction.journal.is_file())
        self.assertNotEqual((self.output / 'graph.json').read_bytes(), before['graph.json'])
        self.assertEqual((self.output / 'PATTERNS.md').read_bytes(), before['PATTERNS.md'])
        with self.native.memory._transaction():
            pass
        self.assertEqual(self.cache(), before)
        self.assertFalse(self.native.memory.transaction.journal.exists())
        self.assertNotIn('Synthetic current target', self.successful('patterns'))
        self.assertEqual(json.loads((self.output / 'graph.json').read_text())['nodeCount'], 1)
        for path in self.output.iterdir():
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_restricted_context_and_invalid_connector_cannot_use_cache(self):
        self.successful('build')
        before = self.cache()
        self.fixture.configuration.update(lambda config: config['destinations']['chat-a:200'].update(
            read=['project'], projects=['lab']))
        result = self.call('patterns')
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('Synthetic current target', result.stdout + result.stderr)
        self.assertEqual(self.cache(), before)
        (self.fixture.root / 'LIFEOS/USER/CONFIG/memory-access.json').write_text('{invalid')
        result = self.call('patterns')
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('Synthetic current target', result.stdout + result.stderr)
        self.assertEqual(self.cache(), before)
