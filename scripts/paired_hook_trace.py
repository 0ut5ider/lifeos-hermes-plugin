# ABOUTME: Records real hook command outcomes in disposable LifeOS installations.
# ABOUTME: Forwards each command's input, output, and exit code without changing its result.

from __future__ import annotations

import argparse
import base64
import fcntl
import hashlib
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _metadata(group: dict) -> dict:
    return {key: value for key, value in group.items()
            if key != "hooks" and not (key == "matcher" and value in ("", None))}


def _write_private(path: Path, data: bytes) -> None:
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=f".{path.name}.", delete=False) as stream:
        temporary = Path(stream.name)
        os.fchmod(stream.fileno(), 0o600)
        stream.write(data)
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def instrument(manifest_path: Path, settings_path: Path, trace_path: Path) -> dict:
    for path in (manifest_path, settings_path):
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"Hook input is not a regular file: {path}")
    if not trace_path.is_absolute() or trace_path.is_symlink():
        raise ValueError("Trace path must be absolute and must not be a symbolic link")
    backup = settings_path.with_name(settings_path.name + ".paired-original")
    state = settings_path.with_name(settings_path.name + ".paired-state")
    if backup.exists() or state.exists():
        raise ValueError("Hook trace backup already exists")
    original = settings_path.read_bytes()
    installed = json.loads(original)
    source = json.loads(manifest_path.read_text(encoding="utf-8"))["hooks"]
    wrapped = 0
    http = 0
    for event, groups in source.items():
        installed_groups = installed["hooks"].get(event, [])
        for group_index, group in enumerate(groups, 1):
            for hook_index, hook in enumerate(group["hooks"], 1):
                identifier = f"{event}.{group_index}.{hook_index}"
                matches = [candidate for target_group in installed_groups
                           if _metadata(target_group) == _metadata(group)
                           for candidate in target_group["hooks"] if candidate == hook]
                if len(matches) != 1:
                    raise ValueError(f"LifeOS hook is missing or ambiguous: {identifier}")
                if hook["type"] == "http":
                    http += 1
                    continue
                if hook["type"] != "command":
                    raise ValueError(f"Unsupported hook type: {identifier}")
                command = hook["command"]
                encoded = base64.b64encode(command.encode()).decode()
                matches[0]["command"] = " ".join(shlex.quote(item) for item in (
                    sys.executable, str(Path(__file__).resolve()), "run", identifier,
                    str(trace_path), encoded,
                ))
                wrapped += 1
    if wrapped + http != sum(len(group["hooks"]) for groups in source.values() for group in groups):
        raise ValueError("Not every LifeOS registration was accounted for")
    edited = (json.dumps(installed, indent=2, ensure_ascii=False) + "\n").encode()
    shutil.copy2(settings_path, backup)
    backup.chmod(0o600)
    try:
        _write_private(settings_path, edited)
        _write_private(state, json.dumps({"original_sha256": _digest(original),
                                          "wrapped_sha256": _digest(edited),
                                          "trace": str(trace_path), "wrapped": wrapped,
                                          "http": http}).encode())
    except Exception:
        _write_private(settings_path, original)
        backup.unlink(missing_ok=True)
        state.unlink(missing_ok=True)
        raise
    return {"wrapped": wrapped, "http": http}


def restore(settings_path: Path) -> dict:
    backup = settings_path.with_name(settings_path.name + ".paired-original")
    state = settings_path.with_name(settings_path.name + ".paired-state")
    if backup.is_symlink() or state.is_symlink() or not backup.is_file() or not state.is_file():
        raise ValueError("Hook trace backup is missing")
    document = json.loads(state.read_text())
    original = backup.read_bytes()
    if _digest(original) != document["original_sha256"]:
        raise ValueError("Hook trace backup changed")
    current = settings_path.read_bytes()
    if _digest(current) != document["wrapped_sha256"]:
        archive = settings_path.with_name(settings_path.name + f".paired-intervening-{int(time.time())}")
        if archive.exists():
            raise ValueError("Intervening hook settings archive already exists")
        shutil.copy2(settings_path, archive)
        archive.chmod(0o600)
    _write_private(settings_path, original)
    backup.unlink()
    state.unlink()
    return {"restored": True, "original_sha256": document["original_sha256"]}


def run_hook(identifier: str, trace_path: Path, encoded_command: str) -> int:
    command = base64.b64decode(encoded_command, validate=True).decode("utf-8")
    request = sys.stdin.buffer.read()
    started = time.monotonic()
    result = subprocess.run(["/bin/bash", "-c", command], input=request,
                            capture_output=True, check=False)
    os.write(sys.stdout.fileno(), result.stdout)
    os.write(sys.stderr.fileno(), result.stderr)
    try:
        payload = json.loads(request)
    except (ValueError, UnicodeError):
        payload = {}
    row = {"id": identifier, "event": payload.get("hook_event_name"),
           "tool_name": payload.get("tool_name"), "session_id": payload.get("session_id"),
           "stdin_base64": base64.b64encode(request).decode("ascii"),
           "payload_keys": sorted(payload),
           "last_assistant_message": payload.get("last_assistant_message"),
           "stop_hook_active": payload.get("stop_hook_active"),
           "exit_code": result.returncode, "elapsed_ms": round((time.monotonic() - started) * 1000),
           "stdout": result.stdout[:8192].decode("utf-8", errors="replace"),
           "stderr": result.stderr[:8192].decode("utf-8", errors="replace"),
           "stdout_size": len(result.stdout), "stderr_size": len(result.stderr),
           "stdout_sha256": _digest(result.stdout), "stderr_sha256": _digest(result.stderr)}
    data = (json.dumps(row, ensure_ascii=False) + "\n").encode()
    descriptor = os.open(trace_path, os.O_WRONLY | os.O_CREAT | os.O_APPEND | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        os.write(descriptor, data)
    finally:
        os.close(descriptor)
    return result.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description="Record paired LifeOS hook command outcomes")
    sub = parser.add_subparsers(dest="action", required=True)
    prepare = sub.add_parser("instrument")
    prepare.add_argument("manifest", type=Path)
    prepare.add_argument("settings", type=Path)
    prepare.add_argument("trace", type=Path)
    recover = sub.add_parser("restore")
    recover.add_argument("settings", type=Path)
    invoke = sub.add_parser("run")
    invoke.add_argument("id")
    invoke.add_argument("trace", type=Path)
    invoke.add_argument("command")
    args = parser.parse_args()
    if args.action == "instrument":
        print(json.dumps(instrument(args.manifest, args.settings, args.trace)))
        return 0
    if args.action == "restore":
        print(json.dumps(restore(args.settings)))
        return 0
    return run_hook(args.id, args.trace, args.command)


if __name__ == "__main__":
    raise SystemExit(main())
