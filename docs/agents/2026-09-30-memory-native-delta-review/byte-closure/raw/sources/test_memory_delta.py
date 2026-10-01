# ABOUTME: Verifies registered turn-start summaries use current memory authority.
# ABOUTME: Runs native composers and log readers with disposable facts and cursor state.

from dataclasses import asdict, replace
import json
import os
import subprocess
import unittest

import test_memory_delegation as delegation_fixture
from test_memory_native import OWNER


class MemoryDeltaTests(unittest.TestCase):
    def setUp(self):
        self.fixture = delegation_fixture.MemoryDelegationTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        self.memory = self.fixture.fixture.memory
        self.obs = self.root / 'LIFEOS/MEMORY/OBSERVABILITY'

    def call(self, *, context=True, standalone=False, timeout=45):
        environment = dict(os.environ, HOME=str(self.fixture.fixture.home), BUN_CONFIG_NO_AUTO_INSTALL='1')
        for name in ('LIFEOS_MEMORY_INTERNAL', 'LIFEOS_MEMORY_CONTEXT', 'CLAUDE_AGENT_TYPE',
                     'CLAUDE_CODE_SUBAGENT_NAME', 'CLAUDE_CODE_SUBAGENT_TYPE', 'CLAUDE_CODE_FORK_SUBAGENT',
                     'CLAUDE_AGENT_SDK', 'CLAUDE_PROJECT_DIR'):
            environment.pop(name, None)
        if context:
            environment['LIFEOS_MEMORY_CONTEXT'] = json.dumps(asdict(self.fixture.context))
        script = 'MemoryDeltaSurface.hook.ts' if standalone else 'MemoryTurnStart.hook.ts'
        result = subprocess.run(['bun', '--no-install', str(self.root / 'hooks' / script)],
                                input=json.dumps({'session_id': 'delta-session', 'prompt': 'memory'}),
                                env=environment, cwd=self.root, capture_output=True, text=True, timeout=timeout)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        return result.stdout

    def remember(self, marker, request):
        return self.fixture.fixture.remember('RULE: ' + marker, request, 'principal')

    def test_authorized_updates_and_native_heartbeat_still_surface(self):
        self.remember('Synthetic current delta marker', 'current')
        first = self.call()
        self.assertIn('+1 learned', first)
        self.assertIn('Synthetic current delta marker', first)
        self.assertIn('<lifeos-memory>', first)
        second = self.call()
        self.assertIn('<lifeos-memory-delta>', second)
        self.assertIn('last curation', second)
        self.assertNotIn('+1 learned', second)

    def test_unmanaged_turn_start_keeps_native_log_behavior(self):
        self.remember('Synthetic unmanaged delta marker', 'unmanaged')
        (self.root / 'LIFEOS/USER/CONFIG/memory-access.json').unlink()
        self.assertIn('Synthetic unmanaged delta marker', self.call(context=False))

    def test_registered_composer_excludes_forgotten_log_claims_and_keeps_current_rows(self):
        saved = self.remember('Synthetic forgotten delta marker', 'forgotten')
        self.memory.forget(OWNER, saved['reference'], 'forget-delta')
        self.remember('Synthetic current delta marker', 'current')
        output = self.call()
        self.assertNotIn('Synthetic forgotten delta marker', output)
        self.assertIn('Synthetic current delta marker', output)
        self.assertIn('+1 learned', output)
        self.assertIn('Synthetic forgotten delta marker', (self.obs / 'memory-writes.jsonl').read_text())

    def test_standalone_delta_excludes_superseded_log_claims(self):
        saved = self.remember('Synthetic superseded delta marker', 'prior')
        self.memory.correct(OWNER, saved['reference'], 'RULE: Synthetic corrected delta marker', 'correct-delta')
        self.remember('Synthetic next delta marker', 'next')
        output = self.call(standalone=True)
        self.assertNotIn('Synthetic superseded delta marker', output)
        self.assertIn('Synthetic next delta marker', output)

    def test_missing_context_does_not_consume_cursor_or_injection_state(self):
        self.remember('Synthetic private delta marker', 'private')
        self.assertEqual(self.call(context=False), '')
        self.assertFalse((self.obs / 'memory-delta-cursor.json').exists())
        self.assertFalse((self.root / 'LIFEOS/MEMORY/STATE/memory-inject/delta-session.json').exists())
        authorized = self.call()
        self.assertIn('<lifeos-memory>', authorized)
        self.assertIn('+1 learned', authorized)

    def test_standalone_delta_refuses_missing_context(self):
        self.remember('Synthetic private standalone marker', 'standalone')
        self.assertEqual(self.call(context=False, standalone=True), '')
        self.assertFalse((self.obs / 'memory-delta-cursor.json').exists())

    def test_invalid_connector_cannot_fall_back_to_native_log(self):
        self.remember('Synthetic invalid connector delta marker', 'invalid')
        (self.root / 'LIFEOS/USER/CONFIG/memory-access.json').write_text('{invalid')
        self.assertEqual(self.call(), '')
        self.assertFalse((self.obs / 'memory-delta-cursor.json').exists())

    def test_restricted_destination_cannot_read_unclassified_log(self):
        self.remember('Synthetic restricted delta marker', 'restricted')
        configuration = self.fixture.configuration.load()
        configuration['destinations']['chat-a:200'].update(read=['project'], projects=['lab'])
        self.fixture.configuration.save(configuration)
        self.assertEqual(self.call(), '')

    def test_unknown_author_and_changed_participants_cannot_surface_private_status(self):
        self.remember('Synthetic unidentified delta marker', 'unidentified')
        original = self.fixture.context
        for context in (replace(original, author='unknown'), replace(original, participants=('other',))):
            with self.subTest(context=context):
                self.fixture.context = context
                self.assertEqual(self.call(), '')
                self.assertFalse((self.obs / 'memory-delta-cursor.json').exists())

    def test_denied_turn_preserves_existing_native_state(self):
        self.remember('Synthetic admitted cursor marker', 'admitted')
        self.call()
        paths = (self.obs / 'memory-delta-cursor.json',
                 self.root / 'LIFEOS/MEMORY/STATE/memory-inject/delta-session.json',
                 self.root / 'LIFEOS/MEMORY/STATE/delta-surface-heartbeat')
        before = {path: path.read_bytes() for path in paths}
        self.assertEqual(self.call(context=False), '')
        self.assertEqual(before, {path: path.read_bytes() for path in paths})

    def test_log_and_cache_redirects_cannot_read_configuration(self):
        self.remember('Synthetic permitted redirect marker', 'redirect')
        secret = self.root / 'LIFEOS/USER/CONFIG/synthetic-secret.json'
        secret.write_text(json.dumps({'overall_grade': 'Synthetic configuration-only marker'}))
        cache = self.root / 'LIFEOS/USER/CACHE/freshness.json'
        cache.parent.mkdir(parents=True)
        cache.symlink_to(secret)
        output = self.call()
        self.assertNotIn('Synthetic configuration-only marker', output)
        self.assertIn('Synthetic permitted redirect marker', output)
        log = self.obs / 'memory-writes.jsonl'
        log.unlink()
        log.symlink_to(secret)
        result = self.fixture.call([{'name': 'load'}])
        self.assertNotIn('Synthetic configuration-only marker', str(result))
        from lifeos_hook_bridge.memory_service import MemoryService
        denied = MemoryService(self.fixture.configuration).native(self.fixture.context, 'read_source', {'path': str(log)})
        self.assertFalse(denied['ok'], denied)

    def test_decoded_log_claims_are_filtered_without_changing_raw_evidence(self):
        saved = self.remember('Synthetic forgotten escaped delta marker', 'escaped')
        self.memory.forget(OWNER, saved['reference'], 'forget-escaped')
        self.remember('Synthetic current escaped control', 'control')
        log = self.obs / 'memory-writes.jsonl'
        rows = log.read_text().splitlines()
        row = json.loads(rows[-1])
        row['additions'] = ['RULE: Synthetic forgotten\nescaped delta marker']
        log.write_text(json.dumps(row) + '\n' + rows[-1] + '\n')
        before = log.read_bytes()
        output = self.call()
        self.assertNotIn('Synthetic forgotten', output)
        self.assertIn('Synthetic current escaped control', output)
        self.assertEqual(log.read_bytes(), before)

    def test_health_and_freshness_retained_text_is_filtered(self):
        saved = self.remember('Synthetic forgotten diagnostic marker', 'diagnostic')
        self.memory.forget(OWNER, saved['reference'], 'forget-diagnostic')
        cache = self.root / 'LIFEOS/USER/CACHE/freshness.json'
        cache.parent.mkdir(parents=True)
        cache.write_text(json.dumps({'overall_grade': 'F', 'fresh_count': 0, 'total': 8,
                                     'most_stale': {'name': 'Synthetic forgotten diagnostic marker', 'grade': 'F'}}))
        (self.obs / 'memory-health.jsonl').write_text(json.dumps({'overall': 'critical', 'findings': [
            {'severity': 'critical', 'message': 'Synthetic forgotten diagnostic marker'}]}) + '\n')
        output = self.call()
        self.assertNotIn('Synthetic forgotten diagnostic marker', output)
        self.assertIn('<lifeos-memory-delta>', output)

    def test_authorized_freshness_and_health_remain_visible(self):
        self.remember('Synthetic current status marker', 'status')
        cache = self.root / 'LIFEOS/USER/CACHE/freshness.json'
        cache.parent.mkdir(parents=True)
        cache.write_text(json.dumps({'overall_grade': 'C', 'fresh_count': 5, 'total': 8}))
        (self.obs / 'memory-health.jsonl').write_text(json.dumps({'overall': 'critical', 'findings': [
            {'severity': 'critical', 'message': 'Synthetic current health finding'}]}) + '\n')
        output = self.call()
        self.assertIn('C (5/8 fresh)', output)
        self.assertIn('Synthetic current health finding', output)

    def test_native_tail_window_finishes_within_registered_hook_timeout(self):
        self.remember('Synthetic bounded volume marker', 'volume')
        log = self.obs / 'memory-writes.jsonl'
        row = log.read_text().splitlines()[-1]
        log.write_text((row + '\n') * 1000)
        output = self.call(timeout=8)
        self.assertIn('+500 learned', output)
        self.assertIn('Synthetic bounded volume marker', output)

    def test_malformed_write_row_does_not_hide_later_current_updates(self):
        self.remember('Synthetic valid row shape marker', 'shape')
        log = self.obs / 'memory-writes.jsonl'
        valid = log.read_text().splitlines()[-1]
        row = json.loads(valid)
        row['additions'] = 'Synthetic invalid array shape'
        log.write_text(json.dumps(row) + '\n' + valid + '\n')
        output = self.call()
        self.assertIn('+1 learned', output)
        self.assertIn('Synthetic valid row shape marker', output)

    def test_full_native_curation_rows_fit_the_connector_response_budget(self):
        entries = [f'RULE: Synthetic capacity record {index:02} ' + ('archive detail ' * 14).strip()
                   for index in range(40)]
        snapshot = self.memory.read_hot(OWNER, 'principal')
        saved = self.memory.native_set(OWNER, 'principal', entries, 'capacity', snapshot['revision'])
        self.assertTrue(saved['ok'], saved)
        log = self.obs / 'memory-writes.jsonl'
        native_row = log.read_text().splitlines()[-1]
        self.remember('Synthetic current byte control', 'byte-control')
        control = log.read_text().splitlines()[-1]
        log.write_text((native_row + '\n') * 499 + control + '\n')
        output = self.call(standalone=True, timeout=8)
        self.assertIn('+1 learned', output)
        self.assertIn('Synthetic current byte control', output)
        from lifeos_hook_bridge.memory_service import MemoryService
        result = MemoryService(self.fixture.configuration).native(self.fixture.context, 'read_source', {'path': str(log)})
        self.assertTrue(result['ok'], result)
        self.assertLess(len((json.dumps(result) + '\n').encode()), 4 * 1024 * 1024)

    def test_summary_projection_preserves_curation_counts_and_native_sample_order(self):
        entries = [f'RULE: Synthetic summarized curation entry {index}' for index in range(40)]
        snapshot = self.memory.read_hot(OWNER, 'principal')
        saved = self.memory.native_set(OWNER, 'principal', entries, 'summary-capacity', snapshot['revision'])
        self.assertTrue(saved['ok'], saved)
        log = self.obs / 'memory-writes.jsonl'
        row = json.loads(log.read_text().splitlines()[-1])
        row['updated_by'] = 'MemorySystem.add'
        log.write_text(json.dumps(row) + '\n')
        output = self.call(standalone=True)
        self.assertIn('+40 learned', output)
        self.assertIn('Synthetic summarized curation entry 0', output)
        self.assertIn('Synthetic summarized curation entry 1', output)
        self.assertNotIn('Synthetic summarized curation entry 2', output)
        heartbeat = self.call(standalone=True)
        self.assertIn('last curation +40 new', heartbeat)

    def test_excluded_latest_health_does_not_replay_older_critical_warning(self):
        from datetime import datetime, timezone
        saved = self.remember('Synthetic retired health detail', 'retired-health')
        self.memory.forget(OWNER, saved['reference'], 'forget-health')
        self.remember('Synthetic latest health control', 'health-control')
        ts = datetime.now(timezone.utc).isoformat()
        log = self.obs / 'memory-health.jsonl'
        log.write_text(json.dumps({'ts': ts, 'overall': 'critical', 'findings': [
            {'severity': 'critical', 'message': 'Synthetic obsolete critical warning'}]}) + '\n' +
            json.dumps({'ts': ts, 'overall': 'ok', 'findings': [
                {'severity': 'ok', 'message': 'Synthetic retired health detail'}]}) + '\n')
        output = self.call()
        self.assertNotIn('Synthetic obsolete critical warning', output)
        self.assertNotIn('Synthetic retired health detail', output)
        self.assertNotIn('MEMORY HEALTH: CRITICAL', output)
        self.assertIn('Synthetic latest health control', output)


if __name__ == '__main__':
    unittest.main()
