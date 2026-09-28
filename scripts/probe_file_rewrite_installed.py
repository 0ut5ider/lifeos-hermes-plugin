# ABOUTME: Checks a Write input replacement through the installed Hermes plugin manager.
# ABOUTME: Uses a disposable workspace and confirms LifeOS rules inspect the final target.

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

from hermes_cli import plugins as plugins_mod
from tools import file_tools
from tools.registry import registry


def main() -> None:
    source = Path(__file__).resolve().parents[1]
    installed = Path.home() / ".hermes/plugins/lifeos-hook-bridge"
    assert (installed / "bridge.py").read_bytes() == (source / "lifeos_hook_bridge/bridge.py").read_bytes()
    with tempfile.TemporaryDirectory(prefix="lifeos-file-rewrite-") as directory:
        root = Path(directory)
        home = root / "hermes"
        plugin = home / "plugins/lifeos-hook-bridge"
        plugin.parent.mkdir(parents=True)
        shutil.copytree(installed, plugin)
        (home / "config.yaml").write_text("plugins:\n  enabled:\n    - lifeos-hook-bridge\n")
        original = root / "original.txt"
        rewritten = root / "rewritten.txt"
        output = {"hookSpecificOutput": {"hookEventName": "PermissionRequest", "decision": {
            "behavior": "allow", "updatedInput": {"file_path": str(rewritten), "content": "MODIFIED"},
        }}}
        hook = root / "rewrite.py"
        hook.write_text(
            "import json,sys\n"
            "data=json.load(sys.stdin)\n"
            f"assert data['tool_input']['file_path']=={str(original)!r}\n"
            f"print(json.dumps({output!r}))\n"
        )
        settings = root / "settings.json"
        registration = {"hooks": {"PermissionRequest": [{"matcher": "Write", "hooks": [
            {"type": "command", "command": f"{sys.executable} {hook}"},
        ]}]}}
        settings.write_text(json.dumps(registration))
        previous_env = {key: os.environ.get(key) for key in ("HERMES_HOME", "LIFEOS_HOOK_SETTINGS")}
        previous_cwd = Path.cwd()
        os.environ["HERMES_HOME"] = str(home)
        os.environ["LIFEOS_HOOK_SETTINGS"] = str(settings)
        os.chdir(root)
        try:
            plugins_mod._reset_plugin_managers_for_tests()
            args = {"path": str(original), "content": "ORIGINAL"}
            details = plugins_mod._get_pre_tool_call_directive_details(
                "write_file", args, session_id="rewrite-file-probe", task_id="rewrite-file-probe",
            )
            assert details.action is None, details
            assert details.modified_args == {"path": str(rewritten), "content": "MODIFIED"}, details
            result = json.loads(registry.dispatch("write_file", details.modified_args, task_id="rewrite-file-probe"))
            assert result.get("status") not in {"error", "blocked", "pending_approval"}, result
            assert not original.exists()
            assert rewritten.is_file(), result
            assert rewritten.read_text() == "MODIFIED", result
            registration["permissions"] = {"deny": [f"Edit(//{str(rewritten).lstrip('/')})"]}
            settings.write_text(json.dumps(registration))
            denied = plugins_mod._get_pre_tool_call_directive_details(
                "write_file", args, session_id="rewrite-file-deny", task_id="rewrite-file-deny",
            )
            assert denied.action == "block", denied
            print(json.dumps({
                "effective_args": details.modified_args,
                "original_exists": original.exists(),
                "rewritten_content": rewritten.read_text(),
                "final_target_denied": denied.action == "block",
            }, indent=2))
        finally:
            plugins_mod._reset_plugin_managers_for_tests()
            os.chdir(previous_cwd)
            for key, value in previous_env.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value


if __name__ == "__main__":
    main()
