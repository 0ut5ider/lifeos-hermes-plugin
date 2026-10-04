# ABOUTME: Runs the native TELOS state writer against synthetic admitted dimension sources.
# ABOUTME: Checks percentage semantics, authority, retirement, paths, and publication boundaries.
from dataclasses import asdict
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

import test_memory_delegation as delegation
from test_memory_native import OWNER


class MemoryStateTests(unittest.TestCase):
    def setUp(self):
        self.fixture = delegation.MemoryDelegationTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        self.telos = self.root / 'LIFEOS/USER/TELOS'
        self.telos.mkdir()
        self.output = self.telos / 'LIFEOS_STATE.json'
        self.note('CURRENT_STATE/HEALTH.md', 'status: have\nstatus: partial\nstatus: missing')
        self.note('IDEAL_STATE/MONEY.md', 'Synthetic money target TBD TBD')

    def note(self, relative, body):
        path = self.telos / relative
        path.parent.mkdir(exist_ok=True)
        path.write_text('---\nlast_updated: 2026-10-04\n---\n' + body + '\n')
        return path

    def call(self, *arguments, context=True):
        environment = dict(os.environ, HOME=str(self.fixture.fixture.home),
            LIFEOS_DIR=str(self.root / 'LIFEOS'), BUN_CONFIG_NO_AUTO_INSTALL='1')
        environment.pop('LIFEOS_MEMORY_INTERNAL', None)
        environment.pop('LIFEOS_MEMORY_CONTEXT', None)
        if context:
            environment['LIFEOS_MEMORY_CONTEXT'] = json.dumps(asdict(self.fixture.context))
        return subprocess.run(['bun', '--no-install', str(self.root / 'LIFEOS/TOOLS/UpdateLifeosState.ts'),
            *arguments], env=environment, capture_output=True, text=True, timeout=30)

    def successful(self, *arguments, context=True):
        result = self.call(*arguments, context=context)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        return result

    def test_native_percentage_and_missing_dimension_semantics(self):
        body = json.loads(self.successful('--json').stdout)
        self.assertEqual(body['dimensions']['health'], {'pct': 50, 'tbd_count': 1,
            'last_updated': '2026-10-04', 'source_file': 'CURRENT_STATE/HEALTH.md'})
        self.assertEqual(body['dimensions']['money']['pct'], 80)
        self.assertEqual(body['dimensions']['money']['tbd_count'], 2)
        self.assertEqual(body['dimensions']['freedom'], {'pct': None, 'tbd_count': 0,
            'last_updated': None, 'source_file': 'FREEDOM.md'})
        self.assertEqual(json.loads(self.output.read_text()), body)

    def test_owner_output_matches_standalone_current_and_ideal_fallback(self):
        managed = json.loads(self.successful('--json').stdout)
        (self.root / 'LIFEOS/USER/CONFIG/memory-access.json').unlink()
        standalone = json.loads(self.successful('--json', context=False).stdout)
        managed.pop('generated_at'); standalone.pop('generated_at')
        self.assertEqual(managed, standalone)

    def test_owner_console_report_matches_standalone(self):
        managed = self.successful().stdout
        (self.root / 'LIFEOS/USER/CONFIG/memory-access.json').unlink()
        self.assertEqual(self.successful(context=False).stdout, managed)

    def test_missing_context_refuses_before_output_publication(self):
        result = self.call('--json', context=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.output.exists())

    def test_revocation_preserves_previous_output(self):
        self.successful()
        before = self.output.read_bytes()
        self.fixture.configuration.update(lambda config: config['accounts'].pop('chat-a:100'))
        result = self.call('--json')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.output.read_bytes(), before)

    def test_restricted_owner_refuses_before_publication(self):
        self.fixture.configuration.update(lambda config: config['destinations']['chat-a:200'].update(
            read=['project'], write=['project'], projects=['lab']))
        result = self.call('--json')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.output.exists())

    def test_retired_source_falls_back_without_reading_retained_claim(self):
        reference = self.fixture.fixture.memory.remember(OWNER, category='principal',
            content='RULE: Synthetic retired state claim', title='', project='',
            request_id='state-retired')['reference']
        path = self.note('CURRENT_STATE/HEALTH.md', 'Synthetic retired state claim\nstatus: have')
        before = path.read_bytes()
        self.fixture.fixture.memory.forget(OWNER, reference, 'state-forget')
        self.note('IDEAL_STATE/HEALTH.md', 'Synthetic current articulation TBD')
        result = json.loads(self.successful('--json').stdout)
        self.assertEqual(result['dimensions']['health']['pct'], 90)
        self.assertEqual(result['dimensions']['health']['source_file'], 'IDEAL_STATE/HEALTH.md')
        self.assertEqual(path.read_bytes(), before)

    def test_owner_can_review_exact_older_state_sources_after_retirement(self):
        from lifeos_hook_bridge.memory_source_review import preview, approve
        memory = self.fixture.fixture.memory
        reference = memory.remember(OWNER, category='principal', content='RULE: Synthetic unrelated old claim',
            title='', project='', request_id='state-older')['reference']
        memory.forget(OWNER, reference, 'state-forget-older')
        paths = ['LIFEOS/USER/TELOS/CURRENT_STATE/HEALTH.md', 'LIFEOS/USER/TELOS/IDEAL_STATE/MONEY.md']
        before = {relative: (self.root / relative).read_bytes() for relative in paths}
        plan = preview(memory, OWNER, paths)
        self.assertTrue(all(source['accepted'] for source in plan['sources']))
        self.assertEqual(approve(memory, OWNER, paths, plan['signature'])['status'], 'committed')
        body = json.loads(self.successful('--json').stdout)
        self.assertEqual(body['dimensions']['health']['pct'], 50)
        self.assertEqual(body['dimensions']['money']['pct'], 80)
        self.assertEqual({relative: (self.root / relative).read_bytes() for relative in paths}, before)

    def test_source_review_cannot_readmit_a_known_retired_state_claim(self):
        from lifeos_hook_bridge.memory_source_review import preview, approve
        memory = self.fixture.fixture.memory
        reference = memory.remember(OWNER, category='principal', content='RULE: Synthetic retired dimension',
            title='', project='', request_id='state-review-retired')['reference']
        self.note('CURRENT_STATE/HEALTH.md', 'Synthetic retired dimension\nstatus: have')
        memory.forget(OWNER, reference, 'state-retire-review')
        paths = ['LIFEOS/USER/TELOS/CURRENT_STATE/HEALTH.md']
        plan = preview(memory, OWNER, paths)
        self.assertFalse(plan['sources'][0]['accepted'])
        self.assertEqual(plan['sources'][0]['content'], '')
        self.assertEqual(approve(memory, OWNER, paths, plan['signature'])['status'], 'rejected')

    def test_foreign_source_link_refuses_before_publication(self):
        path = self.telos / 'CURRENT_STATE/HEALTH.md'
        foreign = self.fixture.fixture.home / 'foreign-state.md'
        foreign.write_bytes(path.read_bytes())
        path.unlink(); path.symlink_to(foreign)
        self.assertNotEqual(self.call('--json').returncode, 0)
        self.assertFalse(self.output.exists())

    def test_output_link_refuses_without_modifying_foreign_file(self):
        foreign = self.fixture.fixture.home / 'foreign-output.json'
        foreign.write_text('Synthetic foreign output')
        self.output.symlink_to(foreign)
        self.assertNotEqual(self.call('--json').returncode, 0)
        self.assertEqual(foreign.read_text(), 'Synthetic foreign output')

    def test_managed_marker_refuses_connector_loss_after_restart(self):
        marker = self.root / 'LIFEOS/USER/CONFIG/memory-http.json'
        marker.write_text('{"version":1,"managed":true}')
        (self.root / 'LIFEOS/USER/CONFIG/memory-access.json').unlink()
        self.assertNotEqual(self.call('--json', context=False).returncode, 0)
        self.assertFalse(self.output.exists())

    def test_output_is_private(self):
        self.successful()
        self.assertEqual(self.output.stat().st_mode & 0o777, 0o600)

    def test_unknown_status_warning_keeps_native_fallback(self):
        self.note('CURRENT_STATE/HEALTH.md', 'status: populated')
        self.note('IDEAL_STATE/HEALTH.md', 'Synthetic health target TBD')
        result = self.call('--json')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('1 unrecognized status keyword(s) (populated)', result.stderr)
        self.assertEqual(json.loads(result.stdout)['dimensions']['health']['pct'], 90)

    def process(self, mode):
        result = subprocess.run([sys.executable, str(Path(__file__).with_name('memory_state_process.py')),
            str(self.fixture.configuration.path), mode], env=dict(os.environ, HOME=str(self.fixture.fixture.home)),
            capture_output=True, text=True, timeout=30)
        self.assertEqual(result.stderr, '')
        return result

    def test_source_change_after_real_render_preserves_previous_artifact(self):
        self.successful()
        before = self.output.read_bytes()
        result = self.process('source')
        self.assertEqual(result.returncode, 0)
        self.assertFalse(json.loads(result.stdout)['ok'])
        self.assertEqual(self.output.read_bytes(), before)

    def test_authority_change_after_real_render_preserves_previous_artifact(self):
        self.successful()
        before = self.output.read_bytes()
        result = self.process('authority')
        self.assertEqual(result.returncode, 0)
        self.assertFalse(json.loads(result.stdout)['ok'])
        self.assertEqual(self.output.read_bytes(), before)

    def test_process_death_recovers_previous_state_before_fresh_publication(self):
        self.successful()
        before = self.output.read_bytes()
        self.note('CURRENT_STATE/HEALTH.md', 'status: have')
        result = self.process('interrupt')
        self.assertEqual(result.returncode, 73)
        self.assertEqual(result.stdout, '')
        self.assertNotEqual(self.output.read_bytes(), before)
        journal = self.fixture.fixture.memory.transaction.journal
        self.assertTrue(journal.exists())
        self.assertEqual(journal.stat().st_mode & 0o777, 0o600)
        with self.fixture.fixture.memory._transaction():
            self.assertEqual(self.output.read_bytes(), before)
        self.assertFalse(journal.exists())
        body = json.loads(self.successful('--json').stdout)
        self.assertEqual(body['dimensions']['health']['pct'], 100)

    def test_output_alias_to_registry_refuses_before_journal_collection(self):
        memory = self.fixture.fixture.memory
        saved = self.fixture.fixture.remember('Synthetic state registry guard', 'state-registry')
        os.link(memory.database, self.output)
        self.assertNotEqual(self.call('--json').returncode, 0)
        self.assertEqual(memory.get(OWNER, saved['reference'])['content'], 'Synthetic state registry guard')

    def test_directory_link_refuses_before_native_source_read(self):
        directory = self.telos / 'CURRENT_STATE'
        foreign = self.fixture.fixture.home / 'foreign-current-state'
        directory.rename(foreign)
        directory.symlink_to(foreign)
        self.assertNotEqual(self.call('--json').returncode, 0)
        self.assertFalse(self.output.exists())

    def test_service_refuses_foreign_root_and_invalid_format_before_publication(self):
        from lifeos_hook_bridge.memory_service import MemoryService
        service = MemoryService(self.fixture.configuration)
        for arguments in [{'root': str(self.fixture.fixture.home / 'foreign'), 'json_output': True},
                {'root': str(self.root / 'LIFEOS'), 'json_output': 'yes'}]:
            with self.subTest(arguments=arguments):
                self.assertFalse(service.native(self.fixture.context, 'lifeos_state', arguments)['ok'])
                self.assertFalse(self.output.exists())
