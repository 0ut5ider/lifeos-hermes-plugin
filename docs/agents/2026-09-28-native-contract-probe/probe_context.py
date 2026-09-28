# ABOUTME: Tests the installed LifeOS ContextReduction rewrite with a temporary rtk executable.
# ABOUTME: Records execution and permission results in the isolated Claude reference account.

import json
import os
import pwd
import subprocess
import tempfile
from pathlib import Path


home = Path(pwd.getpwuid(os.getuid()).pw_dir)
with tempfile.TemporaryDirectory(prefix="parity-context-", dir=home / ".claude") as temporary:
    root = Path(temporary)
    bin_dir = root / "bin"
    bin_dir.mkdir()
    marker = root / "rtk-called.txt"
    rtk = bin_dir / "rtk"
    rtk.write_text(f"#!/bin/sh\nprintf '%s' \"$*\" > {marker}\nprintf 'SYNTHETIC-RTK-RESULT\\n'\n")
    rtk.chmod(0o755)
    environment = dict(os.environ)
    environment["PATH"] = f"{bin_dir}:{environment.get('PATH', '')}"
    command = [str(home / ".local/bin/lifeos-reference"), "-p",
               "Use Bash exactly once with the command `git status`. Report the exact tool output.",
               "--output-format", "json", "--permission-mode", "default", "--max-turns", "3"]
    result = subprocess.run(command, cwd=root, env=environment, capture_output=True, text=True, timeout=180)
    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError:
        output = {}
    print(json.dumps({
        "returncode": result.returncode,
        "permission_denials": output.get("permission_denials"),
        "rtk_executed": marker.exists(),
        "rtk_arguments": marker.read_text() if marker.exists() else None,
        "result_excerpt": str(output.get("result", ""))[-500:],
        "stderr_tail": result.stderr[-500:],
    }))
