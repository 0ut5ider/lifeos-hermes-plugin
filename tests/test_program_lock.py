# ABOUTME: Checks that LifeOS turns and program swaps exclude each other across processes.
# ABOUTME: Holds the real per-profile file lock from separate child processes.
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from lifeos_hook_bridge import program_lock
from lifeos_hook_bridge.bridge import HookBridge

ROOT = Path(__file__).resolve().parents[1]
HOLDER = ('import sys, time\nfrom pathlib import Path\nfrom lifeos_hook_bridge import program_lock\n'
          'mode, profile = sys.argv[1], Path(sys.argv[2])\n'
          'if mode == "shared":\n descriptor = program_lock.shared(profile)\n print("held" if descriptor else "busy", flush=True)\n'
          'else:\n stack = program_lock.exclusive(profile, 5)\n stack.__enter__()\n print("held", flush=True)\n'
          'sys.stdin.read()\n')


class ProgramLockTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.profile = self.root / '.hermes'
        self.profile.mkdir(mode=0o700)

    def hold(self, mode):
        process = subprocess.Popen([sys.executable, '-c', HOLDER, mode, str(self.profile)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True,
            env={**os.environ, 'PYTHONPATH': str(ROOT)})
        self.addCleanup(process.wait, 10)
        self.addCleanup(process.stdin.close)
        self.assertEqual(process.stdout.readline().strip(), 'held')
        return process

    def bridge(self, hooks=None):
        settings = self.root / 'settings.json'
        settings.write_text(json.dumps({'hooks': hooks or {}}))
        bridge = HookBridge(settings, self.root, profile=self.profile, hold_turns=True)
        self.addCleanup(bridge.close)
        return bridge

    def test_exclusive_waits_for_shared_holder_and_times_out(self):
        self.hold('shared')
        with self.assertRaisesRegex(program_lock.ProgramBusy, 'still running'):
            with program_lock.exclusive(self.profile, 0.5):
                pass

    def test_exclusive_proceeds_after_turn_releases(self):
        descriptor = program_lock.shared(self.profile)
        program_lock.release(descriptor)
        with program_lock.exclusive(self.profile, 0.5):
            self.assertIsNone(program_lock.shared(self.profile))

    def test_turn_is_refused_while_program_swap_holds_the_lock(self):
        marker = self.root / 'ran'
        hook = f'{sys.executable} -c "open({str(marker)!r}, \'w\').close()"'
        bridge = self.bridge({'UserPromptSubmit': [{'hooks': [{'type': 'command', 'command': hook}]}]})
        self.hold('exclusive')
        result = bridge.pre_llm_call('hello', session_id='session')
        self.assertEqual(result, {'action': 'block', 'message': program_lock.BUSY_MESSAGE})
        self.assertFalse(marker.exists())

    def test_admitted_turn_blocks_program_swap_until_turn_end(self):
        bridge = self.bridge()
        bridge.pre_llm_call('hello', session_id='session')
        with self.assertRaises(program_lock.ProgramBusy):
            with program_lock.exclusive(self.profile, 0.3):
                pass
        bridge.turn_end(session_id='session')
        with program_lock.exclusive(self.profile, 0.3):
            pass

    def test_unpatched_host_does_not_hold_the_lock_after_admission(self):
        settings = self.root / 'settings.json'
        settings.write_text(json.dumps({'hooks': {}}))
        bridge = HookBridge(settings, self.root, profile=self.profile)
        self.addCleanup(bridge.close)
        self.assertIsNone(bridge.pre_llm_call('hello', session_id='session'))
        with program_lock.exclusive(self.profile, 0.3):
            pass


if __name__ == '__main__':
    unittest.main()
