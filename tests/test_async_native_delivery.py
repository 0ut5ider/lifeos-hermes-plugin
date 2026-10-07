# ABOUTME: Measures native clock output queued by real detached hook processes.
# ABOUTME: Checks clock coalescing separately from ordinary asynchronous hook context.
import json
from dataclasses import asdict
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

from lifeos_hook_bridge.bridge import HookBridge, _native_post_hook

SOURCE = os.environ.get('LIFEOS_GUARD_SOURCE')


@unittest.skipUnless(SOURCE and shutil.which('bun'), 'Prepared native clock and Bun are required')
class AsyncNativeDeliveryTests(unittest.TestCase):
    def test_clock_does_not_read_managed_records_or_borrow_revoked_authority(self):
        from test_memory_delegation import MemoryDelegationTests
        from lifeos_hook_bridge.memory_service import MemoryService
        fixture = MemoryDelegationTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        fixture.fixture.remember('RULE: SYNTHETIC_CLOCK_PRIVATE_RECORD', 'clock-record', 'principal')
        settings = fixture.root/'settings.json'
        settings.write_text(json.dumps({'principal':{'timezone':'UTC'}}))
        before = settings.read_bytes()
        for revoked in (False, True):
            with self.subTest(revoked=revoked):
                if revoked:
                    config = fixture.configuration.load()
                    config['accounts'] = {}
                    fixture.configuration.save(config)
                    result = MemoryService(fixture.configuration).call_context(fixture.context,
                        'lifeos_memory_recall', {'query':'SYNTHETIC_CLOCK_PRIVATE_RECORD'})
                    self.assertIn(result.get('status'), ('rejected', 'unavailable'))
                environment = {**os.environ,'HOME':str(fixture.fixture.home),
                    'LIFEOS_DIR':str(fixture.root/'LIFEOS'),
                    'LIFEOS_MEMORY_CONTEXT':json.dumps(asdict(fixture.context))}
                environment.pop('LIFEOS_MEMORY_INTERNAL', None)
                actual = subprocess.run(['bun',str(Path(SOURCE)/'hooks/TimeContext.hook.ts')],
                    env=environment,text=True,capture_output=True,timeout=10)
                self.assertEqual(actual.returncode, 0)
                self.assertEqual(actual.stderr, '')
                self.assertEqual(actual.stdout.count('<time-now>'), 1)
                self.assertNotIn('SYNTHETIC_CLOCK_PRIVATE_RECORD', actual.stdout)
                self.assertEqual(settings.read_bytes(), before)

    def test_only_the_latest_native_clock_reaches_the_next_turn(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            root = home / '.claude'
            root.mkdir()
            (root / 'hooks').symlink_to(Path(SOURCE) / 'hooks', target_is_directory=True)
            settings = root / 'settings.json'
            settings.write_text(json.dumps({'principal': {'timezone': 'UTC'}, 'hooks': {'UserPromptSubmit': [
                {'hooks': [{'type': 'command', 'command': 'bun $HOME/.claude/hooks/TimeContext.hook.ts', 'async': True, 'timeout': 5}]}]}}))
            bridge = HookBridge(settings, root, lifeos_home=home)
            self.addCleanup(bridge.close)
            for index in range(3):
                bridge._run('UserPromptSubmit', bridge._payload('UserPromptSubmit', 'clock', prompt='fixture-'+str(index)))
            folder = bridge._async_result_dir('clock')
            deadline = time.monotonic() + 8
            while len(list(folder.glob('*.json'))) != 3 and time.monotonic() < deadline:
                time.sleep(.02)
            self.assertEqual(len(list(folder.glob('*.json'))), 3)
            result = bridge.pre_llm_call('Collect completed clock outputs', session_id='clock')
            self.assertEqual(result['context'].count('<time-now>'), 1, result)
            self.assertEqual(list(folder.glob('*.claim')), [])
            self.assertEqual(_native_post_hook('bun $HOME/.claude/hooks/TimeContext.hook.ts', root), 'TimeContext')
            self.assertEqual(_native_post_hook('bun ${HOME}/.claude/hooks/ISASync.hook.ts', root), 'ISASync')
            self.assertEqual(_native_post_hook('bun ~/.claude/hooks/AgentInvocation.hook.ts', root), 'AgentInvocation')
            self.assertEqual(_native_post_hook('bun /other/.claude/hooks/AgentInvocation.hook.ts', root), '')
            bridge.hooks = {}
            # Retained result files are a consumer protocol control, not another native execution.
            minute = int(time.time()) // 60
            for index, (queued, completed) in enumerate(((minute-1, minute-1), (minute-1, minute), (minute+1, minute+1))):
                (folder / ('stale-'+str(index)+'.json')).write_text(json.dumps({'session_id':'clock',
                    'additionalContext':'<time-now>STALE</time-now>', 'context_kind':'clock',
                    'queued_at': queued*60, 'completed_at': completed*60}))
            (folder/'ordinary.json').write_text(json.dumps({'session_id':'clock','additionalContext':'ORDINARY_CONTEXT'}))
            next_turn = bridge.pre_llm_call('Stale clocks must expire', session_id='clock')
            self.assertEqual(next_turn, {'context':'ORDINARY_CONTEXT'})
            self.assertEqual(list(folder.glob('*.json')), [])

    def test_native_clock_survives_parent_kill_and_is_consumed_once_after_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            root = home / '.claude'
            root.mkdir()
            (root / 'hooks').symlink_to(Path(SOURCE) / 'hooks', target_is_directory=True)
            settings = root / 'settings.json'
            settings.write_text(json.dumps({'hooks': {'UserPromptSubmit': [{'hooks': [
                {'type': 'command', 'command': 'bun $HOME/.claude/hooks/TimeContext.hook.ts', 'async': True}]}]}}))
            driver = ('import os,signal\nfrom pathlib import Path\nfrom lifeos_hook_bridge.bridge import HookBridge\n'
                      f'b=HookBridge(Path({str(settings)!r}),Path({str(root)!r}),lifeos_home=Path({str(home)!r}))\n'
                      'b.pre_llm_call("Native clock before interruption",session_id="restart")\n'
                      'os.kill(os.getpid(),signal.SIGKILL)\n')
            env = dict(os.environ)
            env.pop('XDG_RUNTIME_DIR', None)
            killed = subprocess.run([sys.executable, '-c', driver], env=env, timeout=10)
            self.assertEqual(killed.returncode, -9)
            bridge = HookBridge(settings, root, lifeos_home=home)
            self.addCleanup(bridge.close)
            bridge.hooks = {}
            folder = bridge._async_result_dir('restart')
            deadline = time.monotonic() + 8
            while not list(folder.glob('*.json')) and time.monotonic() < deadline:
                time.sleep(.02)
            self.assertTrue(list(folder.glob('*.json')))
            result = bridge.pre_llm_call('Restart', session_id='restart')
            self.assertEqual(result['context'].count('<time-now>'), 1)
            self.assertIsNone(bridge.pre_llm_call('Already consumed', session_id='restart'))
