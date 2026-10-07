# ABOUTME: Measures final response publication through the actual installed native cache hook.
# ABOUTME: Separates Stop candidates from completed, failed, and interrupted Hermes turns.
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest

from lifeos_hook_bridge.bridge import HookBridge

SOURCE = os.environ.get('LIFEOS_GUARD_SOURCE')


@unittest.skipUnless(SOURCE and shutil.which('bun'), 'Prepared native response cache and Bun are required')
class NativeResponseCacheTests(unittest.TestCase):
    def fixture(self, home):
        root = home/'.claude'
        root.mkdir()
        (root/'hooks').symlink_to(Path(SOURCE)/'hooks', target_is_directory=True)
        state = root/'LIFEOS/MEMORY/STATE'
        state.mkdir(parents=True)
        settings = root/'settings.json'
        settings.write_text(json.dumps({'hooks':{'Stop':[{'hooks':[{
            'type':'command','command':'bun '+str(root/'hooks/LastResponseCache.hook.ts')}]}]}}))
        bridge = HookBridge(settings, root, lifeos_home=home)
        self.addCleanup(bridge.close)
        return bridge, state/'last-response.txt'

    def test_interrupted_stop_candidate_preserves_prior_response(self):
        with tempfile.TemporaryDirectory() as directory:
            bridge, cache = self.fixture(Path(directory))
            prior = b'PREVIOUS_COMPLETED_RESPONSE\n'
            cache.write_bytes(prior)
            bridge.stop('UNDELIVERED_CANDIDATE',session_id='interrupted')
            bridge.turn_end(session_id='interrupted',completed=False,interrupted=True,
                            final_response='UNDELIVERED_CANDIDATE')
            self.assertEqual(cache.read_bytes(), prior)

    def test_failed_turn_without_prior_response_does_not_publish_a_candidate(self):
        with tempfile.TemporaryDirectory() as directory:
            bridge, cache = self.fixture(Path(directory))
            bridge.stop('FAILED_CANDIDATE',session_id='failed')
            bridge.turn_end(session_id='failed',completed=False,failed=True,final_response='FAILED_CANDIDATE')
            self.assertFalse(cache.exists())

    def test_completed_final_response_replaces_candidate_with_exact_native_limit(self):
        for size in (17, 1999, 2000, 2001, 4200):
            with self.subTest(size=size), tempfile.TemporaryDirectory() as directory:
                bridge, cache = self.fixture(Path(directory))
                cache.write_text('PREVIOUS_COMPLETED_RESPONSE')
                bridge.stop('CANDIDATE_TO_CONTINUE',session_id='completed')
                final = 'X'*size
                bridge.turn_end(session_id='completed',completed=True,final_response=final)
                self.assertEqual(cache.read_text(), final[:2000])
                bridge.turn_end(session_id='completed',completed=True,final_response=final)
                self.assertEqual(cache.read_text(), final[:2000])

    def test_blocked_candidate_does_not_replace_prior_response(self):
        with tempfile.TemporaryDirectory() as directory:
            bridge, cache = self.fixture(Path(directory))
            cache.write_text('PREVIOUS_COMPLETED_RESPONSE')
            program = bridge.root/'reject-candidate.py'
            program.write_text('# ABOUTME: Supplies a component Stop policy decision.\n'
                               '# ABOUTME: Declares the candidate incomplete without model substitution.\n'
                               'import json\nprint(json.dumps({"decision":"block","reason":"Complete the fixture criterion"}))\n')
            import sys
            bridge.hooks['Stop'][0]['hooks'].append({'type':'command','command':sys.executable+' '+str(program)})
            decision = bridge.stop('BLOCKED_CANDIDATE',session_id='blocked')
            self.assertEqual(decision['action'],'continue')
            self.assertEqual(cache.read_text(),'PREVIOUS_COMPLETED_RESPONSE')
