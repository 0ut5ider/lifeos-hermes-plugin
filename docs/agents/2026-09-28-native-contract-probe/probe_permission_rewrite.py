# ABOUTME: Measures Claude Code PermissionRequest input rewrites on a synthetic Bash call.
# ABOUTME: Uses disposable files to distinguish original execution from rewritten execution.

import json
import os
import pwd
import subprocess
import sys
import tempfile
from pathlib import Path


home = Path(pwd.getpwuid(os.getuid()).pw_dir)
mode = sys.argv[1] if len(sys.argv) > 1 else "rewrite"
with tempfile.TemporaryDirectory(prefix="parity-permission-rewrite-", dir=home / ".claude") as temporary:
    root = Path(temporary)
    original = root / "original.txt"
    rewritten = root / "rewritten.txt"
    event_path = root / "event.json"
    post_path = root / "post.json"
    hook = root / "hook.py"
    post_hook = root / "post.py"
    hook.write_text(
        "import json,sys\nfrom pathlib import Path\n"
        "data=json.load(sys.stdin)\n"
        f"Path({str(event_path)!r}).write_text(json.dumps(data))\n"
        "changed=dict(data['tool_input'])\n"
        f"changed['command']='pwd' if {mode!r} == 'rewrite_pwd' else 'printf MODIFIED > {rewritten}'\n"
        "decision={'behavior':'allow'}\n"
        f"if {mode!r} in ('rewrite', 'rewrite_pwd'): decision['updatedInput']=changed\n"
        "print(json.dumps({'hookSpecificOutput':{'hookEventName':'PermissionRequest',"
        "'decision':decision}}))\n"
    )
    post_hook.write_text(
        "import json,sys\nfrom pathlib import Path\n"
        f"Path({str(post_path)!r}).write_text(json.dumps(json.load(sys.stdin)))\n"
    )
    settings = root / "settings.json"
    settings.write_text(json.dumps({
        "hooks": {"PermissionRequest": [{
            "matcher": "Bash", "hooks": [{"type": "command", "command": f"python3 {hook}"}],
        }], "PostToolUse": [{
            "matcher": "Bash", "hooks": [{"type": "command", "command": f"python3 {post_hook}"}],
        }]},
        "permissions": {"allow": [f"Bash(printf MODIFIED > {rewritten})"]},
    }))
    command = f"printf ORIGINAL > {original}; printf DONE"
    environment = dict(os.environ)
    environment["PATH"] = f"{home / '.bun/bin'}:{home / '.local/bin'}:{environment.get('PATH', '')}"
    result = subprocess.run(
        [str(home / ".local/bin/lifeos-reference"), "-p",
         f"Use Bash once with exactly this command: `{command}`. Report its result.",
         "--output-format", "json", "--settings", str(settings),
         "--setting-sources", "",
         "--permission-mode", "default", "--tools", "Bash", "--max-turns", "3"],
        cwd=root, env=environment, capture_output=True, text=True, timeout=180,
    )
    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError:
        output = {}
    event = json.loads(event_path.read_text()) if event_path.exists() else {}
    post = json.loads(post_path.read_text()) if post_path.exists() else {}
    print(json.dumps({
        "returncode": result.returncode,
        "mode": mode,
        "permission_hook_ran": event_path.exists(),
        "hook_tool_input": event.get("tool_input"),
        "post_tool_input": post.get("tool_input"),
        "post_tool_response_excerpt": str(post.get("tool_response", ""))[-250:],
        "original_exists": original.exists(),
        "rewritten_exists": rewritten.exists(),
        "rewritten_content": rewritten.read_text() if rewritten.exists() else None,
        "permission_denials": output.get("permission_denials"),
        "is_error": output.get("is_error"),
        "stderr_tail": result.stderr[-350:],
    }))
