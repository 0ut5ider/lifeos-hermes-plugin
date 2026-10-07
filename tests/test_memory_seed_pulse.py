# ABOUTME: Runs the interview SeedPulse command with real governed generator children.
# ABOUTME: Verifies parent context, custom roots, refusal, and selected native effects.
from dataclasses import asdict
import json
import os
from pathlib import Path
import subprocess
import unittest

import test_memory_native as native_fixture
import test_memory_telos as telos_fixture


class MemorySeedPulseTests(unittest.TestCase):
    def setUp(self):
        self.fixture = telos_fixture.MemoryTelosTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        self.summary = self.fixture.output
        self.state = self.fixture.telos / 'LIFEOS_STATE.json'
        dimension = self.fixture.telos / 'CURRENT_STATE/HEALTH.md'
        dimension.parent.mkdir()
        dimension.write_text('---\nlast_updated: 2026-10-04\n---\nstatus: have\nstatus: partial\nstatus: missing\n')
        self.events = []

    def call(self, *arguments, context=True):
        owner = self.fixture.fixture
        env = {**os.environ, 'HOME': str(owner.fixture.home), 'BUN_CONFIG_NO_AUTO_INSTALL': '1'}
        for key in ('LIFEOS_MEMORY_INTERNAL', 'LIFEOS_MEMORY_CONTEXT', 'LIFEOS_DIR', 'LIFEOS_CONFIG_DIR',
                    'LIFEOS_CONFIG_PATH', 'CLAUDE_CONFIG_DIR'):
            env.pop(key, None)
        if context:
            env['LIFEOS_MEMORY_CONTEXT'] = json.dumps(asdict(owner.context))
        source = native_fixture.SOURCE / 'skills/LifeOS/Tools/SeedPulse.ts'
        result = subprocess.run(['bun', '--no-install', str(source), *arguments], env=env,
            capture_output=True, text=True, timeout=60)
        self.events.append({'command': result.args, 'status': result.returncode,
                            'stdout': result.stdout, 'stderr': result.stderr})
        self.assertEqual(result.stderr, '')
        return result, json.loads(result.stdout)

    def test_owner_parent_runs_both_governed_children(self):
        result, outcome = self.call('--apply')
        self.assertEqual(result.returncode, 0, outcome)
        self.assertTrue(outcome['ok'], outcome)
        self.assertEqual(outcome['ran'], ['GenerateTelosSummary.ts', 'UpdateLifeosState.ts'])
        self.assertEqual(outcome['failed'], [])
        self.assertIn('Synthetic unified mission', self.summary.read_text())
        self.assertEqual(json.loads(self.state.read_text())['dimensions']['health']['pct'], 50)
        self.assertEqual(self.summary.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.state.stat().st_mode & 0o777, 0o600)

    def test_dry_parent_reports_generators_without_publication(self):
        result, outcome = self.call()
        self.assertEqual(result.returncode, 0, outcome)
        self.assertTrue(outcome['dryRun'])
        self.assertEqual(outcome['willRun'], ['GenerateTelosSummary.ts', 'UpdateLifeosState.ts'])
        self.assertFalse(self.summary.exists())
        self.assertFalse(self.state.exists())

    def test_missing_context_refuses_both_children(self):
        result, outcome = self.call('--apply', context=False)
        self.assertEqual(result.returncode, 1, outcome)
        self.assertFalse(outcome['ok'])
        self.assertFalse(outcome['written'])
        self.assertEqual(outcome['ran'], [])
        self.assertEqual([entry['tool'] for entry in outcome['failed']], ['GenerateTelosSummary.ts', 'UpdateLifeosState.ts'])
        self.assertFalse(self.summary.exists())
        self.assertFalse(self.state.exists())

    def test_revoked_parent_preserves_both_previous_artifacts(self):
        self.test_owner_parent_runs_both_governed_children()
        before = self.summary.read_bytes(), self.state.read_bytes()
        self.fixture.fixture.configuration.update(lambda value: value['accounts'].pop('chat-a:100'))
        result, outcome = self.call('--apply')
        self.assertEqual(result.returncode, 1, outcome)
        self.assertFalse(outcome['written'])
        self.assertEqual((self.summary.read_bytes(), self.state.read_bytes()), before)

    def test_restricted_parent_cannot_seed_global_derivatives(self):
        self.fixture.fixture.configuration.update(lambda value: value['destinations']['chat-a:200'].update(
            read=['project'], write=['project'], projects=['lab']))
        result, outcome = self.call('--apply')
        self.assertEqual(result.returncode, 1, outcome)
        self.assertFalse(outcome['written'])
        self.assertFalse(self.summary.exists())
        self.assertFalse(self.state.exists())

    def test_explicit_installed_alias_keeps_the_governed_root(self):
        alias = self.root.parent / 'custom-profile'
        alias.symlink_to(self.root, target_is_directory=True)
        result, outcome = self.call('--config-root', str(alias), '--config-dir', str(self.root.parent / '.config/LIFEOS'), '--apply')
        self.assertEqual(result.returncode, 0, outcome)
        self.assertTrue(outcome['ok'])
        self.assertIn('Synthetic unified mission', self.summary.read_text())
        self.assertEqual(json.loads(self.state.read_text())['dimensions']['health']['pct'], 50)

    def test_empty_runtime_reports_missing_generators_without_publication(self):
        empty = self.root.parent / 'empty-profile'
        empty.mkdir()
        for arguments in ((), ('--apply',)):
            with self.subTest(arguments=arguments):
                result, outcome = self.call('--config-root', str(empty), *arguments)
                self.assertEqual(result.returncode, 1, outcome)
                self.assertFalse(outcome['ok'])
                self.assertEqual(outcome['missing'], ['GenerateTelosSummary.ts', 'UpdateLifeosState.ts'])
        self.assertFalse(self.summary.exists())
        self.assertFalse(self.state.exists())
