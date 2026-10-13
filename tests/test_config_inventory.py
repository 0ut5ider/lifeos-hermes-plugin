# ABOUTME: Characterizes configuration source roles and exact file-change signatures.
# ABOUTME: Uses real skill trees, dependency files, symlinks, and atomic replacement.
import json
import os
from pathlib import Path
import tempfile
import sys
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

    def test_nested_project_settings_keep_final_skills_role(self):
        settings = self.file('user/.claude/settings.json', '{}')
        nested = self.user / 'skills/research-project'
        nested_settings = self.file('user/.claude/skills/research-project/.claude/settings.json', '{}')
        nested_local = self.file('user/.claude/skills/research-project/.claude/settings.local.json', '{}')
        self.bridge.project_dirs = (self.user.parent, nested, self.project)
        sources = self.bridge._config_sources()
        self.assertEqual(sources[nested_settings], 'skills')
        self.assertEqual(sources[nested_local], 'skills')
        self.assertEqual(self.bridge._config_files(), {
            path: self.signature(path) for path in (settings, nested_settings, nested_local)})

    def test_nested_skill_settings_change_reaches_all_active_sessions(self):
        nested = self.user / 'skills/research-project'
        changed = self.file('user/.claude/skills/research-project/.claude/settings.json', '{}')
        self.file('project/.claude/settings.json', '{}')
        marker = self.root / 'events.jsonl'
        actor = self.file('record.py',
            'import json, sys\n'
            'from pathlib import Path\n'
            'with Path(sys.argv[1]).open("a") as stream:\n'
            '    stream.write(json.dumps(json.load(sys.stdin)) + "\\n")\n')
        self.file('user/.claude/settings.json', json.dumps({'hooks': {'ConfigChange': [{
            'matcher': 'skills', 'hooks': [{'type': 'command',
                'command': f'{sys.executable} {actor} {marker}'}]}]}}))
        previous = Path.cwd()
        self.addCleanup(os.chdir, previous)
        os.chdir(self.user.parent)
        bridge = HookBridge(self.user / 'settings.json', self.user, lifeos_home=self.user.parent)
        def stop_watcher():
            bridge.watcher_stop.set()
            if bridge.watcher is not None:
                bridge.watcher.join(timeout=5)
        self.addCleanup(stop_watcher)
        bridge._remember_project(str(nested), 'nested-session')
        bridge._remember_project(str(self.project), 'other-session')
        bridge.started_sessions.update({'nested-session', 'other-session'})
        bridge.config_files = bridge._config_files()
        changed.write_text('{"changed":true}')
        bridge.poll_config_changes(force=True)
        rows = [json.loads(line) for line in marker.read_text().splitlines()] if marker.exists() else []
        self.assertEqual({row['session_id'] for row in rows}, {'nested-session', 'other-session'})
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(row['source'] == 'skills' and row['file_path'] == str(changed) for row in rows))


if __name__ == '__main__':
    unittest.main()
