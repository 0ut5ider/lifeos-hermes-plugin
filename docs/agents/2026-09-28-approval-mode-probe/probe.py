# ABOUTME: Measures native Claude Code permission-rule behavior in default and bypass modes.
# ABOUTME: Records real hook events and a synthetic file effect for each mode.

import json
import os
import pwd
import subprocess
import sys
import tempfile
from pathlib import Path


mode = sys.argv[1]
rule = sys.argv[2] if len(sys.argv) > 2 else "deny"
home = Path(pwd.getpwuid(os.getuid()).pw_dir)
with tempfile.TemporaryDirectory(prefix="lifeos-approval-mode-", dir=home / ".claude") as temporary:
    root = Path(temporary)
    marker = root / "effect.txt"
    command = f"printf APPROVAL_MODE > {marker}"
    events = root / "events.jsonl"
    hook = root / "hook.py"
    hook.write_text(
        "import json,sys\n"
        "from pathlib import Path\n"
        "event=json.load(sys.stdin)\n"
        f"with Path({str(events)!r}).open('a') as output: output.write(json.dumps(event)+'\\n')\n"
    )
    settings = root / "settings.json"
    settings.write_text(json.dumps({
        "permissions": {"deny": [f"Bash({command})"]} if rule == "deny" else {},
        "hooks": {name: [{"matcher": "Bash", "hooks": [{
            "type": "command", "command": f"python3 {hook}",
        }]}] for name in ("PreToolUse", "PermissionRequest", "PostToolUse")},
    }))
    environment = dict(os.environ)
    environment["PATH"] = f"{home / '.bun/bin'}:{home / '.local/bin'}:{environment.get('PATH', '')}"
    result = subprocess.run(
        [str(home / ".local/bin/lifeos-reference"), "-p",
         f"Use Bash once with exactly this command: `{command}`. Then report the result.",
         "--output-format", "json", "--settings", str(settings), "--setting-sources", "",
         "--permission-mode", mode, "--tools", "Bash", "--max-turns", "3"],
        cwd=root, env=environment, capture_output=True, text=True, timeout=180,
    )
    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError:
        output = {}
    records = [json.loads(line) for line in events.read_text().splitlines()] if events.exists() else []
    print(json.dumps({
        "mode": mode, "rule": rule, "returncode": result.returncode,
        "events": [record.get("hook_event_name") for record in records],
        "tool_inputs": [record.get("tool_input") for record in records],
        "marker_exists": marker.exists(),
        "marker_content": marker.read_text() if marker.exists() else None,
        "permission_denials": output.get("permission_denials"),
        "is_error": output.get("is_error"),
        "stderr_tail": result.stderr[-500:],
    }))
