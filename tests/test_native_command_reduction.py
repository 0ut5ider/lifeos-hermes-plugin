# ABOUTME: Verifies native RTK rewrites and bridge decisions with an actual RTK executable.
# ABOUTME: Uses disposable Git files and denies public pushes before execution.
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import unittest

from lifeos_hook_bridge.bridge import HookBridge


SOURCE = os.environ.get('LIFEOS_RTK_SOURCE')
BINARY = os.environ.get('LIFEOS_RTK_BINARY')


@unittest.skipUnless(SOURCE and BINARY and shutil.which('jq'), 'Native hook source, RTK, and jq are required')
class NativeCommandReductionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='lifeos-rtk-')
        self.addCleanup(self.temporary.cleanup)
        self.home = Path(self.temporary.name)
        self.root = self.home / '.claude'
        self.root.mkdir()
        self.project = self.home / 'project'
        self.project.mkdir()
        self.bin = self.home / 'bin'
        self.bin.mkdir()
        (self.bin / 'rtk').symlink_to(Path(BINARY).resolve())
        self.environment = {**os.environ, 'HOME': str(self.home),
                            'PATH': str(self.bin) + os.pathsep + os.environ['PATH'],
                            'LIFEOS_DIR': str(self.root / 'LIFEOS'),
                            'LIFEOS_NOTIFICATION_CHANNEL': 'headless'}
        for key in ('LIFEOS_MEMORY_CONTEXT', 'LIFEOS_MEMORY_INTERNAL'):
            self.environment.pop(key, None)
        self.source = Path(SOURCE)
        self.hook = self.source / 'hooks/ContextReduction.hook.sh'
        self.run_command(['git', 'init', '--quiet'])
        self.previous_cwd = Path.cwd()
        os.chdir(self.project)
        self.addCleanup(os.chdir, self.previous_cwd)

    def run_command(self, command):
        return subprocess.run(command, cwd=self.project, env=self.environment, text=True,
                              capture_output=True, check=True, timeout=20)

    def native(self, command):
        data = {'hook_event_name': 'PreToolUse', 'session_id': 'rtk-contract', 'cwd': str(self.project),
                'tool_name': 'Bash', 'tool_input': {'command': command, 'timeout': 17, 'description': 'Fixture'}}
        result = subprocess.run(['bash', str(self.hook)], input=json.dumps(data),
                                env=self.environment, cwd=self.project, text=True, capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        return data, json.loads(result.stdout) if result.stdout.strip() else None

    def bridge(self, command, *, guard=False):
        definitions = [{'type': 'command', 'command': 'bash ' + str(self.hook)}]
        if guard:
            definitions.append({'type': 'command', 'command': 'bun ' + str(self.source / 'hooks/PreToolGuard.hook.ts')})
        settings = self.root / 'settings.json'
        settings.write_text(json.dumps({'permissions': {'allow': ['Bash']}, 'hooks': {
            'PreToolUse': [{'matcher': 'Bash', 'hooks': definitions}]}}))
        bridge = HookBridge(settings, self.root, lifeos_home=self.home)
        bridge.environment.update(self.environment)
        try:
            return bridge.pre_tool_call('terminal', {'command': command, 'timeout': 17, 'description': 'Fixture'},
                                        session_id='rtk-contract')
        finally:
            bridge.close()

    def test_git_rewrite_preserves_fields_and_executes_actual_rtk(self):
        command = 'git status --short'
        data, output = self.native(command)
        updated = output['hookSpecificOutput']['updatedInput']
        self.assertEqual(updated, {**data['tool_input'], 'command': 'rtk git status --short'})
        verdict = self.bridge(command)
        self.assertEqual(verdict['action'], 'modify')
        self.assertEqual(verdict['args'], updated)
        (self.project / 'untracked.txt').write_text('Fixture content\n')
        raw = self.run_command(['git', 'status', '--short'])
        rewritten = self.run_command(['rtk', 'git', 'status', '--short'])
        self.assertIn('untracked.txt', raw.stdout)
        self.assertIn('untracked.txt', rewritten.stdout)
        self.assertIn('rtk 0.51.0', self.run_command(['rtk', '--version']).stdout)

    def test_environment_and_git_flags_keep_the_actual_repository(self):
        command = f'GIT_PAGER=cat git -C {self.project} status --short'
        _, output = self.native(command)
        updated = output['hookSpecificOutput']['updatedInput']['command']
        self.assertEqual(updated, f'GIT_PAGER=cat rtk git -C {self.project} status --short')
        (self.project / 'flag-proof.txt').write_text('Flag proof\n')
        result = self.run_command(['bash', '-c', updated])
        self.assertIn('flag-proof.txt', result.stdout)

    def test_gh_metadata_rewrite_executes_the_real_help_path_without_authentication(self):
        _, output = self.native('gh pr view --help')
        updated = output['hookSpecificOutput']['updatedInput']['command']
        self.assertEqual(updated, 'rtk gh pr view --help')
        self.assertEqual(self.bridge('gh pr view --help')['args']['command'], updated)
        result = self.run_command(['bash', '-c', updated])
        self.assertTrue(result.stdout.strip())

    def test_command_chains_preserve_the_shell_execution_order(self):
        (self.project / 'chain-proof.txt').write_text('Chain proof\n')
        command = 'git status --short && printf PAIR_CHAIN_FINISHED'
        _, output = self.native(command)
        updated = output['hookSpecificOutput']['updatedInput']['command']
        self.assertEqual(updated, 'rtk ' + command)
        self.assertEqual(self.bridge(command)['args']['command'], updated)
        result = self.run_command(['bash', '-c', updated])
        self.assertIn('chain-proof.txt', result.stdout)
        self.assertTrue(result.stdout.endswith('PAIR_CHAIN_FINISHED'))
        _, output = self.native('printf PAIR_CHAIN_START && git status --short')
        self.assertIsNone(output)

    def test_reads_existing_rtk_and_multiline_scripts_keep_the_command(self):
        for command in ('rtk git status', 'cat file.txt', 'rg needle file.txt', 'ls',
                        'printf first\nprintf second', 'cat <<EOF\nFixture\nEOF'):
            with self.subTest(command=command):
                _, output = self.native(command)
                self.assertIsNone(output)
                self.assertIsNone(self.bridge(command))

    def test_actual_native_public_guard_denies_after_a_rewrite(self):
        self.run_command(['git', 'config', 'user.name', 'Fixture'])
        self.run_command(['git', 'config', 'user.email', 'fixture@example.invalid'])
        self.run_command(['git', 'remote', 'add', 'origin', 'https://github.com/fixture/guard-test.git'])
        (self.project / 'tracked.txt').write_text('PAIR_DENY_TOKEN\n')
        self.run_command(['git', 'add', 'tracked.txt'])
        self.run_command(['git', 'commit', '--quiet', '-m', 'Guard fixture'])
        security = self.root / 'LIFEOS/USER/SECURITY'
        security.mkdir(parents=True)
        (security / 'PublicScrubPatterns.txt').write_text('PAIR_DENY_TOKEN\n')
        state = self.root / 'LIFEOS/MEMORY/STATE'
        state.mkdir(parents=True)
        (state / 'public-push-gate.json').write_text(json.dumps({
            'fixture/guard-test': {'v': 'public', 'ts': int(time.time() * 1000)}}))
        data, output = self.native('git push origin')
        updated = output['hookSpecificOutput']['updatedInput']
        self.assertEqual(updated['command'], 'rtk git push origin')
        run = subprocess.run(['bun', str(self.source / 'hooks/PreToolGuard.hook.ts')],
                             input=json.dumps({**data, 'tool_input': updated}), env=self.environment,
                             cwd=self.project, text=True, capture_output=True, timeout=20)
        self.assertEqual(run.returncode, 2, run.stderr)
        self.assertIn('PublicPushGate', run.stderr)
        verdict = self.bridge('git push origin', guard=True)
        self.assertEqual(verdict['action'], 'block')
        self.assertIn('PublicPushGate', verdict['message'])
        self.assertEqual(self.run_command(['git', 'status', '--porcelain']).stdout, '')
