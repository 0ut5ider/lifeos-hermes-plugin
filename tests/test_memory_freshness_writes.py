# ABOUTME: Characterizes native freshness timestamp mutations and their publication boundaries.
# ABOUTME: Uses actual native functions and preserves synthetic source bytes after denied writes.
import json
import os
import re
from pathlib import Path
import subprocess
import sys
import unittest

import test_memory_freshness as freshness_fixture
from test_memory_native import OWNER


class MemoryFreshnessWriteTests(unittest.TestCase):
    def setUp(self):
        self.fixture = freshness_fixture.MemoryFreshnessTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        self.path = self.root / 'LIFEOS/USER/TELOS/TELOS.md'
        self.path.write_text(self.path.read_text().replace('last_updated:', 'provenance: template\nlast_updated:', 1))
        self.memory = self.fixture.memory

    def call(self, function, *, context=True, by='synthetic-writer', path=None, slug='mission'):
        target = str(path or self.path)
        args = [slug, by, target] if function == 'bumpTelosTimestamp' else [target, by]
        return self.fixture.library(function, *args, context=context)

    def successful(self, function, **options):
        result = self.call(function, **options)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        return json.loads(result.stdout)

    def refused(self, function, *, context=True, path=None):
        target = path or self.path
        before = target.read_bytes()
        result = self.call(function, context=context, path=path)
        if function == 'stampContextWrite':
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout), {'changed': False, 'provenanceFlipped': False})
        else:
            self.assertNotEqual(result.returncode, 0)
        self.assertEqual(target.read_bytes(), before)

    def test_machine_stamp_changes_only_write_clock_and_template_provenance(self):
        result = self.successful('stampContextWrite')
        self.assertEqual(result, {'changed': True, 'provenanceFlipped': True})
        text = self.path.read_text()
        self.assertIn('provenance: customized\n', text)
        self.assertIn('last_reviewed: 2026-10-01\n', text)
        self.assertIn('last_updated_by: synthetic-writer\n', text)
        self.assertIn('Synthetic freshness mission', text)
        self.assertFalse(self.successful('stampContextWrite')['provenanceFlipped'])

    def test_review_stamp_preserves_the_existing_write_clock(self):
        result = self.successful('bumpReviewedTimestamp')
        self.assertTrue(result['changed'])
        text = self.path.read_text()
        self.assertIn('last_updated: 2026-10-02\n', text)
        self.assertIn('last_reviewed_by: synthetic-writer\n', text)
        self.assertIn('provenance: template\n', text)
        self.assertNotIn('last_updated_by:', text)

    def test_owner_and_standalone_mutations_preserve_native_bytes(self):
        original = self.path.read_bytes()
        for function in ('bumpTelosTimestamp', 'bumpContextTimestamp', 'bumpReviewedTimestamp', 'stampContextWrite'):
            with self.subTest(function=function):
                self.path.write_bytes(original)
                managed = self.successful(function)
                candidate = self.path.read_text()
                connector = self.root / 'LIFEOS/USER/CONFIG/memory-access.json'
                settings = connector.read_bytes()
                connector.unlink()
                try:
                    self.path.write_bytes(original)
                    standalone = self.successful(function, context=False)
                    native = self.path.read_text()
                finally:
                    connector.write_bytes(settings); connector.chmod(0o600)
                normalize = lambda text: re.sub(r'^(last_updated|last_reviewed): .*$', r'\1: TIME', text, flags=re.MULTILINE)
                self.assertEqual(managed, standalone)
                self.assertEqual(normalize(candidate), normalize(native))

    def test_missing_context_refuses_each_timestamp_mutation(self):
        for function in ('bumpTelosTimestamp', 'bumpContextTimestamp', 'bumpReviewedTimestamp', 'stampContextWrite'):
            with self.subTest(function=function):
                self.refused(function, context=False)

    def test_revoked_owner_refuses_each_timestamp_mutation(self):
        self.fixture.fixture.configuration.update(lambda c: c['accounts'].pop('chat-a:100'))
        for function in ('bumpTelosTimestamp', 'bumpContextTimestamp', 'bumpReviewedTimestamp', 'stampContextWrite'):
            with self.subTest(function=function):
                self.refused(function)

    def test_owner_read_without_write_refuses_each_timestamp_mutation(self):
        self.fixture.fixture.configuration.update(lambda c: c['destinations']['chat-a:200'].update(write=[]))
        for function in ('bumpTelosTimestamp', 'bumpContextTimestamp', 'bumpReviewedTimestamp', 'stampContextWrite'):
            with self.subTest(function=function):
                self.refused(function)

    def test_retired_source_cannot_be_made_current_by_a_timestamp_write(self):
        reference = self.memory.remember(OWNER, category='principal', content='RULE: Synthetic retired timestamp claim',
            title='', project='', request_id='freshness-write-retired')['reference']
        self.path.write_text(self.path.read_text() + '\nSynthetic retired timestamp claim\n')
        self.memory.forget(OWNER, reference, 'freshness-write-forget')
        for function in ('bumpTelosTimestamp', 'bumpContextTimestamp', 'bumpReviewedTimestamp', 'stampContextWrite'):
            with self.subTest(function=function):
                self.refused(function)

    def test_foreign_source_link_refuses_without_mutating_the_foreign_file(self):
        foreign = self.fixture.fixture.fixture.home / 'foreign-freshness-write.md'
        foreign.write_bytes(self.path.read_bytes())
        self.path.unlink(); self.path.symlink_to(foreign)
        self.refused('bumpContextTimestamp')

    def test_publication_uses_private_owner_permissions(self):
        self.successful('bumpContextTimestamp')
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)

    def test_system_context_timestamp_keeps_native_source_text(self):
        path = self.root / 'LIFEOS/DOCUMENTATION/LifeosSystemArchitecture.md'
        self.assertTrue(self.successful('bumpContextTimestamp', path=path)['changed'])
        self.assertIn('Synthetic architecture', path.read_text())
        self.assertIn('last_reviewed: 2026-10-01', path.read_text())

    def test_unsupported_configuration_target_refuses_before_a_write(self):
        path = self.root / 'LIFEOS/USER/CONFIG/synthetic-unsupported.md'
        path.write_text('# Synthetic private configuration\n')
        self.refused('bumpContextTimestamp', path=path)

    def test_unknown_section_preserves_native_committed_file_timestamp(self):
        result = self.successful('bumpTelosTimestamp', slug='synthetic_absent')
        self.assertEqual(result, {'changed': True, 'sectionFound': False})
        self.assertIn('last_updated_by: synthetic-writer', self.path.read_text())

    def test_managed_default_writer_uses_current_attested_identity(self):
        settings = self.root / 'settings.json'
        settings.write_text('{"daidentity":{"name":"SYNTHETIC_UNADMITTED_WRITER"}}')
        result = self.fixture.library('bumpContextTimestamp', str(self.path))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('last_updated_by: chat-a:100\n', self.path.read_text())
        self.assertNotIn('SYNTHETIC_UNADMITTED_WRITER', self.path.read_text())

    def test_missing_connector_durable_marker_refuses_timestamp_publication(self):
        (self.root / 'LIFEOS/USER/CONFIG/memory-http.json').write_text('{"version":1,"managed":true}')
        (self.root / 'LIFEOS/USER/CONFIG/memory-access.json').unlink()
        self.refused('bumpContextTimestamp', context=False)

    def process(self, mode, path=None):
        target = path or self.path
        result = subprocess.run([sys.executable, str(Path(__file__).with_name('memory_freshness_write_process.py')),
            str(self.fixture.fixture.configuration.path), mode, 'write_freshness', str(target.relative_to(self.root))],
            env=self.fixture.environment(), capture_output=True, text=True, timeout=30)
        self.assertEqual(result.stderr, '')
        return result

    def test_changed_source_survives_refusal_and_next_transaction(self):
        before = self.path.read_text()
        result = self.process('source')
        self.assertEqual(result.returncode, 0)
        self.assertFalse(json.loads(result.stdout)['ok'])
        expected = before + '\nSynthetic later source edit\n'
        self.assertEqual(self.path.read_text(), expected)
        with self.memory._transaction():
            self.assertEqual(self.path.read_text(), expected)

    def test_revocation_after_render_preserves_previous_source(self):
        before = self.path.read_bytes()
        result = self.process('authority')
        self.assertEqual(result.returncode, 0)
        self.assertFalse(json.loads(result.stdout)['ok'])
        with self.memory._transaction():
            self.assertEqual(self.path.read_bytes(), before)

    def test_later_excluded_source_edit_survives_refusal_and_next_transaction(self):
        before = self.path.read_text()
        result = self.process('source_excluded')
        self.assertEqual(result.returncode, 0)
        self.assertFalse(json.loads(result.stdout)['ok'])
        expected = before + '\n<private>Synthetic later excluded edit</private>\n'
        self.assertEqual(self.path.read_text(), expected)
        with self.memory._transaction():
            self.assertEqual(self.path.read_text(), expected)

    def test_process_death_recovers_user_and_fixed_system_sources(self):
        for relative in ['LIFEOS/USER/TELOS/TELOS.md', 'LIFEOS/LIFEOS_SYSTEM_PROMPT.md',
                         'LIFEOS/DOCUMENTATION/ARCHITECTURE_SUMMARY.md',
                         'LIFEOS/DOCUMENTATION/LifeosSystemArchitecture.md']:
            with self.subTest(relative=relative):
                path = self.root / relative
                before = path.read_bytes()
                result = self.process('interrupt', path)
                self.assertEqual(result.returncode, 73)
                self.assertEqual(result.stdout, '')
                self.assertNotEqual(path.read_bytes(), before)
                journal = self.memory.transaction.journal
                self.assertTrue(journal.exists())
                self.assertEqual(journal.stat().st_mode & 0o777, 0o600)
                with self.memory._transaction():
                    self.assertEqual(path.read_bytes(), before)
                self.assertFalse(journal.exists())
                self.assertTrue(self.successful('bumpContextTimestamp', path=path)['changed'])

    def test_single_line_writer_label_cannot_add_review_metadata(self):
        before = self.path.read_bytes()
        result = self.call('bumpContextTimestamp', by='synthetic\nlast_reviewed_by: forged')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.path.read_bytes(), before)

    def test_retired_claim_in_writer_label_cannot_be_published(self):
        saved = self.memory.remember(OWNER, category='principal', content='RULE: Synthetic retired writer label',
            title='', project='', request_id='retired-writer-label')
        self.memory.forget(OWNER, saved['reference'], 'forget-writer-label')
        # A new current source is admissible, but its generated metadata is still checked.
        self.fixture.source('LIFEOS/USER/TELOS/TELOS.md', '# Synthetic clean current TELOS\n')
        before = self.path.read_bytes()
        result = self.call('bumpContextTimestamp', by='Synthetic retired writer label')
        self.assertNotEqual(result.returncode, 0)
        with self.memory._transaction():
            self.assertEqual(self.path.read_bytes(), before)

    def test_exact_review_of_older_safe_source_allows_native_mutation(self):
        from lifeos_hook_bridge.memory_source_review import preview, approve
        saved = self.memory.remember(OWNER, category='principal', content='RULE: Synthetic unrelated old stamp',
            title='', project='', request_id='older-safe-stamp')
        self.memory.forget(OWNER, saved['reference'], 'forget-old-stamp')
        paths = ['LIFEOS/USER/TELOS/TELOS.md']
        plan = preview(self.memory, OWNER, paths)
        self.assertTrue(plan['sources'][0]['accepted'])
        self.assertEqual(approve(self.memory, OWNER, paths, plan['signature'])['status'], 'committed')
        self.assertTrue(self.successful('bumpContextTimestamp')['changed'])
        self.assertIn('Synthetic freshness mission', self.path.read_text())

    def test_missing_source_keeps_native_no_change_report_and_does_not_create_file(self):
        self.path.unlink()
        for function in ('bumpTelosTimestamp', 'bumpContextTimestamp', 'bumpReviewedTimestamp', 'stampContextWrite'):
            with self.subTest(function=function):
                self.assertFalse(self.successful(function)['changed'])
                self.assertFalse(self.path.exists())

    def test_empty_and_plain_sources_keep_native_transformations(self):
        for original in ('', '# Synthetic plain source\n'):
            for function in ('bumpContextTimestamp', 'bumpReviewedTimestamp', 'stampContextWrite'):
                with self.subTest(original=original, function=function):
                    self.path.write_text(original)
                    managed = self.successful(function)
                    candidate = self.path.read_text()
                    connector = self.root / 'LIFEOS/USER/CONFIG/memory-access.json'
                    settings = connector.read_bytes()
                    connector.unlink()
                    try:
                        self.path.write_text(original)
                        native = self.successful(function, context=False)
                        control = self.path.read_text()
                    finally:
                        connector.write_bytes(settings); connector.chmod(0o600)
                    normalize = lambda text: re.sub(r'^(last_updated|last_reviewed): .*$', r'\1: TIME', text, flags=re.MULTILINE)
                    self.assertEqual(managed, native)
                    self.assertEqual(normalize(candidate), normalize(control))
