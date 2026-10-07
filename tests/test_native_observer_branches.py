# ABOUTME: Exercises installed observer branches against real files, processes, and transcripts.
# ABOUTME: Measures loop thresholds, audit truncation, parallel rows, and source-specific baselines.
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import unittest

from lifeos_hook_bridge.bridge import HookBridge

SOURCE = os.environ.get('LIFEOS_GUARD_SOURCE')


@unittest.skipUnless(SOURCE and shutil.which('bun'), 'Installed LifeOS observers and Bun are required')
class NativeObserverBranchesTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix='observer-branches-')
        self.addCleanup(directory.cleanup)
        self.home = Path(directory.name)
        self.root = self.home / '.claude'
        self.root.mkdir()
        self.lifeos = self.root / 'LIFEOS'
        self.settings = self.root / 'settings.json'
        self.settings.write_text('{}')
        self.source = Path(SOURCE)
        self.env = {**os.environ, 'HOME': str(self.home), 'LIFEOS_DIR': str(self.lifeos), 'LIFEOS_NOTIFICATION_CHANNEL': 'headless'}

    def native(self, program, payload):
        run = subprocess.run(['bun', str(self.source / 'hooks' / (program + '.hook.ts'))],
                             input=json.dumps(payload), capture_output=True, text=True, env=self.env, timeout=20)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertNotIn('Error:', run.stderr)
        return run

    def observer(self, session, sequence):
        outputs = []
        for tool, args, failed in sequence:
            payload = {'hook_event_name': 'PostToolUseFailure' if failed else 'PostToolUse',
                       'session_id': session, 'tool_name': tool, 'tool_input': args}
            if failed:
                actual = subprocess.run(['sh', '-c', 'exit 1'], capture_output=True, text=True)
                self.assertEqual(actual.returncode, 1)
                payload['error'] = 'Exit code ' + str(actual.returncode)
            result = self.native('PostToolObserver', payload)
            outputs.append(json.loads(result.stdout).get('hookSpecificOutput', {}).get('additionalContext', '') if result.stdout else '')
        state = json.loads((self.lifeos / 'MEMORY/STATE/loop-detector' / (session + '.json')).read_text())
        self.assertEqual(state['seq'], len(sequence))
        return outputs, state

    def test_full_observer_exact_repeat_and_episode_deduplication(self):
        outputs, state = self.observer('exact', [('Read', {'file_path': '/fixture'}, False)] * 7)
        self.assertEqual([i for i, output in enumerate(outputs) if '[LOOP DETECTED]' in output], [2])
        self.assertEqual(len(state['alerted']), 1)

    def test_oscillation_and_cooldown_preserve_threshold(self):
        sequence = [('Read', {'file_path': '/a' if i % 2 == 0 else '/b'}, False) for i in range(8)]
        outputs, state = self.observer('oscillation', sequence)
        self.assertIn('flip-flopping', outputs[3])
        self.assertFalse(any('[LOOP DETECTED]' in out for out in outputs[4:7]))
        self.assertIn('[LOOP DETECTED]', outputs[7])
        self.assertEqual(state['lastAlert'], 8)

    def test_failure_hammering_and_parallel_session_history(self):
        def check(index):
            outputs, state = self.observer('parallel-' + str(index), [('Bash', {'command': 'false #' + str(i)}, i < 3) for i in range(5)])
            self.assertIn('3 failed', outputs[4])
            self.assertEqual(sum(row['failed'] for row in state['window']), 3)
        with ThreadPoolExecutor(max_workers=4) as workers:
            list(workers.map(check, range(4)))

    def test_system_surface_reads_actual_isa_and_preserves_other_session(self):
        isa = self.home / 'project/ISA.md'
        isa.parent.mkdir()
        isa.write_text('- [ ] ISC-1: Fixture\n')
        payload = {'hook_event_name': 'PostToolUse', 'session_id': 'surface', 'tool_name': 'Write',
                   'tool_input': {'file_path': str(isa)}, 'tool_response': {'success': True}}
        first = self.native('PostToolObserver', payload)
        self.assertIn('0 closed', first.stdout)
        isa.write_text('- [x] ISC-1: Fixture\n')
        second = self.native('PostToolObserver', {**payload, 'tool_name': 'Edit'})
        self.assertIn('0→1', second.stdout)
        self.native('PostToolObserver', {**payload, 'session_id': 'other'})
        ledger = json.loads((self.lifeos / 'MEMORY/STATE/system-delta-surface.json').read_text())
        self.assertEqual(len(ledger['entries']), 2)
        self.assertEqual(ledger['entries'][-1]['detail'], '0→1')

    def test_config_deletion_and_malformed_source_retain_prior_baseline(self):
        audit = self.lifeos / 'MEMORY/OBSERVABILITY/config-changes.jsonl'
        for index, source in enumerate(('user_settings', 'project_settings', 'local_settings', 'skills')):
            target = self.home / ('config-' + str(index))
            original = 'skill baseline' if source == 'skills' else '{"env":{"FIXTURE":"baseline"}}'
            target.write_text(original)
            payload = {'hook_event_name': 'ConfigChange', 'session_id': 'configuration', 'source': source, 'file_path': str(target)}
            self.native('EventLogger', payload)
            self.assertEqual(json.loads(audit.read_text().splitlines()[-1])['config_key'], 'initial')
            target.unlink()
            self.native('EventLogger', payload)
            deleted = json.loads(audit.read_text().splitlines()[-1])
            self.assertEqual(deleted['change_summary'], 'could not read configuration file')
            if source != 'skills':
                target.write_text('{')
                self.native('EventLogger', payload)
                self.assertEqual(json.loads(audit.read_text().splitlines()[-1])['change_summary'], 'could not read configuration file')
            target.write_text(original)
            self.native('EventLogger', payload)
            self.assertEqual(json.loads(audit.read_text().splitlines()[-1])['config_key'], 'unchanged')

    def test_audit_failures_keep_actual_error_and_exact_truncation(self):
        error = 'actual-fixture-error-' + 'x' * 1200
        # Model terminal failures and MCP failures are event contracts, not provider emulation.
        for tool in ('Bash', 'Write', 'mcp__fixture__failed', 'Model'):
            self.native('EventLogger', {'hook_event_name': 'PostToolUseFailure', 'session_id': 'failed',
                                       'tool_name': tool, 'error': error, 'tool_input': {'value': 'y' * 700}})
        rows = [json.loads(line) for line in (self.lifeos / 'MEMORY/OBSERVABILITY/tool-failures.jsonl').read_text().splitlines()]
        self.assertEqual([row['tool_name'] for row in rows], ['Bash', 'Write', 'mcp__fixture__failed', 'Model'])
        self.assertTrue(all(row['error'] == error[:1000] for row in rows))
        self.assertTrue(all(len(row['tool_input_preview']) == 503 and row['tool_input_preview'].endswith('...') for row in rows))

    def test_parallel_async_logging_survives_bridge_close_with_complete_rows(self):
        hook = self.source / 'hooks/EventLogger.hook.ts'
        self.settings.write_text(json.dumps({'hooks': {'PostToolUse': [{'hooks': [
            {'type': 'command', 'command': 'bun ' + str(hook), 'async': True}]}]}}))
        bridge = HookBridge(self.settings, self.root, lifeos_home=self.home)
        bridge.environment.update(self.env)
        count = 24
        with ThreadPoolExecutor(max_workers=4) as workers:
            list(workers.map(lambda index: bridge.post_tool_call('terminal', {'command': 'true #' + str(index)},
                json.dumps({'output': '', 'exit_code': 0}), session_id='audit-' + str(index), tool_call_id='call-' + str(index)), range(count)))
        bridge.close()
        target = self.lifeos / 'MEMORY/OBSERVABILITY/tool-activity.jsonl'
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            if target.exists() and len(target.read_text().splitlines()) == count:
                break
            time.sleep(.05)
        rows = [json.loads(line) for line in target.read_text().splitlines()]
        self.assertEqual(len(rows), count)
        self.assertEqual({row['session_id'] for row in rows}, {'audit-' + str(i) for i in range(count)})
        self.assertTrue(all(row['ground_truth']['exit_code'] == 0 for row in rows))
