# ABOUTME: Characterizes how the bridge recognizes native LifeOS hook scripts in hook commands.
# ABOUTME: Covers launcher stripping, home spellings, malformed quoting, and exact path matching.
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from lifeos_hook_bridge.bridge import (_is_native_checkpoint, _is_native_task_governance,
                                       _is_native_version_drift, _native_post_hook)


class HookCommandRecognitionTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.home = Path(directory.name).resolve()
        self.root = self.home / '.claude'
        (self.root / 'hooks').mkdir(parents=True)
        environment = mock.patch.dict(os.environ, {'HOME': str(self.home)})
        environment.start()
        self.addCleanup(environment.stop)

    def test_version_drift_accepts_one_script_with_optional_bun(self):
        script = str(self.root / 'hooks/VersionDrift.hook.ts')
        for command in ('$HOME/.claude/hooks/VersionDrift.hook.ts', '${HOME}/.claude/hooks/VersionDrift.hook.ts',
                        'bun $HOME/.claude/hooks/VersionDrift.hook.ts', '/usr/bin/bun ' + script, script,
                        '~/.claude/hooks/VersionDrift.hook.ts', 'bun ~/.claude/hooks/VersionDrift.hook.ts'):
            self.assertTrue(_is_native_version_drift(command, self.root), command)
        for command in ('', 'bun', 'node ' + script, 'bun run ' + script, script + ' --flag',
                        'bun "' + script, '/other/.claude/hooks/VersionDrift.hook.ts',
                        str(self.root / 'hooks/TimeContext.hook.ts')):
            self.assertFalse(_is_native_version_drift(command, self.root), command)

    def test_native_post_hook_names_only_known_scripts_under_root(self):
        self.assertEqual(_native_post_hook('bun $HOME/.claude/hooks/TimeContext.hook.ts', self.root), 'TimeContext')
        self.assertEqual(_native_post_hook('bun ${HOME}/.claude/hooks/ISASync.hook.ts', self.root), 'ISASync')
        self.assertEqual(_native_post_hook('~/.claude/hooks/AgentInvocation.hook.ts', self.root), 'AgentInvocation')
        self.assertEqual(_native_post_hook(str(self.root / 'hooks/ReminderRouter.hook.ts'), self.root), 'ReminderRouter')
        other = tempfile.TemporaryDirectory()
        self.addCleanup(other.cleanup)
        # The $HOME spelling rewrites against the supplied root, not the process home directory.
        self.assertEqual(_native_post_hook('$HOME/.claude/hooks/SpendAuditor.hook.ts', Path(other.name)), 'SpendAuditor')
        for command in ('', 'bun', 'bun "unterminated', 'node $HOME/.claude/hooks/TimeContext.hook.ts',
                        'bun $HOME/.claude/hooks/TimeContext.hook.ts extra', '/other/.claude/hooks/AgentInvocation.hook.ts',
                        '$HOME/.claude/hooks/VersionDrift.hook.ts', '$HOME/.claude/hooks/Unknown.hook.ts'):
            self.assertEqual(_native_post_hook(command, self.root), '', command)

    def test_checkpoint_matches_final_path_parts_without_resolving(self):
        for command in ('bun $HOME/.claude/hooks/CheckpointPerISC.hook.ts', '${HOME}/.claude/hooks/CheckpointPerISC.hook.ts',
                        '/elsewhere/.claude/hooks/CheckpointPerISC.hook.ts', 'bun ~/.claude/hooks/CheckpointPerISC.hook.ts'):
            self.assertTrue(_is_native_checkpoint(command), command)
        for command in ('', 'bun', 'bun "unterminated', 'node ~/.claude/hooks/CheckpointPerISC.hook.ts',
                        '~/.claude/hooks/CheckpointPerISC.hook.ts --flag', '~/hooks/CheckpointPerISC.hook.ts',
                        '~/.claude/other/CheckpointPerISC.hook.ts'):
            self.assertFalse(_is_native_checkpoint(command), command)

    def test_task_governance_requires_a_string_and_the_resolved_root_script(self):
        for command in ('bun $HOME/.claude/hooks/TaskGovernance.hook.ts', '${HOME}/.claude/hooks/TaskGovernance.hook.ts',
                        '~/.claude/hooks/TaskGovernance.hook.ts', str(self.root / 'hooks/TaskGovernance.hook.ts')):
            self.assertTrue(_is_native_task_governance(command, self.root), command)
        for command in (None, 1, ['bun'], '', 'bun', 'bun "unterminated', 'node ~/.claude/hooks/TaskGovernance.hook.ts',
                        '~/.claude/hooks/TaskGovernance.hook.ts --flag', '/elsewhere/.claude/hooks/TaskGovernance.hook.ts'):
            self.assertFalse(_is_native_task_governance(command, self.root), command)


if __name__ == '__main__':
    unittest.main()
