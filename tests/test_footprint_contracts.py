# ABOUTME: Verifies plugin-owned commands, model observations, and installed hook capabilities.
# ABOUTME: Keeps patch reductions tied to actual routes and verified native files.

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from lifeos_hook_bridge import register
from lifeos_hook_bridge.model_tiers import configured_model_map
from lifeos_hook_bridge.bridge import HookBridge


class FootprintContractsTests(unittest.TestCase):
    def test_commands_register_before_lifeos_is_installed(self):
        class Context:
            def __init__(self):
                self.commands = {}

            def register_cli_command(self, name, **entry):
                self.commands[name] = entry

        ctx = Context()
        with tempfile.TemporaryDirectory() as directory, patch.dict(
            os.environ, {"LIFEOS_HOOK_SETTINGS": str(Path(directory) / "missing.json")}
        ):
            register(ctx)
        self.assertEqual(set(ctx.commands), {"lifeos-infer", "lifeos-probe", "lifeos-backup"})

    def test_observation_binds_provider_model_and_effort(self):
        from lifeos_hook_bridge.model_tiers import carrier_observation

        mapping = configured_model_map({
            "sonnet_provider": "local-a", "sonnet_model": "shared", "sonnet_effort": "medium",
            "haiku_provider": "local-b", "haiku_model": "shared", "haiku_effort": "medium",
        }.get, "local-a", "parent")
        for provider, expected in (("local-a", "sonnet"), ("local-b", "haiku"), ("unknown", None)):
            with self.subTest(provider=provider):
                result = carrier_observation("shared", "medium", provider, mapping)
                self.assertEqual(result["tier"], expected)
                self.assertEqual(result["model"], "shared")
                self.assertEqual(result["provider"], provider)
        self.assertIsNone(carrier_observation("shared", "high", "local-a", mapping)["tier"])

    def test_identical_top_routes_choose_fable_and_unknown_effort_stays_unknown(self):
        from lifeos_hook_bridge.model_tiers import carrier_observation

        mapping = configured_model_map(dict().get, "local", "one-model")
        self.assertEqual(carrier_observation("one-model", "xhigh", "local", mapping)["tier"], "fable")
        self.assertIsNone(carrier_observation("one-model", "", "local", mapping)["tier"])
        self.assertEqual(carrier_observation("claude-sonnet-5", "", "anthropic", mapping)["tier"], "sonnet")

    def test_capability_requires_record_and_exact_native_bytes(self):
        from lifeos_hook_bridge.native_capabilities import capability_record, supports_task_count

        source = os.environ.get("LIFEOS_TASK_HOOK_PATH")
        if not source:
            self.skipTest("Prepared native TaskGovernance is required")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            hooks = root / "hooks"
            hooks.mkdir()
            hook = hooks / "TaskGovernance.hook.ts"
            hook.write_bytes(Path(source).read_bytes())
            self.assertFalse(supports_task_count(root))
            record = hooks / "lifeos-bridge-capabilities.json"
            record.write_text(json.dumps(capability_record()))
            self.assertTrue(supports_task_count(root))
            hook.write_text(hook.read_text() + "\n// changed installation\n")
            self.assertFalse(supports_task_count(root))
            hook.write_bytes(Path(source).read_bytes())
            record.write_text('{"schema":1,"source_commit":"unknown"}')
            self.assertFalse(supports_task_count(root))

    def test_changed_native_installation_blocks_task_creation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            hooks = root / "hooks"
            hooks.mkdir()
            hook = hooks / "TaskGovernance.hook.ts"
            hook.write_text("changed native hook")
            settings = root / "settings.json"
            settings.write_text(json.dumps({"hooks": {"TaskCreated": [{"hooks": [
                {"type": "command", "command": f"bun {hook}"},
            ]}]}}))
            bridge = HookBridge(settings, root)
            self.addCleanup(bridge.close)
            for result in (
                bridge._task_created_verdict({"todos": [{"id": "one", "content": "Meaningful task description"}]}, "session", "one"),
                bridge._kanban_task_verdict({"title": "Meaningful task description"}, "session", "two"),
            ):
                self.assertEqual(result["action"], "block")
                self.assertIn("verified installation", result["message"])

    def test_observation_skips_sidechains_and_reclassifies_after_configuration_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            settings = root / "settings.json"
            settings.write_text('{"hooks":{}}')
            values = {"pin": "fable", "sonnet": {"model": "shared", "provider": "local-a", "effort": "medium"}}
            bridge = HookBridge(settings, root, model_tiers_provider=lambda: values)
            self.addCleanup(bridge.close)
            bridge.stop("Main response", "session", model="shared", provider="local-a", reasoning_effort="medium")
            with bridge.transcript_path("session").open("a") as stream:
                stream.write(json.dumps({"type": "assistant", "isSidechain": True,
                                         "message": {"model": "other", "provider": "local-b", "reasoning_effort": "low"}}) + "\n")
            payload = {"session_id": "session", "hook_event_name": "UserPromptSubmit"}
            observed = json.loads(bridge._event_environment(payload)["LIFEOS_CARRIER_OBSERVATION"])
            self.assertEqual((observed["model"], observed["provider"], observed["tier"]), ("shared", "local-a", "sonnet"))
            values["sonnet"]["provider"] = "local-b"
            self.assertIsNone(json.loads(bridge._event_environment(payload)["LIFEOS_CARRIER_OBSERVATION"])["tier"])

    def test_project_native_task_registration_requires_verified_capability(self):
        source = os.environ.get("LIFEOS_TASK_HOOK_PATH")
        if not source:
            self.skipTest("Prepared native TaskGovernance is required")
        from lifeos_hook_bridge.native_capabilities import RECORD_NAME, capability_record
        for settings_name in ("settings.json", "settings.local.json"):
            with self.subTest(settings_name=settings_name), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                hooks = root / "hooks"
                hooks.mkdir()
                native = hooks / "TaskGovernance.hook.ts"
                native.write_bytes(Path(source).read_bytes())
                settings = root / "settings.json"
                settings.write_text('{"hooks":{}}')
                project = root / "project"
                (project / ".claude").mkdir(parents=True)
                (project / ".claude" / settings_name).write_text(json.dumps({
                    "hooks": {"TaskCreated": [{"hooks": [{"type": "command", "command": f"bun {native}"}]}]},
                }))
                bridge = HookBridge(settings, root)
                self.addCleanup(bridge.close)
                with patch("lifeos_hook_bridge.bridge._trusted_project", return_value=True), patch(
                    "lifeos_hook_bridge.bridge._scope_cwd", return_value=str(project)
                ):
                    bridge._remember_project(str(project), "project-session")
                    verdict = bridge._kanban_task_verdict({"title": "Meaningful task description"}, "project-session", "first")
                    self.assertEqual(verdict["action"], "block")
                    self.assertIn("verified installation", verdict["message"])
                    (hooks / RECORD_NAME).write_text(json.dumps(capability_record()))
                    self.assertTrue(bridge._supports_native_task_hook("project-session", str(project)))
                    bridge.task_counts["project-session"] = 50
                    bridge.task_state_loaded.add("project-session")
                    verdict = bridge._kanban_task_verdict({"title": "Meaningful task description"}, "project-session", "second")
                    self.assertIn("session limit of 50", verdict["message"])
                    native.write_text(native.read_text() + "\n// modified installed hook\n")
                    verdict = bridge._task_created_verdict({"todos": [{"id": "one", "content": "Meaningful task description"}]}, "project-session", "third")
                    self.assertIn("verified installation", verdict["message"])
