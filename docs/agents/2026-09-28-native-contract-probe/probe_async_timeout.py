# ABOUTME: Measures Claude Code's timeout for an asynchronous prompt hook.
# ABOUTME: Uses a disposable script that records start and completion markers.

import json
import os
import pwd
import subprocess
import tempfile
import time
from pathlib import Path


home = Path(pwd.getpwuid(os.getuid()).pw_dir)
with tempfile.TemporaryDirectory(prefix="parity-async-timeout-", dir=home / ".claude") as temporary:
    root = Path(temporary)
    started = root / "started"
    finished = root / "finished"
    hook = root / "hook.py"
    hook.write_text(
        "import json,sys,time\nfrom pathlib import Path\n"
        "json.load(sys.stdin)\n"
        f"Path({str(started)!r}).touch()\n"
        "time.sleep(3)\n"
        f"Path({str(finished)!r}).touch()\n"
    )
    settings = root / "settings.json"
    settings.write_text(json.dumps({"hooks": {"UserPromptSubmit": [{"hooks": [{
        "type": "command", "command": f"python3 {hook}", "async": True, "timeout": 1,
    }]}]}}))
    environment = dict(os.environ)
    environment["PATH"] = f"{home / '.bun/bin'}:{home / '.local/bin'}:{environment.get('PATH', '')}"
    result = subprocess.run(
        [str(home / ".local/bin/lifeos-reference"), "-p", "Reply READY without tools.",
         "--output-format", "json", "--settings", str(settings), "--tools", "", "--max-turns", "1"],
        cwd=home / ".claude", env=environment, text=True, capture_output=True, timeout=180,
    )
    time.sleep(4)
    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError:
        output = {}
    print(json.dumps({
        "returncode": result.returncode,
        "is_error": output.get("is_error"),
        "started": started.exists(),
        "finished_after_four_seconds": finished.exists(),
        "stderr_tail": result.stderr[-350:],
    }))
