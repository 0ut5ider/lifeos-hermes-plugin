# ABOUTME: Checks child callback correlation using the actual native delegation tracker.
# ABOUTME: Keeps repeated callbacks, concurrent children, and parent dispatch distinct.
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest

from lifeos_hook_bridge.bridge import HookBridge

SOURCE = os.environ.get('LIFEOS_GUARD_SOURCE')


@unittest.skipUnless(SOURCE and shutil.which('bun'), 'Prepared native delegation tracker and Bun are required')
class ChildLifecycleTests(unittest.TestCase):
    def test_callbacks_record_one_start_and_one_stop_per_actual_child_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            root = home / '.claude'
            root.mkdir()
            (root / 'hooks').symlink_to(Path(SOURCE) / 'hooks', target_is_directory=True)
            settings = root / 'settings.json'
            settings.write_text(json.dumps({'hooks': {event: [{'matcher': 'Agent', 'hooks': [
                {'type': 'command', 'command': 'bun ' + str(root / 'hooks/AgentInvocation.hook.ts')}]}]
                for event in ('PreToolUse', 'PostToolUse')}}))
            bridge = HookBridge(settings, root, lifeos_home=home)
            self.addCleanup(bridge.close)
            bridge.child_lifecycle_enabled = True
            args = {'goal': 'Same goal for each child', 'background': True}
            self.assertIsNone(bridge.pre_tool_call('delegate_task', args, session_id='parent', tool_call_id='call'))
            count = 8
            def run(index):
                values = {'parent_session_id': 'parent', 'child_session_id': 'child-' + str(index),
                    'child_goal': args['goal'], 'child_role': 'leaf', 'child_model': 'private-child-model',
                    'child_provider': 'custom', 'child_requested_model': 'haiku' if index % 2 == 0 else '',
                    'child_reasoning_config': {'effort': 'low' if index % 2 == 0 else 'xhigh'}}
                bridge.child_start(**values)
                bridge.child_start(**values)
                bridge.observe_api_response(session_id=values['child_session_id'], response_model='actual-child-model', provider='private')
                bridge.child_stop(parent_session_id='other-parent', child_session_id=values['child_session_id'],
                                  child_status='completed', child_summary='WRONG')
                bridge.child_stop(parent_session_id='parent', child_session_id=values['child_session_id'],
                                  child_status='completed' if index % 2 == 0 else 'error', child_summary='ACTUAL_FIXTURE_SUMMARY')
                bridge.child_stop(parent_session_id='parent', child_session_id=values['child_session_id'],
                                  child_status='completed', child_summary='DUPLICATE')
            with ThreadPoolExecutor(max_workers=4) as workers:
                list(workers.map(run, range(count)))
            bridge.post_tool_call('delegate_task', args, json.dumps({'status':'dispatched','mode':'background'}),
                                  session_id='parent', tool_call_id='call')
            rows = [json.loads(line) for line in (root / 'LIFEOS/MEMORY/OBSERVABILITY/subagent-events.jsonl').read_text().splitlines()]
            starts = [row for row in rows if row['event'] == 'subagent_start']
            stops = [row for row in rows if row['event'] == 'subagent_stop']
            self.assertEqual(len(starts), count)
            self.assertEqual(len(stops), count)
            self.assertEqual({row['subagent_id'] for row in starts}, {row['subagent_id'] for row in stops})
            self.assertEqual(len({row['subagent_id'] for row in starts}), count)
            self.assertTrue(all(row['subagent_model'] == 'private-child-model' for row in starts))
            self.assertEqual(sum(row.get('subagent_requested_model') == 'haiku' for row in starts), 4)
            self.assertEqual({row.get('subagent_reasoning_effort') for row in starts}, {'low', 'xhigh'})
            self.assertEqual(sum(row['subagent_level'] == 'session-inherited' for row in starts), 4)
            self.assertTrue(all(row.get('subagent_observed_model') == 'actual-child-model' for row in stops), stops)
            self.assertEqual(json.loads((root / 'LIFEOS/MEMORY/OBSERVABILITY/agent-starts.json').read_text()), {})
            bridge.child_start(parent_session_id='parent', child_session_id='unobserved', child_goal='No response model')
            bridge.observe_api_response(session_id='unobserved', model='requested-alias', provider='custom')
            bridge.child_stop(parent_session_id='parent', child_session_id='unobserved', child_status='completed')
            last = json.loads((root / 'LIFEOS/MEMORY/OBSERVABILITY/subagent-events.jsonl').read_text().splitlines()[-1])
            self.assertNotIn('subagent_observed_model', last)
