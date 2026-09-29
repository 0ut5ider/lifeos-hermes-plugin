# ABOUTME: Checks LifeOS Bash permission decisions through a patched Hermes command guard.
# ABOUTME: Runs the installed native Safety hook in a disposable LifeOS state directory.

import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
HERMES_SOURCE = os.environ.get("HERMES_POLICY_SOURCE")
LIFEOS_SAFETY_HOOK = os.environ.get("LIFEOS_PERMISSION_HOOK")


@unittest.skipUnless(HERMES_SOURCE and LIFEOS_SAFETY_HOOK, "patched Hermes and native Safety hook are required")
class HostCommandPolicyTests(unittest.TestCase):
    def test_native_safety_neutral_command_requests_review(self):
        sys.path.insert(0, HERMES_SOURCE)
        try:
            from hermes_cli import plugins as plugins_mod
            from tools.approval import check_all_command_guards

            with tempfile.TemporaryDirectory(prefix="lifeos-command-policy-") as directory:
                home = Path(directory) / "hermes"
                plugin = home / "plugins/lifeos-hook-bridge"
                plugin.parent.mkdir(parents=True)
                shutil.copytree(ROOT / "lifeos_hook_bridge", plugin)
                (home / "config.yaml").write_text(
                    "plugins:\n  enabled:\n    - lifeos-hook-bridge\napprovals:\n  mode: manual\n"
                )
                settings = Path(directory) / "settings.json"
                settings.write_text(json.dumps({"hooks": {"PermissionRequest": [{
                    "matcher": "Bash", "hooks": [{"type": "command", "command": LIFEOS_SAFETY_HOOK}],
                }]}}))
                environment = {
                    "HERMES_HOME": str(home),
                    "LIFEOS_HOOK_SETTINGS": str(settings),
                    "LIFEOS_DIR": str(Path(directory) / "LIFEOS"),
                    "HERMES_INTERACTIVE": "1",
                    "PATH": str(Path.home() / ".bun/bin") + os.pathsep + os.environ.get("PATH", ""),
                }
                with patch.dict(os.environ, environment):
                    plugins_mod._reset_plugin_managers_for_tests()
                    try:
                        prompts = []
                        safe = check_all_command_guards(
                            "echo 67890", "local",
                            approval_callback=lambda *args, **kwargs: prompts.append("safe") or "deny",
                        )
                        self.assertTrue(safe["approved"])
                        self.assertEqual(prompts, [])

                        reviewed = check_all_command_guards(
                            "curl -I http://192.168.8.1:9", "local",
                            approval_callback=lambda *args, **kwargs: prompts.append("review") or "deny",
                        )
                        self.assertFalse(reviewed["approved"])
                        self.assertEqual(prompts, ["review"])

                        docker = check_all_command_guards(
                            "curl -I http://192.168.8.1:9", "docker", has_host_access=False,
                            approval_callback=lambda *args, **kwargs: prompts.append("docker") or "deny",
                        )
                        self.assertFalse(docker["approved"])
                        self.assertEqual(prompts, ["review", "docker"])

                        hardline = check_all_command_guards(
                            "rm -rf /", "local",
                            approval_callback=lambda *args, **kwargs: self.fail("Hardline asked for approval"),
                        )
                        self.assertFalse(hardline["approved"])

                        log = Path(directory) / "LIFEOS/MEMORY/OBSERVABILITY/permission-decisions.jsonl"
                        decisions = [json.loads(line) for line in log.read_text().splitlines()]
                        self.assertEqual([item["decision"] for item in decisions], ["neutral", "neutral"])

                        exact_command = "curl -I --max-time 1 http://192.168.8.1:9"
                        settings.write_text(json.dumps({
                            "hooks": {"PermissionRequest": [{
                                "matcher": "Bash", "hooks": [{"type": "command", "command": LIFEOS_SAFETY_HOOK}],
                            }]},
                            "permissions": {"allow": [f"Bash({exact_command})"]},
                        }))
                        allow_prompts = []
                        allowed = check_all_command_guards(
                            exact_command, "local",
                            approval_callback=lambda *args, **kwargs: allow_prompts.append(args) or "deny",
                        )
                        self.assertFalse(allowed["approved"])
                        self.assertEqual(allowed["pattern_key"], "tirith:raw_ip_url")
                        self.assertEqual(len(allow_prompts), 1, "Hermes security scan remains authoritative")
                        self.assertEqual([json.loads(line)["decision"] for line in log.read_text().splitlines()],
                                         ["neutral", "neutral"])

                        settings.write_text(json.dumps({
                            "hooks": {"PermissionRequest": [{
                                "matcher": "Bash", "hooks": [{"type": "command", "command": LIFEOS_SAFETY_HOOK}],
                            }]},
                            "permissions": {"deny": [f"Bash({exact_command})"]},
                        }))
                        denied = check_all_command_guards(
                            exact_command, "local",
                            approval_callback=lambda *args, **kwargs: self.fail("Denied rule asked for approval"),
                        )
                        self.assertFalse(denied["approved"])
                        self.assertEqual([json.loads(line)["decision"] for line in log.read_text().splitlines()],
                                         ["neutral", "neutral"])
                        settings.write_text(json.dumps({
                            "hooks": {"PermissionRequest": [{
                                "matcher": "Bash", "hooks": [{"type": "command", "command": LIFEOS_SAFETY_HOOK}],
                            }]},
                            "permissions": {"deny": ["Bash(printf world)"]},
                        }))
                        compound = check_all_command_guards(
                            "printf hello; printf world", "local",
                            approval_callback=lambda *args, **kwargs: self.fail("Compound deny asked for approval"),
                        )
                        self.assertFalse(compound["approved"])
                        self.assertEqual([json.loads(line)["decision"] for line in log.read_text().splitlines()],
                                         ["neutral", "neutral"])
                        permanent_command = "curl -I http://192.168.8.1:9"
                        (home / "config.yaml").write_text(
                            "plugins:\n  enabled:\n    - lifeos-hook-bridge\n"
                            "approvals:\n  mode: manual\n"
                            f"command_allowlist:\n  - {json.dumps(permanent_command)}\n"
                        )
                        from tools.approval import load_permanent_allowlist
                        load_permanent_allowlist()
                        settings.write_text(json.dumps({
                            "hooks": {"PermissionRequest": [{
                                "matcher": "Bash", "hooks": [{"type": "command", "command": LIFEOS_SAFETY_HOOK}],
                            }]},
                            "permissions": {"deny": [f"Bash({permanent_command})"]},
                        }))
                        permanent_denial = check_all_command_guards(
                            permanent_command, "local",
                            approval_callback=lambda *args, **kwargs: self.fail("Denied rule asked for approval"),
                        )
                        self.assertFalse(permanent_denial["approved"])
                        self.assertEqual(permanent_denial["outcome"], "plugin_denied")
                        (home / "config.yaml").write_text(
                            "plugins:\n  enabled:\n    - lifeos-hook-bridge\napprovals:\n  mode: manual\n"
                        )
                        load_permanent_allowlist()
                        from agent import terminal_approval_batch
                        from tools.approval_context import _approval_tool_call_id
                        prepared = SimpleNamespace(
                            preparing=False,
                            check_cancelled=lambda: None,
                            batch=SimpleNamespace(failure_seen=False, task_id=""),
                            parsed=SimpleNamespace(ref=lambda _: SimpleNamespace(call_id="policy-call")),
                            guard_key=(permanent_command, "local", False, "", ""),
                            decision={"approved": True, "message": None},
                        )
                        slot_token = terminal_approval_batch._slot.set(prepared)
                        call_token = _approval_tool_call_id.set("policy-call")
                        try:
                            prepared_denial = check_all_command_guards(
                                permanent_command, "local",
                                approval_callback=lambda *args, **kwargs: self.fail("Denied rule asked for approval"),
                            )
                            self.assertFalse(prepared_denial["approved"])
                            self.assertEqual(prepared_denial["outcome"], "plugin_denied")
                        finally:
                            _approval_tool_call_id.reset(call_token)
                            terminal_approval_batch._slot.reset(slot_token)
                        with patch("tools.approval_context._get_approval_mode", return_value="off"):
                            bypass_denial = check_all_command_guards(permanent_command, "local")
                        self.assertFalse(bypass_denial["approved"])
                        self.assertEqual(bypass_denial["outcome"], "plugin_denied")
                        with patch("tools.approval._yolo_active", return_value=True):
                            yolo_denial = check_all_command_guards(permanent_command, "local")
                        self.assertFalse(yolo_denial["approved"])
                        self.assertEqual(yolo_denial["outcome"], "plugin_denied")
                        prior_hook_log = log.read_text()
                        settings.write_text(json.dumps({"hooks": {"PermissionRequest": [{
                            "matcher": "Bash", "hooks": [{"type": "command", "command": LIFEOS_SAFETY_HOOK}],
                        }]}}))
                        with patch("tools.approval_context._get_approval_mode", return_value="off"):
                            bypass_allowed = check_all_command_guards(permanent_command, "local")
                        self.assertTrue(bypass_allowed["approved"])
                        with patch("tools.approval._yolo_active", return_value=True):
                            yolo_allowed = check_all_command_guards(permanent_command, "local")
                        self.assertTrue(yolo_allowed["approved"])
                        self.assertEqual(log.read_text(), prior_hook_log)
                        guarded_path = Path(directory) / "guarded.txt"
                        redirect_command = f"printf PARITY > {guarded_path}"
                        settings.write_text(json.dumps({
                            "hooks": {"PermissionRequest": [{
                                "matcher": "Bash", "hooks": [{"type": "command", "command": LIFEOS_SAFETY_HOOK}],
                            }]},
                            "permissions": {
                                "allow": [f"Bash({redirect_command})"],
                                "deny": [f"Edit(//{str(guarded_path).lstrip('/')})"],
                            },
                        }))
                        redirected = check_all_command_guards(
                            redirect_command, "local",
                            approval_callback=lambda *args, **kwargs: self.fail("File deny asked for approval"),
                        )
                        self.assertFalse(redirected["approved"])
                        self.assertFalse(guarded_path.exists())
                        self.assertEqual([json.loads(line)["decision"] for line in log.read_text().splitlines()],
                                         ["neutral", "neutral"])
                    finally:
                        plugins_mod._reset_plugin_managers_for_tests()
        finally:
            sys.path.remove(HERMES_SOURCE)


if __name__ == "__main__":
    unittest.main()
