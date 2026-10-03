# ABOUTME: Tests native prompt context permissions and cache lifetime in real Bun processes.
# ABOUTME: Uses isolated identity, hot facts, policy changes, and native source redirects.
from dataclasses import asdict
import json
import os
from pathlib import Path
import select
import subprocess
import unittest

import test_memory_delegation as delegation_fixture
from test_memory_native import SOURCE, OWNER


class MemoryContextBuilderTests(unittest.TestCase):
    def setUp(self):
        self.fixture = delegation_fixture.MemoryDelegationTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        (self.root / 'LIFEOS/PULSE').symlink_to(SOURCE / 'LIFEOS/PULSE')
        self.sources = {
            'DIGITAL_ASSISTANT/DA_IDENTITY.md': 'Synthetic assistant identity marker',
            'PRINCIPAL/PRINCIPAL_IDENTITY.md': 'Synthetic private principal identity marker',
            'TELOS/PRINCIPAL_TELOS.md': 'Synthetic principal goal marker',
            'PROJECTS.md': '# Projects\nRouting details are omitted.\n## Open Sessions to Resume\nSynthetic active session marker',
        }
        for relative, content in self.sources.items():
            path = self.root / 'LIFEOS/USER' / relative
            path.parent.mkdir(exist_ok=True)
            path.write_text(content + '\n')
        self.fixture.fixture.remember('RULE: Synthetic context hot fact', 'context-hot', 'principal')
        environment = dict(os.environ, HOME=str(self.fixture.fixture.home), BUN_CONFIG_NO_AUTO_INSTALL='1')
        for name in ('LIFEOS_MEMORY_INTERNAL', 'LIFEOS_MEMORY_CONTEXT', 'LIFEOS_CONFIG_PATH'):
            environment.pop(name, None)
        self.environment = environment
        self.process = None

    def start(self):
        self.process = subprocess.Popen(['bun', '--no-install', str(Path(__file__).with_name('native_memory_context.ts')),
            str(self.root / 'LIFEOS/PULSE/lib/lifeos-context.ts')],
            env=self.environment, cwd=self.root, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True)
        self.addCleanup(self.stop)

    def stop(self):
        if self.process is None:
            return
        self.process.stdin.close()
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait()
        errors = self.process.stderr.read()
        self.process.stdout.close()
        self.process.stderr.close()
        self.assertEqual(self.process.returncode, 0, errors)
        self.assertEqual(errors, '')

    def call(self, *, context=True, query=None, probe=False):
        if self.process is None:
            self.start()
        request = {'context': asdict(self.fixture.context) if context else None, 'query': query, 'probe': probe}
        self.process.stdin.write(json.dumps(request) + '\n')
        self.process.stdin.flush()
        readable, _, _ = select.select([self.process.stdout], [], [], 45)
        self.assertTrue(readable, 'The native context builder did not return within 45 seconds')
        line = self.process.stdout.readline()
        self.assertTrue(line, 'The native context process closed its output')
        return json.loads(line)

    def deny(self, result):
        self.assertIn('error', result, result)
        self.assertNotIn('identity marker', json.dumps(result))
        self.assertNotIn('context hot fact', json.dumps(result))

    def names(self, principal, assistant='LifeOS'):
        (self.root / 'LIFEOS/USER/CONFIG/LIFEOS_CONFIG.toml').write_text(
            '[principal]\nname=' + json.dumps(principal) + '\ntimezone="UTC"\n'
            '[da]\nname=' + json.dumps(assistant) + '\n[da.voices.main]\nvoice_id="synthetic"\n')
        self.environment['LIFEOS_MEMORY_CONTEXT'] = json.dumps(asdict(self.fixture.context))

    def test_standalone_builder_keeps_identity_memory_order_and_active_session_slice(self):
        (self.root / 'LIFEOS/USER/CONFIG/memory-access.json').unlink()
        result = self.call(context=False)
        block = result['block']
        self.assertIn('Synthetic private principal identity marker', block)
        self.assertIn('Synthetic context hot fact', block)
        self.assertIn('Synthetic active session marker', block)
        self.assertNotIn('Routing details are omitted', block)
        self.assertLess(block.index('identity marker'), block.index('context hot fact'))
        self.assertLess(block.index('context hot fact'), block.index('principal goal marker'))

    def test_native_subprocess_receives_the_current_context_after_import(self):
        self.assertTrue(self.call(probe=True)['access'])
        self.assertFalse(self.call(context=False, probe=True)['access'])
        self.assertTrue(self.call(probe=True)['access'])

    def test_native_subprocess_does_not_retain_its_initial_owner_context(self):
        self.environment['LIFEOS_MEMORY_CONTEXT'] = json.dumps(asdict(self.fixture.context))
        self.assertTrue(self.call(probe=True)['access'])
        self.assertFalse(self.call(context=False, probe=True)['access'])

    def test_managed_owner_keeps_identity_goals_sessions_and_current_memory(self):
        block = self.call(query='Synthetic context hot fact')['block']
        for marker in ('assistant identity marker', 'principal identity marker', 'principal goal marker',
                       'active session marker', 'context hot fact'):
            self.assertIn(marker, block)

    def test_missing_context_cannot_read_identity_sources(self):
        self.deny(self.call(context=False, query='Synthetic context hot fact'))

    def test_cached_owner_block_is_not_reused_after_context_is_removed(self):
        self.assertIn('context hot fact', self.call()['block'])
        self.deny(self.call(context=False))

    def test_cached_owner_block_is_not_reused_after_policy_revocation(self):
        self.assertIn('context hot fact', self.call()['block'])
        configuration = self.fixture.configuration.load()
        configuration['accounts'] = {}
        self.fixture.configuration.save(configuration)
        self.deny(self.call())

    def test_project_only_caller_cannot_collect_unclassified_identity(self):
        configuration = self.fixture.configuration.load()
        configuration['destinations']['chat-a:200'].update(read=['project'], projects=['lab'])
        self.fixture.configuration.save(configuration)
        self.deny(self.call())

    def test_connector_loss_cannot_select_raw_reader_or_cached_owner_block(self):
        self.assertIn('context hot fact', self.call()['block'])
        (self.root / 'LIFEOS/USER/CONFIG/memory-access.json').unlink()
        self.deny(self.call())

    def test_invalid_connector_refuses_before_identity_collection(self):
        (self.root / 'LIFEOS/USER/CONFIG/memory-access.json').write_text('{invalid')
        self.deny(self.call())

    def test_updated_native_identity_is_visible_on_the_next_managed_call(self):
        self.assertIn('principal goal marker', self.call()['block'])
        target = self.root / 'LIFEOS/USER/TELOS/PRINCIPAL_TELOS.md'
        target.write_text('Synthetic updated current goal marker\n')
        self.assertIn('updated current goal marker', self.call()['block'])

    def test_identity_source_cannot_follow_a_redirect_into_configuration(self):
        target = self.root / 'LIFEOS/USER/PRINCIPAL/PRINCIPAL_IDENTITY.md'
        target.unlink()
        secret = self.root / 'LIFEOS/USER/CONFIG/synthetic-secret.md'
        secret.write_text('SYNTHETIC_CONFIGURATION_ONLY_MARKER\n')
        target.symlink_to(secret)
        result = self.call()
        self.assertNotIn('SYNTHETIC_CONFIGURATION_ONLY_MARKER', json.dumps(result))
        self.assertIn('PRINCIPAL_IDENTITY unavailable on disk', result['block'])

    def test_forgotten_claims_in_identity_and_cached_hot_memory_stay_excluded(self):
        saved = self.fixture.fixture.memory.recall(OWNER, 'Synthetic context hot fact')[0]
        target = self.root / 'LIFEOS/USER/PRINCIPAL/PRINCIPAL_IDENTITY.md'
        target.write_text('Synthetic private principal identity marker\nRULE: Synthetic context hot fact\n')
        self.assertIn('context hot fact', self.call()['block'])
        self.fixture.fixture.memory.forget(OWNER, saved['reference'], 'forget-context')
        result = self.call()
        self.assertNotIn('context hot fact', result['block'])

    def test_private_markup_in_identity_is_excluded_from_the_owner_block(self):
        (self.root / 'LIFEOS/USER/PRINCIPAL/PRINCIPAL_IDENTITY.md').write_text(
            '<private>SYNTHETIC_CONTEXT_PRIVATE_MARKER</private>\n')
        result = self.call()
        self.assertNotIn('SYNTHETIC_CONTEXT_PRIVATE_MARKER', json.dumps(result))

    def test_owner_display_names_do_not_carry_private_markup(self):
        self.names('<private>SYNTHETIC_PRIVATE_NAME</private>', 'Synthetic assistant')
        result = self.call()
        self.assertNotIn('SYNTHETIC_PRIVATE_NAME', json.dumps(result))
        self.assertIn('Synthetic assistant', result['block'])

    def test_managed_display_names_are_refreshed_without_reusing_a_retired_label(self):
        self.names('SyntheticCurrentDisplayName')
        self.assertIn('SyntheticCurrentDisplayName', self.call()['block'])
        self.names('SyntheticUpdatedDisplayName')
        result = self.call()
        self.assertIn('SyntheticUpdatedDisplayName', result['block'])
        self.assertNotIn('SyntheticCurrentDisplayName', result['block'])

    def test_oversized_identity_source_is_unavailable_instead_of_entering_context(self):
        marker = 'SYNTHETIC_OVERSIZED_IDENTITY'
        (self.root / 'LIFEOS/USER/PRINCIPAL/PRINCIPAL_IDENTITY.md').write_text(marker + ' ' * (256 * 1024))
        result = self.call()
        self.assertNotIn(marker, result['block'])
        self.assertIn('PRINCIPAL_IDENTITY unavailable on disk', result['block'])

    def test_retired_display_name_is_not_reused_from_native_configuration(self):
        marker = 'SyntheticRetiredDisplayName'
        self.names(marker)
        saved = self.fixture.fixture.remember('RULE: ' + marker, 'display-name', 'principal')
        self.assertIn(marker, self.call()['block'])
        self.fixture.fixture.memory.forget(OWNER, saved['reference'], 'forget-name')
        self.assertNotIn(marker, json.dumps(self.call()))


if __name__ == '__main__':
    unittest.main()
