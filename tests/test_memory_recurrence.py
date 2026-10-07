# ABOUTME: Exercises the native recurrence ledger through current owner admission.
# ABOUTME: Checks source filtering, native reports, and registry publication.
from dataclasses import asdict
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

import test_memory_delegation as delegation_fixture
from test_memory_native import OWNER


class MemoryRecurrenceTests(unittest.TestCase):
    def setUp(self):
        self.fixture = delegation_fixture.MemoryDelegationTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        self.stream = self.root / 'LIFEOS/MEMORY/OBSERVABILITY/tool-failures.jsonl'
        self.stream.parent.mkdir(parents=True, exist_ok=True)
        self.row = {'timestamp': datetime.now(timezone.utc).isoformat(), 'event': 'tool_failure',
                    'tool_name': 'terminal', 'error': 'Synthetic recurrence failure', 'session_id': 'synthetic'}
        self.write([self.row])
        self.registry = self.root / 'LIFEOS/MEMORY/LEARNING/PATCHES/registry.jsonl'
        self.record = {'ts': datetime.now(timezone.utc).isoformat(), 'class_id': 'tool:terminal:synthetic-recurrence-failure',
            'hypothesis_slug': 'synthetic-failure', 'files': ['hooks/Synthetic.ts'], 'fixture': None, 'note': 'Synthetic repair'}

    def write(self, rows):
        self.stream.write_text(''.join(json.dumps(row) + '\n' for row in rows))

    def call(self, mode='report', *, context=True, original=False, record=None):
        source = Path(os.environ['LIFEOS_FRESHNESS_CONTROL_SOURCE']) if original else self.root
        module = source / 'LIFEOS/TOOLS/RecurrenceLedger.ts'
        env = {**os.environ, 'HOME': str(self.fixture.fixture.home), 'LIFEOS_DIR': str(self.root / 'LIFEOS'),
               'BUN_CONFIG_NO_AUTO_INSTALL': '1'}
        env.pop('LIFEOS_MEMORY_INTERNAL', None)
        env.pop('LIFEOS_MEMORY_CONTEXT', None)
        if context:
            env['LIFEOS_MEMORY_CONTEXT'] = json.dumps(asdict(self.fixture.context))
        code = 'const m = await import(' + json.dumps(str(module)) + ');'
        if mode == 'append':
            code += 'm.appendPatchRegistry(' + json.dumps(record or self.record) + '); console.log("appended");'
        else:
            name = {'report': 'buildReport(30)', 'events': 'collectFailureEvents(30)',
                    'clusters': 'collectObservabilityClusters(30)', 'registry': 'readPatchRegistry()'}[mode]
            code += 'console.log(JSON.stringify(m.' + name + '));'
        return subprocess.run(['bun', '--no-install', '-e', code], env=env, capture_output=True, text=True, timeout=40)

    def test_owner_report_and_library_results_match_original_native(self):
        self.registry.parent.mkdir(parents=True, exist_ok=True)
        self.registry.write_text(json.dumps(self.record) + '\n')
        for mode in ('report', 'events', 'clusters', 'registry'):
            with self.subTest(mode=mode):
                actual, original = self.call(mode), self.call(mode, original=True)
                self.assertEqual(actual.returncode, 0, actual.stderr)
                self.assertEqual(original.returncode, 0, original.stderr)
                self.assertEqual(actual.stderr + original.stderr, '')
                self.assertEqual(actual.stdout, original.stdout)
        self.assertEqual(json.loads(self.call().stdout)[0]['count'], 1)

    def test_missing_context_cannot_read_events_or_registry(self):
        for mode in ('report', 'events', 'clusters', 'registry'):
            with self.subTest(mode=mode):
                self.assertNotEqual(self.call(mode, context=False).returncode, 0)

    def test_private_and_decoded_private_rows_stay_outside_counts(self):
        extra = [dict(self.row, error='<private>Synthetic secret error</private>'),
                 dict(self.row, metadata={'label': '<private>Synthetic hidden metadata</private>'})]
        self.write([self.row, *extra])
        result = self.call('events')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(json.loads(result.stdout)), 1)
        self.assertNotIn('secret', result.stdout)

    def test_retired_error_cannot_return_in_events(self):
        marker = self.row['error']
        memory = self.fixture.fixture.memory
        saved = memory.remember(OWNER, category='assistant', content='RULE: ' + marker,
            title='', project='', request_id='recurrence-retire')
        self.assertEqual(saved['status'], 'committed', saved)
        self.assertEqual(memory.forget(OWNER, saved['reference'], 'recurrence-forget')['status'], 'committed')
        result = self.call('events')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), [])

    def test_revoked_account_cannot_read(self):
        self.fixture.configuration.update(lambda value: value['accounts'].pop('chat-a:100'))
        self.assertNotEqual(self.call().returncode, 0)

    def test_redirected_stream_refuses_foreign_content(self):
        foreign = self.fixture.fixture.home / 'foreign-stream.jsonl'
        foreign.write_bytes(self.stream.read_bytes())
        self.stream.unlink()
        self.stream.symlink_to(foreign)
        self.assertNotEqual(self.call().returncode, 0)

    def test_missing_context_cannot_append_registry(self):
        self.assertNotEqual(self.call('append', context=False).returncode, 0)
        self.assertFalse(self.registry.exists())

    def test_private_registry_record_refuses_publication(self):
        result = self.call('append', record=dict(self.record, note='<private>Synthetic private repair</private>'))
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.registry.exists())

    def test_read_only_owner_can_report_but_cannot_append(self):
        self.fixture.configuration.update(lambda value: value['destinations']['chat-a:200'].update(write=[]))
        result = self.call()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotEqual(self.call('append').returncode, 0)
        self.assertFalse(self.registry.exists())

    def test_owner_append_retains_native_bytes_with_private_permissions(self):
        actual = self.call('append')
        self.assertEqual(actual.returncode, 0, actual.stderr)
        self.assertEqual(actual.stderr, '')
        expected = self.registry.read_bytes()
        self.registry.unlink()
        original = self.call('append', original=True)
        self.assertEqual(original.returncode, 0, original.stderr)
        self.assertEqual(actual.stdout, original.stdout)
        self.assertEqual(self.registry.read_bytes(), expected)
        self.registry.unlink()
        self.assertEqual(self.call('append').returncode, 0)
        self.assertEqual(self.registry.stat().st_mode & 0o777, 0o600)

    def test_all_streams_and_capture_timestamps_match_original_native(self):
        stamp = self.row['timestamp']
        rows = {'verification-gate': {'ts': stamp, 'decision': 'block', 'type': 'T1', 'unit': 'synthetic-unit', 'evSummary': 'Synthetic evidence'},
                'format-gate': {'ts': stamp, 'decision': 'flag', 'code': 'SYNTHETIC', 'detail': 'Synthetic format'},
                'writing-gate': {'ts': stamp, 'decision': 'block-strong-no-run', 'strong': 3, 'weak': 1},
                'hook-healer': {'timestamp': stamp, 'event': 'synthetic-warning', 'path': 'hooks/Synthetic.ts'}}
        for name, row in rows.items():
            (self.stream.parent / (name + '.jsonl')).write_text(json.dumps(row) + '\n')
        directory = self.root / 'LIFEOS/MEMORY/LEARNING/FAILURES/2026-10/synthetic'
        directory.mkdir(parents=True)
        capture = directory / 'sentiment.json'
        capture.write_text(json.dumps({'summary': 'Synthetic wrong approach', 'session_id': 'synthetic'}))
        for mode in ('events', 'clusters', 'report'):
            with self.subTest(mode=mode):
                actual, original = self.call(mode), self.call(mode, original=True)
                self.assertEqual(actual.returncode, 0, actual.stderr)
                self.assertEqual(original.returncode, 0, original.stderr)
                self.assertEqual(actual.stdout, original.stdout)
        self.assertEqual(len(json.loads(self.call('events').stdout)), 6)
        capture.write_text(json.dumps({'summary': '<private>Synthetic capture secret</private>'}))
        self.assertEqual(len(json.loads(self.call('events').stdout)), 5)

    def test_private_registry_rows_do_not_return(self):
        self.registry.parent.mkdir(parents=True, exist_ok=True)
        self.registry.write_text(json.dumps(dict(self.record, note='<private>Synthetic patch secret</private>')) + '\n')
        result = self.call('registry')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), [])

    def test_source_discovery_and_row_limits_refuse(self):
        self.write([{'timestamp': '2026-10-05', 'event': 'tool_failure', 'error': 'Synthetic'}] * 2049)
        self.assertNotEqual(self.call('events').returncode, 0)
        self.write([self.row])
        directory = self.root / 'LIFEOS/MEMORY/LEARNING/FAILURES/2026-10'
        directory.mkdir(parents=True)
        for n in range(2049):
            (directory / str(n)).touch()
        self.assertNotEqual(self.call().returncode, 0)

    def process(self, mode):
        result = subprocess.run([sys.executable, str(Path(__file__).with_name('memory_recurrence_process.py')),
            str(self.fixture.configuration.path), mode], capture_output=True, text=True, timeout=40)
        self.assertEqual(result.stderr, '')
        return result

    def test_later_registry_edits_and_authority_changes_preserve_data(self):
        self.registry.parent.mkdir(parents=True, exist_ok=True)
        previous = json.dumps(self.record) + '\n'
        for mode in ('destination', 'authority'):
            with self.subTest(mode=mode):
                self.registry.write_text(previous)
                result = self.process(mode)
                self.assertEqual(result.returncode, 0, result.stdout)
                self.assertFalse(json.loads(result.stdout)['ok'])
                expected = 'Synthetic later registry edit\n' if mode == 'destination' else previous
                self.assertEqual(self.registry.read_text(), expected)

    def test_interrupted_registry_publication_recovers_previous_bytes(self):
        self.registry.parent.mkdir(parents=True, exist_ok=True)
        previous = json.dumps(self.record) + '\n'
        self.registry.write_text(previous)
        result = self.process('interrupt')
        self.assertEqual(result.returncode, 73, result.stdout)
        self.assertNotEqual(self.registry.read_text(), previous)
        with self.fixture.fixture.memory._transaction():
            pass
        self.assertEqual(self.registry.read_text(), previous)

    def test_source_or_authority_change_during_collection_refuses_delivery(self):
        for mode in ('source', 'read-authority'):
            with self.subTest(mode=mode):
                self.write([self.row])
                result = self.process(mode)
                self.assertEqual(result.returncode, 0, result.stdout)
                self.assertFalse(json.loads(result.stdout)['ok'])

    def test_discovery_limit_applies_across_capture_directories(self):
        for month in ('2026-09', '2026-10'):
            directory = self.root / 'LIFEOS/MEMORY/LEARNING/FAILURES' / month
            directory.mkdir(parents=True)
            for n in range(1050):
                (directory / str(n)).touch()
        self.assertNotEqual(self.call().returncode, 0)

    def test_registry_retry_returns_receipt_without_duplicate_append(self):
        from lifeos_hook_bridge.memory_service import MemoryService
        service = MemoryService(self.fixture.configuration)
        arguments = {'base': str(self.root / 'LIFEOS'), 'record': self.record, 'request_id': 'recurrence-retry'}
        first = service.native(self.fixture.context, 'recurrence_append', arguments)
        self.assertTrue(first['ok'], first)
        previous = self.registry.read_bytes()
        second = service.native(self.fixture.context, 'recurrence_append', arguments)
        self.assertTrue(second['ok'], second)
        self.assertEqual(second['receipt'], first['receipt'])
        self.assertEqual(self.registry.read_bytes(), previous)
