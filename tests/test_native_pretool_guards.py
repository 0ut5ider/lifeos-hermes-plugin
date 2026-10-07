# ABOUTME: Verifies installed guard parser branches with disposable files and repositories.
# ABOUTME: Measures native and bridge decisions without sending messages or publishing repositories.
import json
import hashlib
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
            {'matcher': 'Bash|Write|Edit|MultiEdit', 'hooks': [{'type': 'command', 'command': 'bun ' + shlex.quote(str(self.hook))}]}]}}))
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

    def test_file_tools_keep_system_user_and_outside_decisions(self):
        for tool in ('Write', 'Edit', 'MultiEdit'):
            for zone in ('system', 'user', 'outside'):
                target = self.home / {'system': '.claude/hooks/guard-target.txt',
                                     'user': '.claude/LIFEOS/USER/CONFIG/guard-target.txt',
                                     'outside': 'project/guard-target.txt'}[zone]
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text('PAIR_OLD_LINE\n')
                for content in ('PAIR_DENY_TOKEN', 'PAIR_PUBLIC_CONTENT'):
                    with self.subTest(tool=tool, zone=zone, content=content):
                        operation = {'file_path': str(target), **({'content': content} if tool == 'Write' else
                                     {'new_string': content} if tool == 'Edit' else
                                     {'edits': [{'old_string': 'PAIR_OLD_LINE', 'new_string': content}]})}
                        payload = {'session_id': 'file-guard', 'cwd': str(self.project),
                                   'tool_name': tool, 'tool_input': operation}
                        result = subprocess.run(['bun', str(self.hook)], input=json.dumps(payload), text=True,
                                                capture_output=True, env=self.environment, timeout=15)
                        denied = zone == 'system' and content == 'PAIR_DENY_TOKEN'
                        self.assertEqual(result.returncode, 2 if denied else 0, result.stderr)
                        if tool == 'Write':
                            name, args = 'write_file', {'path': str(target), 'content': content}
                        elif tool == 'Edit':
                            name, args = 'patch', {'path': str(target), 'old_string': 'PAIR_OLD_LINE', 'new_string': content}
                        else:
                            name, args = 'patch', {'mode': 'patch', 'patch': '\n'.join([
                                '*** Begin Patch', '*** Update File: ' + str(target),
                                '-PAIR_OLD_LINE', '+' + content, '*** End Patch'])}
                        verdict = self.bridge.pre_tool_call(name, args, session_id='file-guard')
                        self.assertEqual(bool(verdict and verdict['action'] == 'block'), denied, verdict)
                        self.assertEqual(target.read_text(), 'PAIR_OLD_LINE\n')

    def test_plutil_output_form_avoids_the_in_place_extraction_guard(self):
        self.decision('plutil -extract Label raw fixture.plist', True, 'blocked `plutil -extract`')
        for command in ('plutil -extract Label raw -o - fixture.plist',
                        'plutil -extract Label raw -o=stdout fixture.plist', 'plutil -lint fixture.plist'):
            with self.subTest(command=command):
                self.decision(command, False, '')

    def test_egress_ceiling_uses_actual_classification_without_a_network_call(self):
        for command, denied in (
            ('bun OpenRouter.ts --prompt PAIR_PUBLIC_CONTENT', False),
            ('bun OpenRouter.ts --prompt LIFEOS/USER/CONTACTS.md', True),
            ('bun OpenRouter.ts --pin fireworks --prompt LIFEOS/USER/TELOS/mission.md', True),
            ('cat OpenRouter.ts', False),
        ):
            with self.subTest(command=command):
                self.decision(command, denied, 'EgressClassGuard')

    def test_native_read_view_blocks_only_a_stale_whole_file_write(self):
        target = self.project / 'ISA.md'
        target.write_text('PAIR_PRIOR_CLAIM\n')
        payload = {'session_id': 'isa-view', 'cwd': str(self.project), 'tool_name': 'Read',
                   'tool_input': {'file_path': str(target)}}
        result = subprocess.run(['bun', str(Path(SOURCE) / 'hooks/ISAStaleWriteGuard.hook.ts')],
                                input=json.dumps(payload), text=True, capture_output=True,
                                env=self.environment, timeout=15)
        self.assertEqual((result.returncode, result.stderr), (0, ''))
        def check(tool, denied):
            operation = {'file_path': str(target), 'content': 'PAIR_REPLACEMENT',
                         'old_string': 'PAIR_UPDATED_CLAIM', 'new_string': 'PAIR_EDITED_CLAIM'}
            payload.update(tool_name=tool, tool_input=operation)
            native = subprocess.run(['bun', str(self.hook)], input=json.dumps(payload), text=True,
                                    capture_output=True, env=self.environment, timeout=15)
            self.assertEqual(native.returncode, 2 if denied else 0, native.stderr)
            if denied:
                self.assertIn('stale whole-file Write', native.stderr)
            name = 'write_file' if tool == 'Write' else 'patch'
            args = {'path': str(target), 'content': 'PAIR_REPLACEMENT'} if tool == 'Write' else {
                'path': str(target), 'old_string': 'PAIR_UPDATED_CLAIM', 'new_string': 'PAIR_EDITED_CLAIM'}
            verdict = self.bridge.pre_tool_call(name, args, session_id='isa-view')
            self.assertEqual(bool(verdict and verdict['action'] == 'block'), denied, verdict)
        check('Write', False)
        target.write_text('PAIR_UPDATED_CLAIM\n')
        check('Write', True)
        self.assertEqual(target.read_text(), 'PAIR_UPDATED_CLAIM\n')
        check('Edit', False)
        state = self.root / 'LIFEOS/MEMORY/STATE/isa-session-view/isa-view.json'
        state.write_text('{')
        check('Write', False)
        state.unlink()
        check('Write', False)
        target.unlink()
        check('Write', False)

    def test_system_guard_read_failure_cannot_suppress_the_later_stale_write_guard(self):
        target = self.root / 'hooks/ISA.md'
        target.parent.mkdir(parents=True)
        target.write_text('PAIR_UPDATED_CLAIM\n')
        state = self.root / 'LIFEOS/MEMORY/STATE/isa-session-view/isolation.json'
        state.parent.mkdir(parents=True)
        state.write_text(json.dumps({'views': {str(target): hashlib.sha256(b'PAIR_PRIOR_CLAIM\n').hexdigest()}}))
        patterns = self.root / 'LIFEOS/USER/SECURITY/DENY_LIST.txt'
        patterns.unlink()
        patterns.mkdir()
        payload = {'session_id': 'isolation', 'cwd': str(self.project), 'tool_name': 'Write',
                   'tool_input': {'file_path': str(target), 'content': 'PAIR_DENY_TOKEN'}}
        native = subprocess.run(['bun', str(self.hook)], input=json.dumps(payload), text=True,
                                capture_output=True, env=self.environment, timeout=15)
        self.assertEqual(native.returncode, 2, native.stderr)
        self.assertIn('stale whole-file Write', native.stderr)
        verdict = self.bridge.pre_tool_call('write_file', {'path': str(target), 'content': 'PAIR_DENY_TOKEN'},
                                            session_id='isolation')
        self.assertEqual(verdict['action'], 'block')
        self.assertIn('stale whole-file Write', verdict['message'])
        rows = [json.loads(line) for line in (self.root / 'LIFEOS/MEMORY/OBSERVABILITY/system-file-guard.jsonl').read_text().splitlines()]
        self.assertEqual([row['action'] for row in rows], ['fail-safe-open', 'fail-safe-open'])
        self.assertEqual(target.read_text(), 'PAIR_UPDATED_CLAIM\n')

    def test_egress_classifier_fault_blocks_only_a_confirmed_tier_two_call(self):
        # Fault injection exercises the native error policy; it is not a model or transport control.
        preload = self.home / 'classification-fault.ts'
        dependency = Path(SOURCE) / 'hooks/lib/egress-class-core.ts'
        preload.write_text('// ABOUTME: Injects a classifier exception into one disposable native process.\n'
                           '// ABOUTME: Leaves the installed classifier and guard files unchanged.\n'
                           'import { SECRET_VALUE_SHAPES } from ' + json.dumps(str(dependency)) + ';\n'
                           'SECRET_VALUE_SHAPES[0].test = () => { throw new Error("PAIR_CLASSIFICATION_FAILURE"); };\n')
        definitions = [{'type': 'command', 'command': ' '.join(shlex.quote(str(arg)) for arg in
                        ('bun', '--preload', preload, self.hook))}]
        self.bridge.settings_path.write_text(json.dumps({'permissions': {'allow': ['Bash']},
            'hooks': {'PreToolUse': [{'matcher': 'Bash', 'hooks': definitions}]}}))
        self.bridge.poll_config_changes(force=True)
        for command, denied in (('bun OpenRouter.ts --prompt PAIR_PUBLIC_CONTENT', True), ('printf safe', False)):
            with self.subTest(command=command):
                payload = {'session_id': 'classifier-fault', 'cwd': str(self.project), 'tool_name': 'Bash',
                           'tool_input': {'command': command}}
                native = subprocess.run(['bun', '--preload', str(preload), str(self.hook)],
                                        input=json.dumps(payload), text=True, capture_output=True,
                                        env=self.environment, timeout=15)
                self.assertEqual(native.returncode, 2 if denied else 0, native.stderr)
                if denied:
                    self.assertIn('classification error on a Tier-2 call', native.stderr)
                verdict = self.bridge.pre_tool_call('terminal', {'command': command, 'workdir': str(self.project)},
                                                    session_id='classifier-fault')
                self.assertEqual(bool(verdict and verdict['action'] == 'block'), denied, verdict)

    def test_voice_remote_and_headless_decisions_preserve_health_and_silent_calls(self):
        for channel in ('headless', 'discord'):
            self.environment['LIFEOS_NOTIFICATION_CHANNEL'] = channel
            self.bridge.environment['LIFEOS_NOTIFICATION_CHANNEL'] = channel
            for command, denied in (
                ('curl http://127.0.0.1:31337/notify', True),
                ('curl http://127.0.0.1:31337/voice/health', False),
                ('curl http://127.0.0.1:31337/notify -d \'{"voice_enabled":false}\'', False),
            ):
                with self.subTest(channel=channel, command=command):
                    self.decision(command, denied, 'VoiceEgressGuard')

    def test_public_policy_skips_nonpublication_and_non_github_destinations(self):
        self.git('init', '--quiet')
        self.git('remote', 'add', 'origin', 'https://fixture.example.invalid/guard-test.git')
        for command in ('git push origin', 'git status', 'gh repo create pair-fixture --private'):
            with self.subTest(command=command):
                self.decision(command, False, '')
