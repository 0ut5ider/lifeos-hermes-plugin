# ABOUTME: Tests the reference child launcher at the four LifeOS model tiers.
# ABOUTME: Reports model calls without printing the private gateway environment.

import json
import os
import pwd
import subprocess
import sys
from pathlib import Path


home = Path(pwd.getpwuid(os.getuid()).pw_dir)
launcher = home / ".config/lifeos-reference/bin/claude"
environment = dict(os.environ)
environment["PATH"] = f"{home / '.bun/bin'}:{home / '.local/bin'}:{environment.get('PATH', '')}"
for tier in ("haiku", "sonnet", "opus", "fable"):
    if len(sys.argv) > 1 and tier not in sys.argv[1:]:
        continue
    result = subprocess.run(
        [str(launcher), "--model", tier, "--effort", "high", "-p", "Reply READY.",
         "--tools", "", "--output-format", "json", "--max-turns", "1"],
        cwd=home / ".claude", capture_output=True, text=True, timeout=180,
        env=environment,
    )
    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError:
        output = {}
    print(json.dumps({
        "tier": tier,
        "returncode": result.returncode,
        "is_error": output.get("is_error"),
        "subtype": output.get("subtype"),
        "errors": [str(error)[:250] for error in output.get("errors", [])],
        "models": list(output.get("modelUsage", {})),
        "result_excerpt": str(output.get("result", ""))[-150:],
        "stderr_tail": result.stderr[-350:],
    }), flush=True)
