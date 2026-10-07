# ABOUTME: Verifies native numeric installation counts under current unrestricted owner authority.
# ABOUTME: Preserves count formats and refuses unbound, restricted, revoked, or redirected calls.
from dataclasses import asdict
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

import test_memory_delegation as delegation
import test_memory_native as native_fixture
from lifeos_hook_bridge.memory_service import MemoryService


class MemoryCountsTests(unittest.TestCase):
    def setUp(self):
        self.fixture = delegation.MemoryDelegationTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        self.events = []
        self.fixture.fixture.memory.recall(native_fixture.OWNER, 'synthetic counts')
        for name in ('MEMORY/LEARNING/sample.md', 'MEMORY/RESEARCH/sample.md', 'MEMORY/RESEARCH/sample.json'):
            path = self.root / 'LIFEOS' / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('Synthetic inventory metadata fixture\n')
        (self.root / 'LIFEOS/MEMORY/WORK/synthetic-work').mkdir(parents=True)
        path = self.root / 'LIFEOS/MEMORY/LEARNING/SIGNALS/ratings.jsonl'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('{"rating":8}\n\n{"rating":9}\n')
        (self.root / 'settings.json').write_text(json.dumps({'hooks': {'Stop': [{'hooks':
            [{'command': 'synthetic_hook_one'}, {'command': 'synthetic_hook_one'}, {'command': 'synthetic_hook_two'}]}]}}))

    def call(self, *arguments, context=True, lifeos_dir=None, original=False):
        environment = {**os.environ, 'HOME': str(self.fixture.fixture.home),
            'LIFEOS_DIR': str(lifeos_dir or self.root / 'LIFEOS'), 'BUN_CONFIG_NO_AUTO_INSTALL': '1'}
        environment.pop('LIFEOS_MEMORY_INTERNAL', None)
        environment.pop('LIFEOS_MEMORY_CONTEXT', None)
        if context:
            environment['LIFEOS_MEMORY_CONTEXT'] = json.dumps(asdict(self.fixture.context))
        source = Path(os.environ['LIFEOS_FRESHNESS_CONTROL_SOURCE']) if original else native_fixture.SOURCE
        result = subprocess.run(['bun', '--no-install', str(source / 'LIFEOS/TOOLS/GetCounts.ts'),
            *arguments], env=environment, capture_output=True, text=True, timeout=30)
        self.events.append({'command': result.args, 'returncode': result.returncode,
            'stdout': result.stdout, 'stderr': result.stderr})
        return result

    def successful(self, *arguments):
        result = self.call(*arguments)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        return result.stdout

    def test_owner_json_shell_and_every_single_count_match_native_formats(self):
        selected = {}
        for arguments in ((), ('--shell',), *(('--single', key) for key in
                ('skills', 'workflows', 'hooks', 'signals', 'files', 'work', 'research', 'ratings'))):
            selected[arguments] = self.successful(*arguments)
        value = json.loads(selected[()])
        self.assertEqual(value['hooks'], 2)
        self.assertEqual(value['signals'], 1)
        self.assertEqual(value['work'], 1)
        self.assertEqual(value['research'], 2)
        self.assertEqual(value['ratings'], 2)
        for arguments, expected in selected.items():
            with self.subTest(arguments=arguments):
                result = self.call(*arguments, context=False, original=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stderr, '')
                self.assertEqual(result.stdout, expected)

    def test_unbound_counts_refuse_without_output(self):
        result = self.call(context=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, '')

    def test_revoked_counts_refuse_without_output(self):
        self.fixture.configuration.update(lambda value: value['accounts'].pop('chat-a:100'))
        result = self.call('--single', 'files')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, '')

    def test_restricted_counts_refuse_without_output(self):
        self.fixture.configuration.update(lambda value: value['destinations']['chat-a:200'].update(
            read=['project'], write=['project'], projects=['lab']))
        result = self.call('--shell')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, '')

    def test_foreign_data_directory_refuses_before_returning_counts(self):
        directory = self.root.parent / 'foreign-counts'
        (directory / 'USER').mkdir(parents=True)
        (directory / 'USER/one').write_text('Synthetic foreign inventory file\n')
        result = self.call('--single', 'files', lifeos_dir=directory)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, '')

    def test_owner_read_grant_without_write_still_receives_counts(self):
        self.fixture.configuration.update(lambda value: value['destinations']['chat-a:200'].update(write=[]))
        self.assertEqual(self.successful('--single', 'ratings'), '2\n')

    def test_durable_marker_refuses_connector_loss_without_output(self):
        (self.root / 'LIFEOS/USER/CONFIG/memory-http.json').write_text('{"version":1,"managed":true}')
        (self.root / 'LIFEOS/USER/CONFIG/memory-access.json').unlink()
        result = self.call(context=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, '')

    def test_physical_installed_root_alias_uses_the_same_inventory(self):
        alias = self.root.parent / 'counts-installed-alias'
        alias.symlink_to(self.root, target_is_directory=True)
        self.fixture.configuration.update(lambda value: value.update(root=str(alias)))
        self.assertEqual(self.successful('--single', 'ratings'), '2\n')

    def test_redirected_selected_inventory_refuses_but_unrelated_single_count_remains_available(self):
        for kind in ('ratings', 'research'):
            with self.subTest(kind=kind):
                path = self.root / ('LIFEOS/MEMORY/LEARNING/SIGNALS/ratings.jsonl' if kind == 'ratings'
                    else 'LIFEOS/MEMORY/RESEARCH')
                original = path.with_name(path.name + '.original')
                path.rename(original)
                foreign = self.root.parent / ('foreign-inventory-' + kind)
                if kind == 'ratings':
                    foreign.write_text('{"rating":7}\n')
                else:
                    foreign.mkdir()
                    (foreign / 'foreign.md').write_text('Synthetic foreign count\n')
                path.symlink_to(foreign, target_is_directory=kind == 'research')
                try:
                    result = self.call('--single', kind)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertEqual(result.stdout, '')
                    self.successful('--single', 'skills')
                finally:
                    path.unlink()
                    original.rename(path)

    def native(self, **changes):
        arguments = {'root': str(self.root), 'lifeos_dir': str(self.root / 'LIFEOS'), 'only': None}
        result = MemoryService(self.fixture.configuration).native(self.fixture.context, 'counts', arguments | changes)
        self.events.append({'native_arguments': arguments | changes, 'native_result': result})
        return result

    def test_inventory_or_authority_change_after_actual_native_collection_refuses(self):
        for kind in ('inventory', 'authority'):
            with self.subTest(kind=kind):
                changed = False
                configuration = self.fixture.configuration.load()
                path = self.root / 'LIFEOS/MEMORY/LEARNING/SIGNALS/ratings.jsonl'
                original = path.read_bytes()
                def trace(frame, event, argument):
                    nonlocal changed
                    if (not changed and event == 'return' and frame.f_code.co_name == '_native'
                            and frame.f_locals.get('action') == 'counts'):
                        changed = True
                        if kind == 'inventory':
                            path.write_bytes(original + b'{"rating":10}\n')
                        else:
                            self.fixture.configuration.update(lambda value: value['accounts'].pop('chat-a:100'))
                    return trace
                sys.settrace(trace)
                try:
                    result = self.native()
                finally:
                    sys.settrace(None)
                self.assertTrue(changed)
                self.assertFalse(result['ok'], result)
                self.assertNotIn('counts', result)
                path.write_bytes(original)
                self.fixture.configuration.update(lambda value: (value.clear(), value.update(configuration)))

    def test_invalid_source_arguments_refuse_without_returning_counts(self):
        for changes in ({'root': 'relative'}, {'root': None}, {'lifeos_dir': []}, {'only': []},
                {'only': 1}, {'only': 'toString'}, {'only': 'unknown'}):
            with self.subTest(changes=changes):
                result = self.native(**changes)
                self.assertFalse(result['ok'], result)
                self.assertNotIn('counts', result)

    def tearDown(self):
        directory = os.environ.get('LIFEOS_COUNTS_EVIDENCE_DIR')
        if directory:
            path = Path(directory)
            path.mkdir(parents=True, exist_ok=True)
            (path / (self._testMethodName + '.json')).write_text(json.dumps(self.events, indent=2) + '\n')


if __name__ == '__main__':
    unittest.main()
