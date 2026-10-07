# ABOUTME: Runs an asynchronous LifeOS hook after the Hermes process exits.
# ABOUTME: Reads and removes a private payload file before starting the hook command.

from __future__ import annotations

import json
import importlib.util
import os
import subprocess
import sys
import tempfile
import time
from contextlib import nullcontext
from pathlib import Path


def main() -> int:
    spool = Path(sys.argv[1])
    try:
        request = json.loads(spool.read_text())
    finally:
        spool.unlink(missing_ok=True)
    if request.get("remote"):
        return _run_remote(request)
    try:
        with _state_lock(request), tempfile.TemporaryFile(mode="w+t", encoding="utf-8") as output:
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


def _state_lock(request: dict):
    key = request.get("state_key")
    if key is None:
        return nullcontext()
    if not isinstance(key, str) or not isinstance(request.get("state_root"), str):
        raise ValueError("Native hook state scope is invalid")
    path = Path(__file__).resolve().parents[1] / "hook_state.py"
    spec = importlib.util.spec_from_file_location("lifeos_hook_state", path)
    if spec is None or spec.loader is None:
        raise ImportError("Native hook state coordination is unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.session_state(Path(request["state_root"]), key)


def _run_remote(request: dict) -> int:
    try:
        for path in reversed([request["plugin_root"], request["source_root"], *request.get("python_paths", [])]):
            if path and os.path.isabs(path):
                sys.path.insert(0, path)
        from remote_hooks import DockerExecBackend, run_project_hook

        remote = request["remote"]
        if remote.get("type") == "ssh":
            from tools.environments.ssh import SSHEnvironment
            backend = SSHEnvironment(
                host=remote["host"], user=remote["user"], port=remote["port"],
                key_path=remote["key_path"], cwd=request["cwd"], probe_only=True,
            )
            cleanup = backend.cleanup
        elif remote.get("type") == "docker":
            backend = DockerExecBackend(remote["executable"], remote["container_id"])
            cleanup = lambda: None
        else:
            return 1
        try:
            result = run_project_hook(
                backend, request["command"], request["payload"], request["cwd"],
                request.get("timeout", 60), request.get("environment", {}),
            )
        finally:
            cleanup()
        if result is None:
            return 1
        if result.returncode == 0 and len(result.stdout) <= 65536:
            _save_context(request, result.stdout)
        return result.returncode
    except (OSError, ValueError, KeyError, ImportError, TypeError) as error:
        print(f"Remote hook runner failed: {error}", file=sys.stderr)
        return 1


def _save_context(request: dict, response: str) -> None:
    event = request["payload"].get("hook_event_name", "")
    text = response.strip()
    if text.startswith("{") and text.endswith("}"):
        try:
            parsed = json.loads(text)
        except (json.JSONDecodeError, ValueError):
            return
    else:
        if event not in {"SessionStart", "UserPromptSubmit"} or not response.strip():
            return
        parsed = {"hookSpecificOutput": {"hookEventName": event, "additionalContext": text}}
    if not isinstance(parsed, dict):
        return
    specific = parsed.get("hookSpecificOutput") or {}
    if not isinstance(specific, dict) or specific.get("hookEventName") != event:
        specific = {}
    context = specific.get("additionalContext")
    message = parsed.get("systemMessage")
    values = {
        "session_id": request["payload"].get("session_id", ""),
        "additionalContext": context if isinstance(context, str) else "",
        "systemMessage": message if isinstance(message, str) else "",
    }
    if request.get("context_kind") == "clock":
        values.update(context_kind="clock", queued_at=request.get("queued_at"), completed_at=time.time())
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
