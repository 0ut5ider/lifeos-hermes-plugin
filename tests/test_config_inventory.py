# ABOUTME: Characterizes configuration source roles and exact file-change signatures.
# ABOUTME: Uses real skill trees, dependency files, symlinks, and atomic replacement.
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from lifeos_hook_bridge.bridge import HookBridge


class ConfigInventoryTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.user = self.root / 'user/.claude'
        self.project = self.root / 'project'
        self.policy = self.root / 'policy'
        self.bridge = object.__new__(HookBridge)
        self.bridge.settings_path = self.user / 'settings.json'
        self.bridge.project_dirs = (self.project,)
        policy = patch('lifeos_hook_bridge.bridge.POLICY_DIRECTORY', self.policy)
        policy.start()
        self.addCleanup(policy.stop)

    def file(self, relative, content='data'):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    @staticmethod
    def signature(path):
        info = path.stat()
        return (info.st_mtime_ns, info.st_size, info.st_ctime_ns, info.st_dev, info.st_ino)

    def test_roles_and_signatures_keep_all_skill_inputs(self):
        settings = self.file('user/.claude/settings.json', '{}')
        user_skill = self.file('user/.claude/skills/research/SKILL.md')
        dependency = self.file('user/.claude/skills/research/node_modules/demo/index.js')
        hidden = self.file('user/.claude/skills/research/.state.json')
        project_skill = self.file('project/.claude/skills/work/SKILL.md')
        local = self.file('project/.claude/settings.local.json', '{}')
        policy = self.file('policy/managed-settings.d/a.json', '{}')
        self.file('policy/managed-settings.d/ignored.txt')
        (policy.parent / 'directory.json').mkdir()
        target = self.file('outside/file.txt')
        linked = project_skill.parent / 'linked.txt'
        linked.symlink_to(target)
        (project_skill.parent / 'linked-directory').symlink_to(target.parent, target_is_directory=True)
        (project_skill.parent / 'broken.txt').symlink_to(self.root / 'missing.txt')
        expected = {settings:'user_settings', self.policy/'managed-settings.json':'policy_settings',
            self.project/'.claude/settings.json':'project_settings', local:'local_settings',
            user_skill:'skills', dependency:'skills', hidden:'skills', project_skill:'skills',
            linked:'skills', policy:'policy_settings'}
        self.assertEqual(self.bridge._config_sources(), expected)
        present = [settings, local, user_skill, dependency, hidden, project_skill, linked, policy]
        self.assertEqual(self.bridge._config_files(), {path:self.signature(path) for path in present})

    def test_overlapping_roots_keep_project_setting_role(self):
        settings = self.file('user/.claude/settings.json', '{}')
        skill = self.file('user/.claude/skills/work/nested/script.py')
        self.bridge.project_dirs = (self.user.parent, self.user.parent)
        self.assertEqual(self.bridge._config_sources(), {
            settings:'project_settings', self.policy/'managed-settings.json':'policy_settings',
            self.user/'settings.local.json':'local_settings', skill:'skills'})
        self.assertEqual(self.bridge._config_files(), {path:self.signature(path) for path in (settings, skill)})

    def test_atomic_replacement_and_removal_change_signatures(self):
        skill = self.file('user/.claude/skills/work/SKILL.md', 'old!')
        before = self.bridge._config_files()[skill]
        replacement = self.file('replacement.txt', 'new!')
        os.utime(replacement, ns=(skill.stat().st_atime_ns, before[0]))
        os.replace(replacement, skill)
        after = self.bridge._config_files()[skill]
        self.assertEqual(after[:2], before[:2])
        self.assertNotEqual(after, before)
        self.assertEqual(after, self.signature(skill))
        skill.unlink()
        self.assertNotIn(skill, self.bridge._config_files())


if __name__ == '__main__':
    unittest.main()
