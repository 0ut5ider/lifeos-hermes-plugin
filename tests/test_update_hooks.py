# ABOUTME: Tests exact LifeOS hook registration replacement during a staged update.
# ABOUTME: Ensures foreign hooks survive and edited or ambiguous old hooks block the update.

import copy
import unittest

from lifeos_hook_bridge.update_hooks import HookUpdateConflict, replace_owned_hooks


def hook(command):
    return {"type": "command", "command": command}


class UpdateHooksTests(unittest.TestCase):
    def test_replaces_old_hooks_and_preserves_foreign_groups_and_settings(self):
        old = {"PreToolUse": [{"matcher": "Bash", "hooks": [hook("old.sh")]}]}
        new = {"PreToolUse": [{"matcher": "Bash", "hooks": [hook("new.sh")]}],
               "Stop": [{"hooks": [hook("stop.sh")]}]}
        current = {"model": "local", "hooks": {
            "PreToolUse": [
                {"matcher": "Read", "hooks": [hook("foreign-read.sh")]},
                {"matcher": "Bash", "hooks": [hook("old.sh"), hook("foreign-bash.sh")]},
                {"matcher": "Write", "hooks": [hook("foreign-write.sh")]},
            ],
            "SessionEnd": [{"hooks": [hook("foreign-end.sh")]}],
        }}
        original = copy.deepcopy(current)

        updated, report = replace_owned_hooks(current, old, new)

        self.assertEqual(current, original)
        self.assertEqual(updated["model"], "local")
        self.assertEqual(updated["hooks"]["PreToolUse"], [
            {"matcher": "Read", "hooks": [hook("foreign-read.sh")]},
            {"matcher": "Bash", "hooks": [hook("new.sh")]},
            {"matcher": "Bash", "hooks": [hook("foreign-bash.sh")]},
            {"matcher": "Write", "hooks": [hook("foreign-write.sh")]},
        ])
        self.assertEqual(updated["hooks"]["SessionEnd"], current["hooks"]["SessionEnd"])
        self.assertEqual(updated["hooks"]["Stop"], new["Stop"])
        self.assertEqual(report, {"old_hooks": 1, "new_hooks": 2, "foreign_hooks": 4})

    def test_identical_manifest_keeps_identical_settings(self):
        manifest = {"Stop": [{"hooks": [hook("a.sh"), hook("b.sh")]}]}
        current = {"hooks": copy.deepcopy(manifest), "env": {"PRIVATE": "kept"}}
        updated, report = replace_owned_hooks(current, manifest, manifest)
        self.assertEqual(updated, current)
        self.assertEqual(report["foreign_hooks"], 0)

    def test_installer_coalesced_empty_matcher_groups_are_owned(self):
        manifest = {"Stop": [{"hooks": [hook("a.sh")]},
                             {"hooks": [hook("b.sh")]}]}
        current = {"hooks": {"Stop": [{"matcher": "", "hooks": [hook("a.sh"), hook("b.sh")]}]}}
        updated, report = replace_owned_hooks(current, manifest, manifest)
        self.assertEqual(updated, current)
        self.assertEqual(report, {"old_hooks": 2, "new_hooks": 2, "foreign_hooks": 0})

    def test_edited_old_hook_blocks_update(self):
        old = {"Stop": [{"hooks": [hook("old.sh")]}]}
        current = {"hooks": {"Stop": [{"hooks": [{**hook("old.sh"), "timeout": 3}]}]}}
        with self.assertRaisesRegex(HookUpdateConflict, "missing or edited"):
            replace_owned_hooks(current, old, old)

    def test_duplicate_old_hook_blocks_update(self):
        old = {"Stop": [{"hooks": [hook("old.sh")]}]}
        current = {"hooks": {"Stop": [{"hooks": [hook("old.sh"), hook("old.sh")]}]}}
        with self.assertRaisesRegex(HookUpdateConflict, "ambiguous"):
            replace_owned_hooks(current, old, old)

    def test_new_hook_collision_with_foreign_hook_blocks_update(self):
        old = {"Stop": [{"hooks": [hook("old.sh")]}]}
        new = {"Stop": [{"hooks": [hook("new.sh")]}]}
        current = {"hooks": {"Stop": [{"hooks": [hook("old.sh")]},
                                      {"hooks": [hook("new.sh")]}]}}
        with self.assertRaisesRegex(HookUpdateConflict, "collides"):
            replace_owned_hooks(current, old, new)

    def test_foreign_hook_type_survives(self):
        old = {"Stop": [{"hooks": [hook("old.sh")]}]}
        new = {"Stop": [{"hooks": [hook("new.sh")]}]}
        foreign = {"type": "prompt", "prompt": "Review this turn"}
        current = {"hooks": {"Stop": [{"hooks": [hook("old.sh"), foreign]}]}}
        updated, report = replace_owned_hooks(current, old, new)
        self.assertEqual(updated["hooks"]["Stop"][-1]["hooks"], [foreign])
        self.assertEqual(report["foreign_hooks"], 1)

    def test_invalid_manifest_blocks_update(self):
        with self.assertRaisesRegex(HookUpdateConflict, "invalid"):
            replace_owned_hooks({"hooks": {}}, {"Stop": "wrong"}, {})


if __name__ == "__main__":
    unittest.main()
