# ABOUTME: Runs an asynchronous LifeOS hook after the Hermes process exits.
# ABOUTME: Reads and removes a private payload file before starting the hook command.

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def main() -> int:
    spool = Path(sys.argv[1])
    try:
        request = json.loads(spool.read_text())
    finally:
        spool.unlink(missing_ok=True)
    try:
        result = subprocess.run(
            ["/bin/bash", "-c", request["command"]],
            input=json.dumps(request["payload"]), text=True,
            timeout=request["timeout"], check=False,
        )
        return result.returncode
    except (OSError, subprocess.TimeoutExpired):
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
