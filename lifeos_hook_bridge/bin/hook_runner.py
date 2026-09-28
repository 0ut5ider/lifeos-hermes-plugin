# ABOUTME: Runs an asynchronous LifeOS hook after the Hermes process exits.
# ABOUTME: Reads and removes a private payload file before starting the hook command.

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def main() -> int:
    spool = Path(sys.argv[1])
    try:
        request = json.loads(spool.read_text())
    finally:
        spool.unlink(missing_ok=True)
    try:
        with tempfile.TemporaryFile(mode="w+t", encoding="utf-8") as output:
            result = subprocess.run(
                ["/bin/bash", "-c", request["command"]],
                input=json.dumps(request["payload"]), text=True,
                stdout=output, stderr=subprocess.DEVNULL,
                timeout=request.get("timeout"), check=False,
                cwd=request.get("cwd"), env=request.get("environment"),
            )
            output.seek(0)
            response = output.read(65537)
        if result.returncode == 0 and len(response) <= 65536:
            _save_context(request, response)
        return result.returncode
    except (OSError, subprocess.TimeoutExpired):
        return 1


def _save_context(request: dict, response: str) -> None:
    try:
        parsed = json.loads(response)
    except (json.JSONDecodeError, ValueError):
        parsed = {"additionalContext": response.strip()} if response.strip() else {}
    if not isinstance(parsed, dict):
        return
    specific = parsed.get("hookSpecificOutput") or {}
    if not isinstance(specific, dict):
        specific = {}
    context = specific.get("additionalContext", parsed.get("additionalContext"))
    message = parsed.get("systemMessage")
    values = {
        "session_id": request["payload"].get("session_id", ""),
        "additionalContext": context if isinstance(context, str) else "",
        "systemMessage": message if isinstance(message, str) else "",
    }
    if not values["additionalContext"].strip() and not values["systemMessage"].strip():
        return
    destination = request.get("result_path")
    if not isinstance(destination, str) or not destination:
        return
    path = Path(destination)
    temporary = path.with_suffix(".tmp")
    try:
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w") as stream:
            json.dump(values, stream)
        os.replace(temporary, path)
    except OSError:
        temporary.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
