# ABOUTME: Verifies grouped interview seeding through native calculations and publication recovery.
# ABOUTME: Checks real parent failure, source changes, and process exit between the two artifacts.
from dataclasses import asdict
import json
import os
from pathlib import Path
import subprocess
import sys
import shutil
import re
import unittest

from lifeos_hook_bridge.memory_service import MemoryService
from lifeos_hook_bridge.memory_access import MemoryUnavailable
import test_memory_seed_pulse as seed_fixture


class MemorySeedRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.fixture = seed_fixture.MemorySeedPulseTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        self.memory = self.fixture.fixture.fixture.fixture.memory
        self.configuration = self.fixture.fixture.fixture.configuration
        self.context = self.fixture.fixture.fixture.context
        self.fixture.summary.write_text('# Synthetic previous interview summary\n')
        self.fixture.state.write_text('{"synthetic_previous_state": true}\n')
        self.original = {str(path): path.read_bytes() for path in (self.fixture.summary, self.fixture.state)}
        self.outcomes = []

    def call(self, **arguments):
        result = MemoryService(self.configuration).native(self.context, 'seed_pulse', {
            'root': str(self.root), 'config_dir': str(self.root.parent / '.config/LIFEOS'),
            'generators': ['GenerateTelosSummary.ts', 'UpdateLifeosState.ts'], **arguments})
        self.outcomes.append(result)
        return result

    def tearDown(self):
        directory = os.environ.get('LIFEOS_SEED_EVIDENCE_DIR')
        if directory:
            path = Path(directory)
            path.mkdir(parents=True, exist_ok=True)
            artifacts = {str(target): {'content': target.read_text(), 'mode': target.stat().st_mode & 0o777}
                for target in (self.fixture.summary, self.fixture.state)}
            (path / (self._testMethodName + '.json')).write_text(json.dumps({'events': self.fixture.events,
                'outcomes': self.outcomes, 'artifacts': artifacts}, indent=2) + '\n')

    def test_native_parent_preserves_both_artifacts_when_the_second_generator_fails(self):
        tools = self.root / 'LIFEOS/TOOLS'
        source = tools.resolve()
        tools.unlink()
        shutil.copytree(source, tools, symlinks=True, ignore=shutil.ignore_patterns('node_modules'))
        (tools / 'node_modules').symlink_to(source / 'node_modules', target_is_directory=True)
        path = self.root / 'LIFEOS/TOOLS/UpdateLifeosState.ts'
        path.write_text('// ABOUTME: Represents an unavailable synthetic generator.\n'
            '// ABOUTME: Throws before any native state calculation or publication.\n'
            'throw new Error("Synthetic second generator failure");\n')
        result, outcome = self.fixture.call('--apply')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(outcome['ok'])
        self.assertFalse(outcome['written'])
        self.assertEqual({name: Path(name).read_bytes() for name in self.original}, self.original)

    def test_grouped_seed_runs_both_native_calculations_with_private_artifacts(self):
        result = self.call()
        self.assertTrue(result['ok'], result)
        self.assertIn('Synthetic unified mission', self.fixture.summary.read_text())
        self.assertEqual(json.loads(self.fixture.state.read_text())['dimensions']['health']['pct'], 50)
        for path in (self.fixture.summary, self.fixture.state):
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_process_exit_after_first_artifact_restores_both_before_a_fresh_seed(self):
        settings = {'configuration': str(self.configuration.path), 'context': asdict(self.context),
            'root': str(self.root), 'summary': str(self.fixture.summary)}
        code = '''import json,os,sys
from pathlib import Path
from lifeos_hook_bridge.memory_policy import SessionContext
from lifeos_hook_bridge.memory_service import MemoryConfiguration,MemoryService
settings=json.loads(sys.stdin.read())
def trace(frame,event,argument):
    if event == 'return' and frame.f_code.co_name == 'publish' and frame.f_locals.get('path') == Path(settings['summary']):
        os._exit(73)
    return trace
sys.settrace(trace)
result=MemoryService(MemoryConfiguration(Path(settings['configuration']))).native(SessionContext(**settings['context']),'seed_pulse',
    {'root':settings['root'],'config_dir':str(Path(settings['root']).parent/'.config/LIFEOS'),
     'generators':['GenerateTelosSummary.ts','UpdateLifeosState.ts']})
print(json.dumps(result))
'''
        child = subprocess.run([sys.executable, '-c', code], input=json.dumps(settings), text=True,
            capture_output=True, env=os.environ.copy(), timeout=30)
        self.assertEqual(child.returncode, 73, child.stdout + child.stderr)
        self.assertEqual(child.stdout + child.stderr, '')
        with self.memory._transaction():
            pass
        self.assertEqual({name: Path(name).read_bytes() for name in self.original}, self.original)
        self.assertTrue(self.call()['ok'])

    def test_managed_parent_retains_native_parent_outcomes_and_artifact_bytes(self):
        result, managed = self.fixture.call('--apply')
        self.assertEqual(result.returncode, 0, managed)
        summary, state = self.fixture.summary.read_text(), json.loads(self.fixture.state.read_text())
        (self.root / 'LIFEOS/USER/CONFIG/memory-access.json').unlink()
        result, original = self.fixture.call('--apply', context=False)
        self.assertEqual(result.returncode, 0, original)
        self.assertEqual(managed, original)
        normalize = lambda text: re.sub(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z', '<generated>', text)
        self.assertEqual(normalize(summary), normalize(self.fixture.summary.read_text()))
        current_state = json.loads(self.fixture.state.read_text())
        state.pop('generated_at'); current_state.pop('generated_at')
        self.assertEqual(state, current_state)

    def test_source_or_authority_changes_after_actual_render_preserve_both_artifacts(self):
        for kind in ('source', 'authority'):
            with self.subTest(kind=kind):
                changed = False
                source = self.fixture.fixture.source
                original = source.read_bytes()
                config = self.configuration.load()
                def trace(frame, event, argument):
                    nonlocal changed
                    if (not changed and event == 'return' and frame.f_code.co_name == '_native'
                            and frame.f_locals.get('action') == 'lifeos_state'):
                        changed = True
                        if kind == 'source':
                            source.write_bytes(original + b'\n## Wisdom\n- Synthetic later source\n')
                        else:
                            self.configuration.update(lambda value: value['accounts'].pop('chat-a:100'))
                    return trace
                sys.settrace(trace)
                try:
                    self.assertFalse(self.call()['ok'])
                finally:
                    sys.settrace(None)
                self.assertTrue(changed)
                self.assertEqual({name: Path(name).read_bytes() for name in self.original}, self.original)
                source.write_bytes(original)
                self.configuration.update(lambda value: (value.clear(), value.update(config)))

    def test_later_destination_edit_between_publications_refuses_recovery_without_overwriting_it(self):
        changed = False
        def trace(frame, event, argument):
            nonlocal changed
            if (not changed and event == 'return' and frame.f_code.co_name == 'publish'
                    and frame.f_locals.get('path') == self.fixture.summary):
                changed = True
                self.fixture.state.write_text('{"synthetic_later_owner_edit": true}\n')
            return trace
        sys.settrace(trace)
        try:
            result = self.call()
        finally:
            sys.settrace(None)
        self.assertTrue(changed)
        self.assertFalse(result['ok'])
        self.assertEqual(result['receipt']['status'], 'unknown')
        before = self.fixture.summary.read_bytes(), self.fixture.state.read_bytes()
        with self.assertRaisesRegex(MemoryUnavailable, 'later'):
            with self.memory._transaction():
                pass
        self.assertEqual((self.fixture.summary.read_bytes(), self.fixture.state.read_bytes()), before)
        self.assertTrue(self.memory.transaction.journal.exists())

    def test_selected_generator_subset_and_retry_preserve_actual_publication_receipts(self):
        first = self.call(generators=['GenerateTelosSummary.ts'], request_id='synthetic-seed-retry')
        self.assertTrue(first['ok'], first)
        self.assertEqual(self.fixture.state.read_bytes(), self.original[str(self.fixture.state)])
        before = self.fixture.summary.read_bytes()
        self.assertEqual(self.call(generators=['GenerateTelosSummary.ts'], request_id='synthetic-seed-retry'), first)
        self.assertEqual(self.fixture.summary.read_bytes(), before)
        self.assertFalse(self.call(generators=['UpdateLifeosState.ts'], request_id='synthetic-seed-retry')['ok'])
        self.assertEqual(self.fixture.state.read_bytes(), self.original[str(self.fixture.state)])

    def test_physical_installed_root_alias_keeps_the_same_native_seed_destination(self):
        alias = self.root.parent / 'seed-installed-alias'
        alias.symlink_to(self.root, target_is_directory=True)
        self.configuration.update(lambda value: value.update(root=str(alias)))
        result = self.call(root=str(alias))
        self.assertTrue(result['ok'], result)
        self.assertIn('Synthetic unified mission', self.fixture.summary.read_text())

    def test_invalid_retry_identity_refuses_without_any_publication(self):
        for request_id in (0, False, [], {}, '', 'x' * 257):
            with self.subTest(request_id=request_id):
                self.assertFalse(self.call(request_id=request_id)['ok'])
                self.assertEqual({name: Path(name).read_bytes() for name in self.original}, self.original)


if __name__ == '__main__':
    unittest.main()
