# ABOUTME: Checks the installed LifeOS bridge through Hermes's real plugin manager.
# ABOUTME: Uses a disposable Hermes home and synthetic hooks without changing the gateway profile.

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

from hermes_cli import plugins as plugins_mod


def main() -> None:
    installed = Path.home() / ".hermes/plugins/lifeos-hook-bridge"
    with tempfile.TemporaryDirectory(prefix="lifeos-installed-contract-") as directory:
        root = Path(directory)
        home = root / "hermes"
        plugin = home / "plugins/lifeos-hook-bridge"
        plugin.parent.mkdir(parents=True)
        shutil.copytree(installed, plugin)
        (home / "config.yaml").write_text("plugins:\n  enabled:\n    - lifeos-hook-bridge\n")
        hook = root / "hook.py"
        events = root / "events.jsonl"
        hook.write_text(
            "import json,sys\nfrom pathlib import Path\n"
            "data=json.load(sys.stdin)\n"
            f"with Path({str(events)!r}).open('a') as stream: stream.write(json.dumps(data)+'\\n')\n"
            "if data['hook_event_name']=='PreToolUse':\n"
            " print(json.dumps({'hookSpecificOutput':{'hookEventName':'PreToolUse',"
            "'permissionDecision':'ask','permissionDecisionReason':'Synthetic installed review'}}))\n"
            "elif data['hook_event_name']=='PermissionRequest':\n"
            " print(json.dumps({'hookSpecificOutput':{'hookEventName':'PermissionRequest',"
            "'decision':{'behavior':'allow'}}}))\n"
            "else:\n"
            " print(json.dumps({'hookSpecificOutput':{'hookEventName':'SessionStart',"
            "'additionalContext':'SYNTHETIC-START'}}))\n"
        )
        settings = root / "settings.json"
        settings.write_text(json.dumps({"hooks": {
            "PreToolUse": [{"matcher": "Read", "hooks": [{"type": "command", "command": f"{sys.executable} {hook}"}]}],
            "SessionStart": [{"matcher": "startup", "hooks": [{"type": "command", "command": f"{sys.executable} {hook}"}]}],
        }}))
        previous_home = os.environ.get("HERMES_HOME")
        previous_settings = os.environ.get("LIFEOS_HOOK_SETTINGS")
        os.environ["HERMES_HOME"] = str(home)
        os.environ["LIFEOS_HOOK_SETTINGS"] = str(settings)
        try:
            plugins_mod._reset_plugin_managers_for_tests()
            details = plugins_mod._get_pre_tool_call_directive_details(
                "read_file", {"path": str(root / "note.txt")}, session_id="installed-probe",
            )
            start = plugins_mod.invoke_hook(
                "pre_llm_call", user_message="Synthetic prompt", session_id="installed-start",
                is_first_turn=True,
            )
            rows = [json.loads(line) for line in events.read_text().splitlines()]
            result = {
                "approval_action": details.action,
                "approval_message": details.message,
                "approval_rule_key": details.rule_key,
                "start_results": start,
                "hook_events": [{"event": row["hook_event_name"], "source": row.get("source")}
                                for row in rows],
            }
            print(json.dumps(result, indent=2))
            assert details.action == "approve"
            assert details.message == "Synthetic installed review"
            assert any(row["hook_event_name"] == "SessionStart" and row["source"] == "startup" for row in rows)

            policy = root / "policy"
            policy.mkdir()
            (policy / "managed-settings.json").write_text("{")
            settings.write_text(json.dumps({"hooks": {
                "PermissionRequest": [{"matcher": "Write", "hooks": [
                    {"type": "command", "command": f"{sys.executable} {hook}"},
                ]}],
            }}))
            bridge_modules = [module for module in tuple(sys.modules.values())
                              if str(getattr(module, "__file__", "")).endswith("lifeos-hook-bridge/bridge.py")]
            assert len(bridge_modules) == 1, bridge_modules
            bridge_module = bridge_modules[0]
            previous_policy = bridge_module.POLICY_DIRECTORY
            bridge_module.POLICY_DIRECTORY = policy
            try:
                read = plugins_mod._get_pre_tool_call_directive_details(
                    "read_file", {"path": str(root / "note.txt")}, session_id="installed-policy",
                )
                write = plugins_mod._get_pre_tool_call_directive_details(
                    "write_file", {"path": str(root / "note.txt"), "content": "synthetic"},
                    session_id="installed-policy",
                )
            finally:
                bridge_module.POLICY_DIRECTORY = previous_policy
            print(json.dumps({"invalid_policy_read": read.action, "invalid_policy_write": write.action}))
            assert read.action == "approve"
            assert write.action == "approve"
        finally:
            plugins_mod._reset_plugin_managers_for_tests()
            if previous_home is None:
                os.environ.pop("HERMES_HOME", None)
            else:
                os.environ["HERMES_HOME"] = previous_home
            if previous_settings is None:
                os.environ.pop("LIFEOS_HOOK_SETTINGS", None)
            else:
                os.environ["LIFEOS_HOOK_SETTINGS"] = previous_settings


if __name__ == "__main__":
    main()
