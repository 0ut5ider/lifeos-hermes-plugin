# ABOUTME: Exercises a PermissionRequest command replacement through the real Hermes plugin manager.
# ABOUTME: Runs in a disposable Hermes home and verifies the original command never executes.

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

from hermes_cli import plugins as plugins_mod
from tools import terminal_tool as terminal_module


def main() -> None:
    source = Path(__file__).resolve().parents[1]
    installed = Path.home() / ".hermes/plugins/lifeos-hook-bridge"
    assert (installed / "bridge.py").read_bytes() == (source / "lifeos_hook_bridge/bridge.py").read_bytes()
    with tempfile.TemporaryDirectory(prefix="lifeos-command-rewrite-") as directory:
        root = Path(directory)
        home = root / "hermes"
        plugin = home / "plugins/lifeos-hook-bridge"
        plugin.parent.mkdir(parents=True)
        shutil.copytree(installed, plugin)
        (home / "config.yaml").write_text("plugins:\n  enabled:\n    - lifeos-hook-bridge\n")
        original = root / "original"
        original_command = f"printf ORIGINAL > {original}; printf DONE"
        hook = root / "replace.py"
        hook.write_text(
            "import json,sys\n"
            "data=json.load(sys.stdin)\n"
            f"assert data['tool_input']['command']=={original_command!r}\n"
            "print(json.dumps({'hookSpecificOutput':{'hookEventName':'PermissionRequest',"
            "'decision':{'behavior':'allow','updatedInput':{'command':'pwd'}}}}))\n"
        )
        settings = root / "settings.json"
        settings.write_text(json.dumps({"hooks": {
            "PermissionRequest": [{"matcher": "Bash", "hooks": [
                {"type": "command", "command": f"{sys.executable} {hook}"},
            ]}],
        }}))
        previous = {key: os.environ.get(key) for key in ("HERMES_HOME", "LIFEOS_HOOK_SETTINGS")}
        os.environ["HERMES_HOME"] = str(home)
        os.environ["LIFEOS_HOOK_SETTINGS"] = str(settings)
        try:
            plugins_mod._reset_plugin_managers_for_tests()
            args = {"command": original_command, "workdir": str(root)}
            result = json.loads(terminal_module._handle_terminal(args, task_id="rewrite-installed"))
            outcome = {
                "status": result.get("status"),
                "effective_command": args["command"],
                "original_exists": original.exists(),
                "output": result.get("output", "").strip(),
            }
            print(json.dumps(outcome, indent=2))
            assert not original.exists(), outcome
            assert args["command"] == "pwd", outcome
            assert result.get("exit_code") == 0, outcome
            assert str(root) in result.get("output", ""), outcome
        finally:
            plugins_mod._reset_plugin_managers_for_tests()
            for key, value in previous.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value


if __name__ == "__main__":
    main()
