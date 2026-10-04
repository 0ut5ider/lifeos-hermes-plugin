# ABOUTME: Exercises native TELOS summary parsing with synthetic owner context and source files.
# ABOUTME: Checks source precedence, templates, retirement, authority, and publication boundaries.
from dataclasses import asdict
import os
import json
import re
from pathlib import Path
import subprocess
import sys
import unittest

import test_memory_delegation as delegation
from test_memory_native import OWNER


class MemoryTelosTests(unittest.TestCase):
    def setUp(self):
        self.fixture = delegation.MemoryDelegationTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        self.telos = self.root / 'LIFEOS/USER/TELOS'
        self.telos.mkdir()
        self.output = self.telos / 'PRINCIPAL_TELOS.md'
        self.source = self.note('TELOS.md', '## Mission\n### M0: Synthetic unified mission\n\n'
            '## Goals\n### G0: Synthetic current goal\n\n## Context Filter\nSynthetic owner context filter.\n')
        (self.root / 'LIFEOS/USER/PRINCIPAL/PRINCIPAL_IDENTITY.md').write_text(
            '---\ncore:\n  full_name: SyntheticOperator\n---\n# Principal Identity\n')

    def note(self, name, content):
        path = self.telos / name
        path.write_text(content)
        return path

    def call(self, *, context=True):
        environment = dict(os.environ, HOME=str(self.fixture.fixture.home),
            LIFEOS_DIR=str(self.root / 'LIFEOS'), BUN_CONFIG_NO_AUTO_INSTALL='1')
        environment.pop('LIFEOS_MEMORY_INTERNAL', None)
        environment.pop('LIFEOS_MEMORY_CONTEXT', None)
        if context:
            environment['LIFEOS_MEMORY_CONTEXT'] = json.dumps(asdict(self.fixture.context))
        return subprocess.run(['bun', '--no-install', str(self.root / 'LIFEOS/TOOLS/GenerateTelosSummary.ts')],
            env=environment, capture_output=True, text=True, timeout=30)

    def successful(self, *, context=True):
        result = self.call(context=context)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('TELOS summary regenerated:', result.stderr)
        self.assertNotIn('WARNING', result.stderr)
        self.assertIn('Generated PRINCIPAL_TELOS.md', result.stdout)
        return self.output.read_text()

    def test_native_unified_sections_identity_and_context_filter(self):
        text = self.successful()
        self.assertIn('SyntheticOperator', text)
        self.assertIn('- **M0**: Synthetic unified mission', text)
        self.assertIn('- **G0**: Synthetic current goal', text)
        self.assertIn('Synthetic owner context filter.', text)

    def test_unified_content_wins_and_empty_section_uses_legacy(self):
        self.note('MISSION.md', '- M0: Synthetic legacy mission\n')
        self.note('WISDOM.md', '- Synthetic legacy wisdom\n')
        text = self.successful()
        self.assertIn('Synthetic unified mission', text)
        self.assertNotIn('Synthetic legacy mission', text)
        self.assertIn('Synthetic legacy wisdom', text)

    def test_plural_missions_and_sample_filter_preserve_native_parser(self):
        self.source.write_text('## Missions\n### M0: Synthetic plural mission\n'
            '### M1: Synthetic ignored mission (sample)\n')
        text = self.successful()
        self.assertIn('Synthetic plural mission', text)
        self.assertNotIn('Synthetic ignored mission', text)

    def test_owner_summary_matches_standalone_except_generation_time(self):
        managed = self.successful()
        (self.root / 'LIFEOS/USER/CONFIG/memory-access.json').unlink()
        standalone = self.successful(context=False)
        normalize = lambda text: re.sub(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z', '<generated>', text)
        self.assertEqual(normalize(managed), normalize(standalone))

    def test_missing_context_refuses_before_publication(self):
        self.assertNotEqual(self.call(context=False).returncode, 0)
        self.assertFalse(self.output.exists())

    def test_revocation_preserves_previous_summary(self):
        self.successful()
        before = self.output.read_bytes()
        self.fixture.configuration.update(lambda config: config['accounts'].pop('chat-a:100'))
        self.assertNotEqual(self.call().returncode, 0)
        self.assertEqual(self.output.read_bytes(), before)

    def test_restricted_owner_refuses_before_publication(self):
        self.fixture.configuration.update(lambda config: config['destinations']['chat-a:200'].update(
            read=['project'], write=['project'], projects=['lab']))
        self.assertNotEqual(self.call().returncode, 0)
        self.assertFalse(self.output.exists())

    def test_foreign_source_link_refuses_before_publication(self):
        foreign = self.fixture.fixture.home / 'foreign-telos.md'
        foreign.write_bytes(self.source.read_bytes())
        self.source.unlink(); self.source.symlink_to(foreign)
        self.assertNotEqual(self.call().returncode, 0)
        self.assertFalse(self.output.exists())

    def test_output_link_refuses_without_modifying_foreign_file(self):
        foreign = self.fixture.fixture.home / 'foreign-summary.md'
        foreign.write_text('Synthetic foreign summary')
        self.output.symlink_to(foreign)
        self.assertNotEqual(self.call().returncode, 0)
        self.assertEqual(foreign.read_text(), 'Synthetic foreign summary')

    def test_output_is_private(self):
        self.successful()
        self.assertEqual(self.output.stat().st_mode & 0o777, 0o600)

    def test_forgotten_unified_source_uses_fresh_legacy_without_modifying_source(self):
        memory = self.fixture.fixture.memory
        reference = memory.remember(OWNER, category='principal', content='RULE: Synthetic unified mission',
            title='', project='', request_id='telos-retired')['reference']
        before = self.source.read_bytes()
        memory.forget(OWNER, reference, 'telos-forget')
        self.note('MISSION.md', '- M0: Synthetic current legacy mission\n')
        text = self.successful()
        self.assertNotIn('Synthetic unified mission', text)
        self.assertIn('Synthetic current legacy mission', text)
        self.assertEqual(self.source.read_bytes(), before)

    def process(self, mode):
        result = subprocess.run([sys.executable, str(Path(__file__).with_name('memory_telos_process.py')),
            str(self.fixture.configuration.path), mode], env=dict(os.environ, HOME=str(self.fixture.fixture.home)),
            capture_output=True, text=True, timeout=30)
        self.assertEqual(result.stderr, '')
        return result

    def test_source_change_after_render_refuses_before_summary_publication(self):
        self.successful()
        before = self.output.read_bytes()
        result = self.process('source')
        self.assertEqual(result.returncode, 0)
        self.assertFalse(json.loads(result.stdout)['ok'])
        self.assertEqual(self.output.read_bytes(), before)

    def test_owner_revocation_after_render_refuses_before_summary_publication(self):
        self.successful()
        before = self.output.read_bytes()
        result = self.process('authority')
        self.assertEqual(result.returncode, 0)
        self.assertFalse(json.loads(result.stdout)['ok'])
        self.assertEqual(self.output.read_bytes(), before)

    def test_process_death_restores_previous_summary_before_fresh_render(self):
        self.successful()
        before = self.output.read_bytes()
        self.source.write_text(self.source.read_text().replace('Synthetic unified mission', 'Synthetic revised mission'))
        result = self.process('interrupt')
        self.assertEqual(result.returncode, 73)
        self.assertEqual(result.stdout, '')
        self.assertNotEqual(self.output.read_bytes(), before)
        journal = self.fixture.fixture.memory.transaction.journal
        self.assertTrue(journal.exists())
        with self.fixture.fixture.memory._transaction():
            self.assertEqual(self.output.read_bytes(), before)
        self.assertFalse(journal.exists())
        self.assertIn('Synthetic revised mission', self.successful())

    def test_exact_owner_review_retains_older_valid_summary_sources(self):
        from lifeos_hook_bridge.memory_source_review import preview, approve
        memory = self.fixture.fixture.memory
        reference = memory.remember(OWNER, category='principal', content='RULE: Synthetic unrelated TELOS retirement',
            title='', project='', request_id='telos-review')['reference']
        memory.forget(OWNER, reference, 'telos-review-forget')
        paths = ['LIFEOS/USER/TELOS/TELOS.md', 'LIFEOS/USER/PRINCIPAL/PRINCIPAL_IDENTITY.md']
        plan = preview(memory, OWNER, paths)
        self.assertTrue(all(source['accepted'] for source in plan['sources']))
        self.assertEqual(approve(memory, OWNER, paths, plan['signature'])['status'], 'committed')
        text = self.successful()
        self.assertIn('Synthetic unified mission', text)
        self.assertIn('SyntheticOperator', text)

    def test_missing_admitted_identity_cannot_borrow_raw_settings_name(self):
        (self.root / 'LIFEOS/USER/PRINCIPAL/PRINCIPAL_IDENTITY.md').unlink()
        (self.root / 'settings.json').write_text(json.dumps({'principal': {'name': 'SyntheticUnreviewedSettingsName'}}))
        self.assertNotIn('SyntheticUnreviewedSettingsName', self.successful())
        (self.root / 'LIFEOS/USER/CONFIG/memory-access.json').unlink()
        self.assertIn('SyntheticUnreviewedSettingsName', self.successful(context=False))

    def test_empty_source_preserves_previous_summary(self):
        self.successful()
        before = self.output.read_bytes()
        self.source.write_text('## Mission\n')
        self.assertNotEqual(self.call().returncode, 0)
        self.assertEqual(self.output.read_bytes(), before)

    def test_sample_only_sources_keep_native_empty_template_behavior(self):
        self.source.write_text('## Mission\n### M0: Synthetic template mission (sample)\n')
        result = self.call()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('TELOS sources are still shipped templates', result.stderr)
        self.assertNotIn('Synthetic template mission', self.output.read_text())

    def test_output_alias_to_registry_refuses_before_journal_collection(self):
        memory = self.fixture.fixture.memory
        saved = self.fixture.fixture.remember('Synthetic TELOS registry guard', 'telos-registry')
        os.link(memory.database, self.output)
        self.assertNotEqual(self.call().returncode, 0)
        self.assertEqual(memory.get(OWNER, saved['reference'])['content'], 'Synthetic TELOS registry guard')

    def test_all_native_summary_sections_retain_their_content(self):
        fields = [('Missions', 'M0', 'mission'), ('Goals', 'G0', 'goal'), ('Problems', 'P0', 'problem'),
            ('Strategies', 'S0', 'strategy'), ('Projects', 'PJ0', 'project'), ('Narratives', 'N0', 'narrative'),
            ('Challenges', 'C0', 'challenge'), ('Traumas', 'TR0', 'trauma'), ('Models', 'MD0', 'model')]
        parts = ['## ' + heading + '\n### ' + identifier + ': Synthetic summary ' + marker + '\n'
                 for heading, identifier, marker in fields]
        parts += ['## Wisdom\n- Synthetic summary wisdom\n', '## Wrong\n- Synthetic summary mistake\n']
        self.source.write_text('\n'.join(parts))
        text = self.successful()
        for marker in [field[2] for field in fields] + ['wisdom', 'mistake']:
            with self.subTest(marker=marker):
                self.assertIn('Synthetic summary ' + marker, text)

    def test_owner_read_grant_without_write_cannot_publish_summary(self):
        self.fixture.configuration.update(lambda config: config['destinations']['chat-a:200'].update(write=[]))
        self.assertNotEqual(self.call().returncode, 0)
        self.assertFalse(self.output.exists())

    def test_durable_marker_refuses_connector_loss_after_restart(self):
        (self.root / 'LIFEOS/USER/CONFIG/memory-http.json').write_text('{"version":1,"managed":true}')
        (self.root / 'LIFEOS/USER/CONFIG/memory-access.json').unlink()
        self.assertNotEqual(self.call(context=False).returncode, 0)
        self.assertFalse(self.output.exists())
