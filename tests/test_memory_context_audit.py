# ABOUTME: Exercises native context audit calculations with current owner source admission.
# ABOUTME: Measures private and retired findings, report permissions, and authority boundaries.
from dataclasses import asdict
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

import test_memory_delegation as delegation
import test_memory_native as native_fixture
from lifeos_hook_bridge.memory_freshness import CONTEXT
from lifeos_hook_bridge.memory_service import MemoryService


class MemoryContextAuditTests(unittest.TestCase):
    def setUp(self):
        self.fixture = delegation.MemoryDelegationTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        self.events = []
        for relative in sorted(CONTEXT):
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('---\nlast_updated: 2026-10-05\n---\n# Synthetic context\n\n'
                '## Synthetic section\nThis synthetic context has sufficient content for the audit.\n')
        self.identity = self.root / 'LIFEOS/USER/PRINCIPAL/PRINCIPAL_IDENTITY.md'
        self.identity.write_text(self.identity.read_text() + '\n## Synthetic empty section\n')
        self.report = self.root / 'LIFEOS/MEMORY/STATE/context-audit/AUDIT.md'

    def call(self, *arguments, context=True, original=False):
        environment = {**os.environ, 'HOME': str(self.fixture.fixture.home),
            'LIFEOS_DIR': str(self.root / 'LIFEOS'), 'BUN_CONFIG_NO_AUTO_INSTALL': '1'}
        environment.pop('LIFEOS_MEMORY_INTERNAL', None)
        environment.pop('LIFEOS_MEMORY_CONTEXT', None)
        if context:
            environment['LIFEOS_MEMORY_CONTEXT'] = json.dumps(asdict(self.fixture.context))
        source = Path(os.environ['LIFEOS_FRESHNESS_CONTROL_SOURCE']) if original else native_fixture.SOURCE
        result = subprocess.run(['bun', '--no-install', str(source / 'LIFEOS/TOOLS/ContextAudit.ts'),
            *arguments], env=environment, capture_output=True, text=True, timeout=40)
        self.events.append({'command': result.args, 'returncode': result.returncode,
            'stdout': result.stdout, 'stderr': result.stderr})
        return result

    def test_owner_json_retains_native_findings(self):
        managed = self.call('--json')
        original = self.call('--json', context=False, original=True)
        self.assertEqual(managed.returncode, original.returncode, managed.stderr)
        left, right = json.loads(managed.stdout), json.loads(original.stdout)
        left.pop('generated_at'); right.pop('generated_at')
        self.assertEqual(left, right)
        self.assertIn('Synthetic empty section', managed.stdout)
        self.assertFalse(self.report.exists())

    def test_owner_markdown_and_critical_exit_match_native_outputs(self):
        for missing in (False, True):
            with self.subTest(missing=missing):
                if missing:
                    self.identity.unlink()
                managed = self.call()
                markdown = self.report.read_text().split('\n', 1)[1]
                original = self.call(context=False, original=True)
                self.assertEqual(managed.returncode, original.returncode, managed.stderr)
                self.assertEqual(managed.returncode, 1 if missing else 0)
                self.assertEqual(managed.stdout, original.stdout)
                self.assertEqual(managed.stderr, original.stderr)
                self.assertEqual(self.report.read_text().split('\n', 1)[1], markdown)

    def test_unbound_call_refuses_without_reading_or_publishing_findings(self):
        result = self.call(context=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, '')
        self.assertFalse(self.report.exists())

    def test_private_or_retired_headings_do_not_return_in_findings(self):
        for kind in ('private', 'retired'):
            with self.subTest(kind=kind):
                marker = 'Synthetic ' + kind + ' audit marker'
                if kind == 'retired':
                    memory = self.fixture.fixture.memory
                    saved = memory.remember(native_fixture.OWNER, category='principal', content='RULE: ' + marker,
                        title='', project='', request_id='retired-audit')
                    self.assertEqual(memory.forget(native_fixture.OWNER, saved['reference'], 'forget-audit')['status'], 'committed')
                heading = '## ' + marker + '\n'
                self.identity.write_text('<private>\n' + heading + '</private>\n' if kind == 'private' else heading)
                result = self.call('--json')
                self.assertNotIn(marker, result.stdout + result.stderr)
                self.assertIn('principal_identity', result.stdout)

    def test_read_only_owner_can_read_but_cannot_publish_report(self):
        self.fixture.configuration.update(lambda value: value['destinations']['chat-a:200'].update(write=[]))
        result = self.call('--json')
        self.assertIn('Synthetic empty section', result.stdout)
        result = self.call()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.report.exists())

    def test_owner_publishes_private_report_and_revocation_preserves_it(self):
        result = self.call()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Synthetic empty section', self.report.read_text())
        self.assertEqual(self.report.stat().st_mode & 0o777, 0o600)
        before = self.report.read_bytes()
        self.fixture.configuration.update(lambda value: value['accounts'].pop('chat-a:100'))
        result = self.call()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, '')
        self.assertEqual(self.report.read_bytes(), before)

    def native(self, json_output=False, **changes):
        arguments = {'root': str(self.root), 'json_output': json_output} | changes
        result = MemoryService(self.fixture.configuration).native(self.fixture.context, 'context_audit', arguments)
        self.events.append({'native_arguments': arguments, 'native_result': result})
        return result

    def test_source_authority_or_destination_changes_after_actual_render_preserve_report(self):
        self.report.parent.mkdir(parents=True, exist_ok=True)
        configuration = self.fixture.configuration.load()
        source = self.identity.read_bytes()
        for kind in ('source', 'authority', 'destination'):
            with self.subTest(kind=kind):
                self.report.write_bytes(b'Synthetic previous audit\n')
                changed = False
                def trace(frame, event, argument):
                    nonlocal changed
                    if (not changed and event == 'return' and frame.f_code.co_name == '_native'
                            and frame.f_locals.get('action') == 'context_audit'):
                        changed = True
                        if kind == 'source':
                            self.identity.write_bytes(source + b'\n## Synthetic later identity\n')
                        elif kind == 'authority':
                            self.fixture.configuration.update(lambda value: value['accounts'].pop('chat-a:100'))
                        else:
                            self.report.write_bytes(b'Synthetic later audit\n')
                    return trace
                sys.settrace(trace)
                try:
                    result = self.native()
                finally:
                    sys.settrace(None)
                self.assertTrue(changed)
                self.assertFalse(result['ok'], result)
                self.assertEqual(self.report.read_bytes(), b'Synthetic later audit\n' if kind == 'destination'
                    else b'Synthetic previous audit\n')
                with self.fixture.fixture.memory._transaction():
                    pass
                self.assertEqual(self.report.read_bytes(), b'Synthetic later audit\n' if kind == 'destination'
                    else b'Synthetic previous audit\n')
                self.identity.write_bytes(source)
                self.fixture.configuration.update(lambda value: (value.clear(), value.update(configuration)))

    def test_redirected_report_refuses_without_changing_foreign_bytes(self):
        foreign = self.root.parent / 'foreign-audit.md'
        foreign.write_text('Synthetic foreign audit\n')
        self.report.parent.mkdir(parents=True, exist_ok=True)
        self.report.symlink_to(foreign)
        result = self.call()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, '')
        self.assertEqual(foreign.read_text(), 'Synthetic foreign audit\n')
        self.assertIn('Synthetic empty section', self.call('--json').stdout)

    def test_fixed_root_alias_and_invalid_arguments(self):
        alias = self.root.parent / 'audit-installed-alias'
        alias.symlink_to(self.root, target_is_directory=True)
        self.fixture.configuration.update(lambda value: value.update(root=str(alias)))
        self.assertIn('Synthetic empty section', self.call('--json').stdout)
        for changes in ({'root': None}, {'root': 'relative'}, {'json_output': 1}, {'json_output': []}):
            with self.subTest(changes=changes):
                result = self.native(**changes)
                self.assertFalse(result['ok'], result)
                self.assertNotIn('report', result)

    def test_managed_marker_and_restricted_audience_refuse_without_output(self):
        self.fixture.configuration.update(lambda value: value['destinations']['chat-a:200'].update(
            read=['project'], write=['project'], projects=['lab']))
        self.assertEqual(self.call('--json').stdout, '')
        (self.root / 'LIFEOS/USER/CONFIG/memory-http.json').write_text('{"version":1,"managed":true}')
        (self.root / 'LIFEOS/USER/CONFIG/memory-access.json').unlink()
        result = self.call('--json', context=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, '')

    def process(self, mode):
        result = subprocess.run([sys.executable, str(Path(__file__).with_name('memory_context_audit_process.py')),
            str(self.fixture.configuration.path), mode, json.dumps(asdict(self.fixture.context))],
            capture_output=True, text=True, timeout=40)
        self.events.append({'command': result.args, 'returncode': result.returncode,
            'stdout': result.stdout, 'stderr': result.stderr})
        return result

    def test_process_exit_after_report_publication_recovers_previous_bytes(self):
        self.report.parent.mkdir(parents=True, exist_ok=True)
        self.report.write_bytes(b'Synthetic previous interrupted report\n')
        result = self.process('exit')
        self.assertEqual(result.returncode, 73, result.stderr)
        self.assertIn('Synthetic empty section', self.report.read_text())
        result = self.process('recover')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.report.read_bytes(), b'Synthetic previous interrupted report\n')
        self.assertEqual(self.call().returncode, 0)

    def test_later_edit_after_process_exit_refuses_recovery_and_preserves_it(self):
        self.assertEqual(self.process('exit').returncode, 73)
        self.report.write_bytes(b'Synthetic later report after interruption\n')
        result = self.process('recover')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.report.read_bytes(), b'Synthetic later report after interruption\n')
        self.assertTrue(self.fixture.fixture.memory.transaction.journal.exists())

    def tearDown(self):
        directory = os.environ.get('LIFEOS_CONTEXT_AUDIT_EVIDENCE_DIR')
        if directory:
            path = Path(directory)
            path.mkdir(parents=True, exist_ok=True)
            (path / (self._testMethodName + '.json')).write_text(json.dumps(self.events, indent=2) + '\n')


if __name__ == '__main__':
    unittest.main()
