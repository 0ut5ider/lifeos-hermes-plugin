# ABOUTME: Exercises native proposal cleanup under current owner memory permissions.
# ABOUTME: Checks cleanup compatibility and refused writes in isolated physical source trees.
from dataclasses import asdict
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unittest

import test_memory_delegation as delegation
from test_memory_native import OWNER


class MemoryProposalGCTests(unittest.TestCase):
    def setUp(self):
        self.fixture = delegation.MemoryDelegationTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        tools = self.root / 'LIFEOS/TOOLS'
        source = tools.resolve()
        tools.unlink()
        shutil.copytree(source, tools)
        modules = source.parent.parent / 'node_modules'
        if modules.exists():
            (self.root / 'node_modules').symlink_to(modules)
        self.target = self.root / 'LIFEOS/USER/CONFIG/OPERATIONAL_RULES.md'
        self.target.write_text('---\nprovenance: template\nlast_updated: 2000-01-01\n---\n'
            '# Synthetic rules\n\n## Memory-System Proposals\n'
            '- Synthetic private cleanup marker [SUPERSEDED]\n'
            '- Keep the distinct synthetic rule.\n'
            '- Keep the distinct synthetic rule. <!-- applied: 2026-10-07 -->\n')

    def call(self, *flags, context=True):
        environment = dict(os.environ, HOME=str(self.fixture.fixture.home), BUN_CONFIG_NO_AUTO_INSTALL='1')
        environment.pop('LIFEOS_MEMORY_INTERNAL', None)
        environment.pop('LIFEOS_MEMORY_CONTEXT', None)
        if context:
            environment['LIFEOS_MEMORY_CONTEXT'] = json.dumps(asdict(self.fixture.context))
        return subprocess.run(['bun', '--no-install', str(self.root / 'LIFEOS/TOOLS/ProposalGC.ts'), *flags],
            env=environment, capture_output=True, text=True, timeout=40)

    def test_unmanaged_cleanup_keeps_the_newest_duplicate_and_distinct_rule(self):
        (self.root / 'LIFEOS/USER/CONFIG/memory-access.json').unlink()
        result = self.call('--apply', '--json', context=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        report, _ = json.JSONDecoder().raw_decode(result.stdout)
        self.assertEqual([row['reason'] for row in report['removals']], ['superseded', 'exact-dup'])
        text = self.target.read_text()
        self.assertNotIn('Synthetic private cleanup marker', text)
        self.assertEqual(text.count('Keep the distinct synthetic rule.'), 1)
        self.assertIn('applied: 2026-10-07', text)

    def test_unmanaged_auto_skips_a_file_above_the_removal_ceiling(self):
        (self.root / 'LIFEOS/USER/CONFIG/memory-access.json').unlink()
        self.target.write_text('## Memory-System Proposals\n' + '- Synthetic [SUPERSEDED]\n' * 21)
        before = self.target.read_bytes()
        result = self.call('--auto', '--json', context=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        report, _ = json.JSONDecoder().raw_decode(result.stdout)
        self.assertEqual(report['skipped'][0]['count'], 21)
        self.assertEqual(self.target.read_bytes(), before)

    def test_missing_context_refuses_read_and_write(self):
        before = self.target.read_bytes()
        result = self.call('--apply', '--json', context=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('Synthetic private cleanup marker', result.stdout)
        self.assertEqual(self.target.read_bytes(), before)

    def test_revoked_owner_refuses_cleanup(self):
        self.fixture.configuration.update(lambda value: value['accounts'].pop('chat-a:100'))
        before = self.target.read_bytes()
        result = self.call('--apply', '--json')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.target.read_bytes(), before)

    def test_restricted_write_grant_refuses_cleanup(self):
        self.fixture.configuration.update(lambda value: value['destinations']['chat-a:200'].update(write=['project']))
        before = self.target.read_bytes()
        result = self.call('--apply', '--json')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.target.read_bytes(), before)

    def test_managed_cleanup_is_private_and_idempotent(self):
        result = self.call('--apply', '--json')
        self.assertEqual(result.returncode, 0, result.stderr)
        report, _ = json.JSONDecoder().raw_decode(result.stdout)
        self.assertEqual(len(report['removals']), 2)
        self.assertEqual(self.target.stat().st_mode & 0o777, 0o600)
        self.assertIn('provenance: customized', self.target.read_text())
        again = self.call('--auto', '--json')
        self.assertEqual(again.returncode, 0, again.stderr)
        self.assertEqual(json.loads(again.stdout)['removals'], [])

    def test_managed_dry_run_preserves_bytes(self):
        before = self.target.read_bytes()
        result = self.call('--json')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout.split('\n\n')[0])['dryRun'], True)
        self.assertEqual(self.target.read_bytes(), before)

    def test_managed_route_reports_a_current_project_without_writing(self):
        projects = self.root / 'LIFEOS/USER/PROJECTS.md'
        projects.write_text('| **SyntheticLab** | Active |\n')
        self.target.write_text('## Memory-System Proposals\n- SyntheticLab requires its synthetic port.\n')
        before = self.target.read_bytes()
        result = self.call('--route', '--json')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['routes'][0]['dest'], 'SyntheticLab')
        self.assertEqual(self.target.read_bytes(), before)

    def process(self, mode):
        return subprocess.run([sys.executable, str(Path(__file__).with_name('memory_proposal_gc_process.py')),
            str(self.fixture.configuration.path), mode], env=dict(os.environ, HOME=str(self.fixture.fixture.home),
                PYTHONPATH=str(Path(__file__).resolve().parents[1])),
            capture_output=True, text=True, timeout=40)

    def test_owner_revocation_after_native_render_preserves_bytes(self):
        before = self.target.read_bytes()
        result = self.process('authority')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(json.loads(result.stdout)['ok'])
        self.assertEqual(self.target.read_bytes(), before)

    def test_concurrent_source_edit_after_native_render_is_preserved(self):
        before = self.target.read_bytes()
        result = self.process('source')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(json.loads(result.stdout)['ok'])
        self.assertEqual(self.target.read_bytes(), before + b'\n- Synthetic concurrent owner edit.\n')

    def test_process_death_recovers_previous_file_and_allows_fresh_cleanup(self):
        before = self.target.read_bytes()
        result = self.process('interrupt')
        self.assertEqual(result.returncode, 73, result.stderr)
        self.assertNotEqual(self.target.read_bytes(), before)
        memory = self.fixture.fixture.memory
        self.assertTrue(memory.transaction.journal.exists())
        with memory._transaction():
            self.assertEqual(self.target.read_bytes(), before)
        self.assertFalse(memory.transaction.journal.exists())
        self.assertEqual(self.call('--apply', '--json').returncode, 0)

    def test_foreign_target_link_refuses_without_modifying_the_foreign_file(self):
        foreign = self.fixture.fixture.home / 'foreign-proposals.md'
        foreign.write_bytes(self.target.read_bytes())
        self.target.unlink()
        self.target.symlink_to(foreign)
        before = foreign.read_bytes()
        result = self.call('--apply', '--json')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(foreign.read_bytes(), before)

    def test_hard_link_target_refuses_without_modifying_an_alias(self):
        alias = self.fixture.fixture.home / 'linked-proposals.md'
        os.link(self.target, alias)
        before = alias.read_bytes()
        result = self.call('--apply', '--json')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(alias.read_bytes(), before)

    def test_forgotten_source_content_refuses_cleanup_and_delivery(self):
        memory = self.fixture.fixture.memory
        saved = memory.remember(OWNER, category='principal', content='RULE: Synthetic private cleanup marker',
            title='', project='', request_id='gc-retired-marker')
        memory.forget(OWNER, saved['reference'], 'gc-forget-marker')
        before = self.target.read_bytes()
        result = self.call('--apply', '--json')
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('Synthetic private cleanup marker', result.stdout)
        self.assertEqual(self.target.read_bytes(), before)

    def test_missing_context_auto_preserves_native_fail_silent_behavior(self):
        before = self.target.read_bytes()
        result = self.call('--auto', '--json', context=False)
        self.assertEqual(result.returncode, 0)
        self.assertIn('unavailable under the current memory policy', result.stderr)
        self.assertNotIn('Synthetic private cleanup marker', result.stdout)
        self.assertEqual(self.target.read_bytes(), before)
