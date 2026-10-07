# ABOUTME: Verifies installed guard parser branches with disposable files and repositories.
# ABOUTME: Measures native and bridge decisions without sending messages or publishing repositories.
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
import time
import unittest

from lifeos_hook_bridge.bridge import HookBridge


SOURCE = os.environ.get('LIFEOS_GUARD_SOURCE')


@unittest.skipUnless(SOURCE and shutil.which('bun'), 'Installed guard source and Bun are required')
class NativePretoolGuardTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='guard-contract-')
        self.addCleanup(temporary.cleanup)
        self.home = Path(temporary.name)
        self.root = self.home / '.claude'
        self.project = self.home / 'project'
        self.project.mkdir()
        security = self.root / 'LIFEOS/USER/SECURITY'
        security.mkdir(parents=True)
        for name in ('DENY_LIST.txt', 'PublicScrubPatterns.txt'):
            (security / name).write_text('PAIR_DENY_TOKEN\n')
        self.hook = Path(SOURCE) / 'hooks/PreToolGuard.hook.ts'
        self.environment = {**os.environ, 'HOME': str(self.home), 'LIFEOS_DIR': str(self.root / 'LIFEOS'),
                            'LIFEOS_NOTIFICATION_CHANNEL': 'headless'}
        for key in ('LIFEOS_MEMORY_CONTEXT', 'LIFEOS_MEMORY_INTERNAL'):
            self.environment.pop(key, None)
        settings = self.root / 'settings.json'
        settings.write_text(json.dumps({'permissions': {'allow': ['Bash']}, 'hooks': {'PreToolUse': [
            {'matcher': 'Bash', 'hooks': [{'type': 'command', 'command': 'bun ' + shlex.quote(str(self.hook))}]}]}}))
        self.bridge = HookBridge(settings, self.root, lifeos_home=self.home)
        self.bridge.environment.update(self.environment)
        self.addCleanup(self.bridge.close)

    def native(self, command):
        payload = {'hook_event_name': 'PreToolUse', 'session_id': 'guard-contract', 'cwd': str(self.project),
                   'tool_name': 'Bash', 'tool_input': {'command': command}}
        return subprocess.run(['bun', str(self.hook)], input=json.dumps(payload), text=True,
                              capture_output=True, env=self.environment, cwd=self.project, timeout=15)

    def decision(self, command, blocked, marker):
        native = self.native(command)
        self.assertEqual(native.returncode, 2 if blocked else 0, native.stderr)
        verdict = self.bridge.pre_tool_call('terminal', {'command': command, 'workdir': str(self.project)},
                                            session_id='guard-contract')
        if blocked:
            self.assertIn(marker, native.stderr)
            self.assertEqual(verdict['action'], 'block')
            self.assertIn(marker, verdict['message'])
        else:
            self.assertEqual(native.stderr, '')
            self.assertTrue(verdict is None or verdict['action'] != 'block', verdict)

    def test_inline_write_forms_keep_system_user_and_outside_classification(self):
        for zone in ('system', 'user', 'outside'):
            target = self.home / {'system': '.claude/hooks/target.txt',
                                      'user': '.claude/LIFEOS/USER/CONFIG/target.txt',
                                      'outside': 'project/target.txt'}[zone]
            target.parent.mkdir(parents=True, exist_ok=True)
            for content in ('PAIR_DENY_TOKEN', 'PAIR_PUBLIC_CONTENT'):
                q = shlex.quote(str(target))
                commands = {
                    'redirect': f'printf {content} > {q}',
                    'append': f'printf {content} >> {q}',
                    'tee': f'printf {content} | tee {q}',
                    'copy': f'cp {content}.txt {q}',
                    'sed': f"sed -i 's/OLD/{content}/' {q}",
                    'pathlib': 'python3 -c ' + shlex.quote(f'from pathlib import Path; Path({str(target)!r}).write_text({content!r})'),
                    'node': 'bun -e ' + shlex.quote(f'require("fs").writeFileSync({json.dumps(str(target))},{json.dumps(content)})'),
                }
                for shape, command in commands.items():
                    with self.subTest(zone=zone, content=content, shape=shape):
                        target.write_text('OLD\n')
                        (self.project / (content + '.txt')).write_text(content)
                        denied = zone == 'system' and content == 'PAIR_DENY_TOKEN'
                        self.decision(command, denied, 'BashSystemWriteGuard')
                        if denied:
                            self.assertEqual(target.read_text(), 'OLD\n')
                        else:
                            execution = subprocess.run(['bash', '-c', command], env=self.environment,
                                                       cwd=self.project, text=True, capture_output=True, timeout=10)
                            self.assertEqual(execution.returncode, 0, execution.stderr)
                            self.assertIn(content, target.read_text())

    def test_indirect_shell_content_retains_the_documented_native_limit(self):
        target = self.root / 'hooks/indirect.txt'
        target.parent.mkdir(parents=True)
        source = self.project / 'fetched.txt'
        source.write_text('PAIR_DENY_TOKEN\n')
        command = f'cp {source} {target}'
        self.decision(command, False, '')
        self.assertFalse(target.exists())

    def git(self, *args):
        return subprocess.run(['git', *args], cwd=self.project, env=self.environment,
                              text=True, capture_output=True, check=True, timeout=10).stdout

    def test_public_clean_private_and_internal_destinations_keep_their_policy(self):
        self.git('init', '--quiet')
        self.git('config', 'user.name', 'Fixture')
        self.git('config', 'user.email', 'fixture@example.invalid')
        (self.project / 'tracked.txt').write_text('PAIR_PUBLIC_CONTENT\n')
        self.git('add', 'tracked.txt')
        self.git('commit', '--quiet', '-m', 'Guard fixture')
        self.decision('false && gh repo create pair-fixture --public', False, '')
        (self.project / 'tracked.txt').write_text('PAIR_DENY_TOKEN\n')
        self.git('add', 'tracked.txt')
        self.git('commit', '--quiet', '-m', 'Restricted fixture')
        self.git('remote', 'add', 'origin', 'https://github.com/fixture/guard-test.git')
        state = self.root / 'LIFEOS/MEMORY/STATE/public-push-gate.json'
        state.parent.mkdir(parents=True, exist_ok=True)
        for visibility in ('private', 'internal', 'public'):
            with self.subTest(visibility=visibility):
                state.write_text(json.dumps({'fixture/guard-test': {'v': visibility, 'ts': int(time.time() * 1000)}}))
                self.decision('git push origin', visibility == 'public', 'PublicPushGate')
        self.assertEqual(self.git('status', '--porcelain'), '')

    def test_malformed_dispatch_and_nonstring_commands_do_not_run_a_guard(self):
        for payload in ('{', '{}', '[]', '{"tool_name":"Bash","tool_input":{"command":[]}}'):
            with self.subTest(payload=payload):
                result = subprocess.run(['bun', str(self.hook)], input=payload, text=True,
                                        capture_output=True, env=self.environment, timeout=10)
                self.assertEqual((result.returncode, result.stdout, result.stderr), (0, '', ''))

    def test_unreadable_deny_list_does_not_suppress_a_later_guard(self):
        patterns = self.root / 'LIFEOS/USER/SECURITY/DENY_LIST.txt'
        patterns.unlink()
        patterns.mkdir()
        command = 'bun ./OpenRouter.ts --prompt LIFEOS/USER/CONTACTS.md'
        self.decision(command, True, 'EgressClassGuard')
