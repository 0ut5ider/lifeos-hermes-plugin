# ABOUTME: Checks native ContextReduction through the installed Hermes plugin manager.
# ABOUTME: Uses a temporary rtk executable and disposable Hermes settings.

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from hermes_cli import plugins as plugins_mod
from tools.approval import check_all_command_guards


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="lifeos-context-contract-") as temporary:
        root = Path(temporary)
        home = root / "hermes"
        plugin = home / "plugins/lifeos-hook-bridge"
        plugin.parent.mkdir(parents=True)
        shutil.copytree(Path.home() / ".hermes/plugins/lifeos-hook-bridge", plugin)
        (home / "config.yaml").write_text(
            "plugins:\n  enabled:\n    - lifeos-hook-bridge\napprovals:\n  mode: manual\n"
        )
        settings = root / "settings.json"
        settings.write_text(json.dumps({
            "hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [{
                "type": "command", "command": str(Path.home() / ".claude/hooks/ContextReduction.hook.sh"),
            }]}]},
            "permissions": {"allow": ["Bash"]},
        }))
        bin_dir = root / "bin"
        bin_dir.mkdir()
        marker = root / "rtk-called.txt"
        rtk = bin_dir / "rtk"
        rtk.write_text(f"#!/bin/sh\nprintf '%s' \"$*\" > {marker}\nprintf 'SYNTHETIC-RTK-RESULT\\n'\n")
        rtk.chmod(0o755)
        old_env = dict(os.environ)
        os.environ["PATH"] = f"{bin_dir}:{old_env.get('PATH', '')}"
        os.environ["HERMES_HOME"] = str(home)
        os.environ["LIFEOS_HOOK_SETTINGS"] = str(settings)
        try:
            plugins_mod._reset_plugin_managers_for_tests()
            details = plugins_mod._get_pre_tool_call_directive_details(
                "terminal", {"command": "git status"}, session_id="context-probe",
            )
            modified = details.modified_args or {"command": "git status"}
            approval_calls = []
            guard = check_all_command_guards(
                modified["command"], "local",
                approval_callback=lambda *args, **kwargs: approval_calls.append(args) or "deny",
            )
            run = subprocess.run(modified["command"], shell=True, cwd=root, env=os.environ,
                                 text=True, capture_output=True, timeout=5)
            print(json.dumps({
                "pretool_action": details.action,
                "modified_command": modified["command"],
                "guard_approved": guard["approved"],
                "guard_prompts": len(approval_calls),
                "execution_returncode": run.returncode,
                "execution_stdout": run.stdout.strip(),
                "rtk_executed": marker.exists(),
                "rtk_arguments": marker.read_text() if marker.exists() else None,
            }))
        finally:
            plugins_mod._reset_plugin_managers_for_tests()
            os.environ.clear()
            os.environ.update(old_env)


if __name__ == "__main__":
    main()
