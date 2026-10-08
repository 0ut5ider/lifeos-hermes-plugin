# ABOUTME: Runs the native user index CLI under actual governed owner contexts.
# ABOUTME: Verifies private publication, current authority, retained-source exclusion, and supported owner-job execution.
from dataclasses import asdict
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest

import test_memory_session_harvest as harvest_fixture
import test_memory_owner_jobs as job_fixture
from test_memory_native import SOURCE, OWNER
from lifeos_hook_bridge.memory_service import MemoryService


class MemoryUserIndexPublishTests(unittest.TestCase):
    def setUp(self):
        self.fixture = harvest_fixture.MemorySessionHarvestTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        pulse = self.root / 'LIFEOS/PULSE'
        pulse.mkdir()
        for name in ('modules', 'Observability', 'node_modules'):
            (pulse / name).symlink_to(SOURCE / 'LIFEOS/PULSE' / name, target_is_directory=True)
        self.output = pulse / 'state/user-index.json'
        self.source = self.root / 'LIFEOS/USER/TELOS/GOALS.md'
        self.source.parent.mkdir(parents=True, exist_ok=True)
        self.source.write_text('# SyntheticPublishedIndexGoal\nSynthetic current goal details\n')
        self.configuration = self.fixture.fixture.configuration
        self.memory = self.fixture.fixture.fixture.memory

    def call(self, *flags, context=True):
        environment = dict(os.environ, HOME=str(self.root.parent), LIFEOS_DIR=str(self.root / 'LIFEOS'),
            BUN_CONFIG_NO_AUTO_INSTALL='1')
        environment.pop('LIFEOS_MEMORY_INTERNAL', None)
        environment.pop('LIFEOS_MEMORY_CONTEXT', None)
        if context: environment['LIFEOS_MEMORY_CONTEXT'] = json.dumps(asdict(self.fixture.context))
        return subprocess.run(['bun', '--no-install', str(self.root / 'LIFEOS/PULSE/modules/user-index.ts'), *flags],
            env=environment, capture_output=True, text=True, timeout=40)

    def test_owner_cli_publishes_a_private_index_and_preserves_source_bytes(self):
        before = self.source.read_bytes(), self.source.stat().st_mtime_ns
        result = self.call('--json')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        index = json.loads(result.stdout)
        self.assertIn('SyntheticPublishedIndexGoal', result.stdout)
        self.assertEqual(json.loads(self.output.read_text()), index)
        self.assertEqual(self.output.stat().st_mode & 0o777, 0o600)
        self.assertEqual((self.source.read_bytes(), self.source.stat().st_mtime_ns), before)

    def test_missing_context_and_revoked_owner_refuse_before_publication(self):
        result = self.call('--json', context=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('SyntheticPublishedIndexGoal', result.stdout)
        self.assertFalse(self.output.exists())
        self.configuration.update(lambda value: value['accounts'].clear())
        result = self.call('--json')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.output.exists())

    def test_retired_source_does_not_enter_native_cli_output_or_cache(self):
        saved = self.memory.remember(OWNER, category='principal', content='RULE: SyntheticPublishedIndexGoal',
            title='', project='', request_id='synthetic-index-publish-source')
        self.memory.forget(OWNER, saved['reference'], 'synthetic-index-publish-forget')
        result = self.call('--json')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn('SyntheticPublishedIndexGoal', result.stdout)
        self.assertNotIn('SyntheticPublishedIndexGoal', self.output.read_text())
        self.assertIn('SyntheticPublishedIndexGoal', self.source.read_text())

    def test_native_query_remains_read_only_and_matches_published_entry(self):
        first = self.call('--json')
        self.assertEqual(first.returncode, 0, first.stderr)
        expected = next(entry for entry in json.loads(first.stdout)['files'] if entry['path'] == 'TELOS/GOALS.md')
        before = self.output.read_bytes(), self.output.stat().st_mtime_ns
        for query in ('TELOS/GOALS.md', str(self.source)):
            with self.subTest(query=query):
                result = self.call('--query', query)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(result.stdout), expected)
                self.assertEqual((self.output.read_bytes(), self.output.stat().st_mtime_ns), before)

    def test_existing_owner_job_admission_can_run_the_fixed_user_index_cli(self):
        fixture = job_fixture.MemoryOwnerJobsTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        root = fixture.fixture.root
        pulse = root / 'LIFEOS/PULSE'
        pulse.mkdir()
        for name in ('modules', 'Observability', 'node_modules'):
            (pulse / name).symlink_to(SOURCE / 'LIFEOS/PULSE' / name, target_is_directory=True)
        result = fixture.run_job('user-index')
        self.assertEqual(result['status'], 'completed', result)
        self.assertEqual((pulse / 'state/user-index.json').stat().st_mode & 0o777, 0o600)

    def service(self, identifier, publish=True):
        return MemoryService(self.configuration).native(self.fixture.context, 'user_index',
            {'query': None, 'publish_index': publish, 'request_id': identifier})

    def test_same_request_preserves_cache_bytes_and_returns_its_committed_index(self):
        first = self.service('synthetic-index-repeat')
        self.assertTrue(first['ok'], first)
        before = self.output.read_bytes(), self.output.stat().st_mtime_ns
        second = self.service('synthetic-index-repeat')
        self.assertTrue(second['ok'], second)
        self.assertEqual(second, first)
        self.assertEqual((self.output.read_bytes(), self.output.stat().st_mtime_ns), before)

    def test_reused_request_preserves_later_source_and_cache_changes(self):
        first = self.service('synthetic-index-source-change')
        self.assertTrue(first['ok'], first)
        before = self.output.read_bytes(), self.output.stat().st_mtime_ns
        self.source.write_text('# Synthetic later index source\n')
        changed = self.service('synthetic-index-source-change')
        self.assertFalse(changed['ok'], changed)
        self.assertEqual((self.output.read_bytes(), self.output.stat().st_mtime_ns), before)
        fresh = self.service('synthetic-index-cache-change')
        self.assertTrue(fresh['ok'], fresh)
        value = json.loads(self.output.read_text())
        value['generated_at'] = '2026-10-08T00:00:00Z'
        self.output.write_text(json.dumps(value))
        before = self.output.read_bytes(), self.output.stat().st_mtime_ns
        changed = self.service('synthetic-index-cache-change')
        self.assertFalse(changed['ok'], changed)
        self.assertEqual((self.output.read_bytes(), self.output.stat().st_mtime_ns), before)

    def test_read_only_owner_can_query_but_cannot_publish(self):
        self.configuration.update(lambda value: [grant.update(write=[]) for grant in value['destinations'].values()])
        result = self.call('--query', 'TELOS/GOALS.md')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('SyntheticPublishedIndexGoal', result.stdout)
        self.assertFalse(self.output.exists())
        result = self.call('--json')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.output.exists())

    def test_missing_connector_and_redirected_cache_refuse_before_publication(self):
        marker = self.root / 'LIFEOS/USER/CONFIG/memory-http.json'
        marker.write_text(json.dumps({'version': 1, 'managed': True}))
        marker.chmod(0o600)
        connector = self.root / 'LIFEOS/USER/CONFIG/memory-access.json'
        data = connector.read_bytes()
        connector.unlink()
        result = self.call('--json')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.output.exists())
        connector.write_bytes(data)
        connector.chmod(0o600)
        self.output.parent.mkdir()
        external = self.root.parent / 'synthetic-external-index.json'
        external.write_text('{}')
        self.output.symlink_to(external)
        result = self.call('--json')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(external.read_text(), '{}')

    def test_actual_process_interruption_recovers_previous_cache_and_preserves_sources(self):
        first = self.service('synthetic-index-before-interruption')
        self.assertTrue(first['ok'], first)
        before = self.output.read_bytes(), self.output.stat().st_mode & 0o777
        self.source.write_text('# SyntheticChangedIndexBeforeInterrupt\n')
        changed = self.source.read_bytes()
        result = subprocess.run([sys.executable, str(Path(__file__).with_name('memory_user_index_interrupt.py')),
            str(self.configuration.path), json.dumps(asdict(self.fixture.context))], capture_output=True, text=True,
            timeout=40, env=dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1])))
        self.assertEqual(result.returncode, 86, result.stderr)
        self.assertEqual(result.stdout + result.stderr, '')
        self.assertTrue(self.memory.transaction.journal.exists())
        recovered = self.service('synthetic-index-after-interruption', publish=False)
        self.assertTrue(recovered['ok'], recovered)
        self.assertEqual((self.output.read_bytes(), self.output.stat().st_mode & 0o777), before)
        self.assertEqual(self.source.read_bytes(), changed)
        self.assertFalse(self.memory.transaction.journal.exists())

    def test_changes_after_actual_rendering_refuse_before_publication(self):
        for mode in ('source', 'authority'):
            with self.subTest(mode=mode):
                result = subprocess.run([sys.executable,
                    str(Path(__file__).with_name('memory_user_index_render_process.py')),
                    str(self.configuration.path), json.dumps(asdict(self.fixture.context)), mode],
                    capture_output=True, text=True, timeout=40,
                    env=dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1])))
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stderr, '')
                self.assertEqual(json.loads(result.stdout), {'rendered': True, 'withheld': True})
                self.assertFalse(self.output.exists())

    def test_hardlinked_cache_refuses_without_changing_either_link(self):
        self.output.parent.mkdir()
        self.output.write_text('{}')
        alias = self.root.parent / 'synthetic-index-cache-alias.json'
        os.link(self.output, alias)
        before = self.output.read_bytes(), self.output.stat().st_mtime_ns
        result = self.call('--json')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((self.output.read_bytes(), self.output.stat().st_mtime_ns), before)
        self.assertEqual(alias.read_text(), '{}')

    def test_native_stats_keep_the_original_format_and_publish_privately(self):
        result = self.call('--stats')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        expected = json.loads(self.output.read_text())
        self.assertIn('Total files: ' + str(expected['stats']['total_files']), result.stdout)
        self.assertIn('Avg completeness: ' + str(expected['stats']['avg_completeness']) + '%', result.stdout)
        self.assertIn('Index written to: ' + str(self.output), result.stdout)
        self.assertEqual(self.output.stat().st_mode & 0o777, 0o600)
        (self.root / 'LIFEOS/USER/CONFIG/memory-access.json').unlink()
        unmanaged = self.call('--stats', context=False)
        self.assertEqual(unmanaged.returncode, 0, unmanaged.stderr)
        self.assertEqual(unmanaged.stderr, '')
        normalize = lambda text: '\n'.join(line for line in text.splitlines() if not line.startswith('Generated:'))
        self.assertEqual(normalize(unmanaged.stdout), normalize(result.stdout))

    def test_actual_native_watcher_publishes_changes_then_preserves_cache_after_revocation(self):
        environment = dict(os.environ, HOME=str(self.root.parent), LIFEOS_DIR=str(self.root / 'LIFEOS'),
            BUN_CONFIG_NO_AUTO_INSTALL='1', LIFEOS_MEMORY_CONTEXT=json.dumps(asdict(self.fixture.context)))
        environment.pop('LIFEOS_MEMORY_INTERNAL', None)
        with tempfile.TemporaryFile(mode='w+') as output, tempfile.TemporaryFile(mode='w+') as errors:
            process = subprocess.Popen(['bun', '--no-install',
                str(self.root / 'LIFEOS/PULSE/modules/user-index.ts'), '--watch'],
                env=environment, stdout=output, stderr=errors)
            def wait_until(predicate):
                deadline = time.monotonic() + 20
                while time.monotonic() < deadline:
                    if predicate(): return
                    if process.poll() is not None: break
                    time.sleep(0.05)
                output.seek(0)
                errors.seek(0)
                self.fail('Native watcher did not reach its expected state: ' + output.read() + errors.read())
            def log_contains(stream, text):
                stream.seek(0)
                return text in stream.read()
            try:
                wait_until(lambda: self.output.exists() and log_contains(output, 'Watching '))
                self.source.write_text('# SyntheticWatchedIndexGoal\n')
                wait_until(lambda: 'SyntheticWatchedIndexGoal' in self.output.read_text())
                self.assertEqual(self.output.stat().st_mode & 0o777, 0o600)
                before = self.output.read_bytes(), self.output.stat().st_mtime_ns
                self.configuration.update(lambda value: value['accounts'].clear())
                self.source.write_text('# SyntheticRevokedWatchGoal\n')
                wait_until(lambda: log_contains(errors, 'Reindex failed:'))
                self.assertEqual((self.output.read_bytes(), self.output.stat().st_mtime_ns), before)
                self.assertNotIn('SyntheticRevokedWatchGoal', self.output.read_text())
                process.send_signal(signal.SIGINT)
                self.assertEqual(process.wait(timeout=10), 0)
                output.seek(0)
                self.assertIn('Stopping...', output.read())
                errors.seek(0)
                failure = errors.read()
                self.assertIn('Reindex failed:', failure)
                self.assertNotIn('watch error', failure)
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait(timeout=10)


if __name__ == '__main__':
    unittest.main()
