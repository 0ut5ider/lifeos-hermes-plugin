# ABOUTME: Stores correlated development events and complete private artifacts.
# ABOUTME: Removes known credentials before content addressing and compression.

from __future__ import annotations

import base64
import dataclasses
import datetime
import gzip
import hashlib
import json
import os
import re
import subprocess
import threading
import time
import uuid
from pathlib import Path

SENSITIVE = re.compile(r"(^|_)(password|passwd|secret|token|api_key|auth_token|private_key)($|_)|^authorization$|^cookie$|^set.cookie$", re.I)
TOKEN_SHAPE = re.compile(r"(?i)(Bearer\s+)[A-Za-z0-9._~+/=-]+|-----BEGIN [^-]*PRIVATE KEY-----.*?-----END [^-]*PRIVATE KEY-----", re.S)


def safe(value, secrets=(), key=""):
    if SENSITIVE.search(key) and key not in {"max_tokens", "input_tokens", "output_tokens", "total_tokens"}:
        return "[REDACTED]"
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        for secret in secrets:
            if secret:
                value = value.replace(secret, "[REDACTED]")
        return TOKEN_SHAPE.sub("[REDACTED]", value)
    if isinstance(value, bytes):
        text = value.decode("utf-8", errors="surrogateescape")
        clean = safe(text, secrets)
        return {"encoding": "base64", "bytes": base64.b64encode(clean.encode("utf-8", errors="surrogateescape")).decode()}
    if isinstance(value, Path):
        return safe(str(value), secrets)
    if isinstance(value, subprocess.CompletedProcess):
        return safe({"args": value.args, "returncode": value.returncode, "stdout": value.stdout, "stderr": value.stderr}, secrets)
    if isinstance(value, BaseException):
        result = {"type": type(value).__name__, "message": str(value)}
        if isinstance(value, subprocess.TimeoutExpired):
            result.update({"stdout": value.stdout, "stderr": value.stderr, "timeout": value.timeout})
        return safe(result, secrets)
    if isinstance(value, dict):
        return {str(k): safe(v, secrets, str(k)) for k, v in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [safe(v, secrets) for v in value]
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {f.name: safe(getattr(value, f.name), secrets, f.name) for f in dataclasses.fields(value)}
    return {"unsupported_type": f"{type(value).__module__}.{type(value).__name__}"}


class Recorder:
    def __init__(self, root: Path, run_id: str, secrets=()):
        if not re.fullmatch(r"[A-Za-z0-9_-]+", run_id):
            raise ValueError("Invalid capture run identifier")
        self.root = Path(root)
        self.run_id = run_id
        self.secrets = sorted(set(secrets), key=len, reverse=True)
        self.process_id = uuid.uuid4().hex
        self.lock = threading.RLock()
        self.sequence = 0
        self.failures = 0
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        if self.root.is_symlink() or self.root.stat().st_uid != os.getuid() or self.root.stat().st_mode & 0o077:
            raise PermissionError("Capture root must be private and owned by this account")
        self.event_path = self._event_path()

    def _event_path(self):
        day = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
        directory = self.root / "runs" / self.run_id / "events" / day
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        return directory / f"{self.process_id}.jsonl"

    def artifact(self, value):
        clean = safe(value, self.secrets)
        data = json.dumps(clean, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        digest = hashlib.sha256(data).hexdigest()
        relative = Path("artifacts/sha256") / digest[:2] / f"{digest[2:]}.json.gz"
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if not path.exists():
            temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
            try:
                fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(fd, "wb") as stream:
                    stream.write(gzip.compress(data, mtime=0))
                    stream.flush()
                # Link publishes an immutable object without replacing an existing one.
                try:
                    os.link(temporary, path)
                except FileExistsError:
                    pass
            finally:
                temporary.unlink(missing_ok=True)
        return {"sha256": digest, "path": str(relative), "bytes": len(data)}

    def emit(self, stage, *, data=None, **fields):
        try:
            reference = self.artifact(data) if data is not None else None
            with self.lock:
                self.sequence += 1
                record = {"schema_version": 1, "event_id": uuid.uuid4().hex,
                          "run_id": self.run_id, "process_id": self.process_id,
                          "sequence": self.sequence, "time_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                          "monotonic_ns": time.monotonic_ns(), "pid": os.getpid(),
                          "thread_id": threading.get_ident(), "stage": stage,
                          **safe(fields, self.secrets)}
                if reference:
                    record["data_ref"] = reference
                if self.failures:
                    record["prior_capture_failures"] = self.failures
                self.event_path = self._event_path()
                fd = os.open(self.event_path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
                with os.fdopen(fd, "a", encoding="utf-8") as stream:
                    stream.write(json.dumps(record, ensure_ascii=True, separators=(",", ":")) + "\n")
                return record
        except Exception as error:
            self.failures += 1
            # No exception text here: the error may contain private payload data.
            try:
                os.write(2, f"Development capture lost an event ({type(error).__name__}); total={self.failures}\n".encode())
            except OSError:
                pass
            return None
