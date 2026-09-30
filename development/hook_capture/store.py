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
from http.cookies import CookieError, SimpleCookie
from pathlib import Path
from urllib.parse import unquote, unquote_plus, quote

SENSITIVE = re.compile(r"(^|[_-])(password|passwd|secret|token|api[_-]?key|(?:access|refresh|auth)[_-]?token|private[_-]?key|client[_-]?secret|authorization|cookie)($|[_-])|^set.cookie$", re.I)
TOKEN_SHAPE = re.compile(r"(?i)(Bearer\s+)[A-Za-z0-9._~+/=-]+|-----BEGIN [^-]*PRIVATE KEY-----.*?-----END [^-]*PRIVATE KEY-----", re.S)
JSON_FIELD = re.compile(r'("(?P<field>(?:\\.|[^"\\])*)"\s*:\s*)("(?:\\.|[^"\\])*"|-?\d+(?:\.\d+)?|true|false|null)')
URL_SHAPE = re.compile(r"(?<![A-Za-z0-9+.-])[A-Za-z][A-Za-z0-9+.-]*://[^\s<>\"']+")


def url_credentials(value):
    for match in URL_SHAPE.finditer(value):
        _, address = match.group(0).split("://", 1)
        authority = re.split(r"[/?#]", address, maxsplit=1)[0]
        if "@" in authority:
            userinfo = authority.rsplit("@", 1)[0]
            if ":" in userinfo:
                yield unquote(userinfo.split(":", 1)[1])
        for parameters in re.split(r"[?#]", address)[1:]:
            for field in parameters.split("&"):
                key, separator, item = field.partition("=")
                if separator and SENSITIVE.search(unquote_plus(key)):
                    yield unquote_plus(item)


def redact_url(match):
    scheme, address = match.group(0).split("://", 1)
    authority = re.split(r"[/?#]", address, maxsplit=1)[0]
    if "@" in authority:
        address = quote("[REDACTED]", safe="") + "@" + authority.rsplit("@", 1)[1] + address[len(authority):]
    def parameter(match):
        prefix, key, item = match.groups()
        return prefix + key + "=" + quote("[REDACTED]", safe="") if SENSITIVE.search(unquote_plus(key)) else match.group(0)
    address = re.sub(r"([?&#])([^=?&#]+)=([^&#]*)", parameter, address)
    return scheme + "://" + address


def declared_secrets(value, seen=None, credential=False, key=""):
    if seen is None:
        seen = set()
    if isinstance(value, str):
        if credential and len(value) >= 4 and value != "[REDACTED]":
            yield value
        if key.casefold().replace("-", "_") in {"authorization", "proxy_authorization"}:
            parts = value.split()
            if len(parts) == 2 and parts[0].casefold() == "basic":
                if len(parts[1]) >= 4:
                    yield parts[1]
                try:
                    decoded = base64.b64decode(parts[1], validate=True).decode("utf-8")
                    if len(decoded) >= 4:
                        yield decoded
                    _, separator, password = decoded.partition(":")
                    if separator and len(password) >= 4:
                        yield password
                except (ValueError, UnicodeError):
                    pass
        if key.casefold().replace("-", "_") in {"cookie", "set_cookie"}:
            cookie = SimpleCookie()
            try:
                cookie.load(value)
                yield from (item.value for item in cookie.values() if len(item.value) >= 4)
            except CookieError:
                pass
        for match in TOKEN_SHAPE.finditer(value):
            token = match.group(0)[len(match.group(1)):] if match.group(1) else match.group(0)
            if len(token) >= 4:
                yield token
        yield from (item for item in url_credentials(value) if len(item) >= 4)
        if value.lstrip().startswith(("{", "[")):
            try:
                yield from declared_secrets(json.loads(value), seen)
            except (ValueError, RecursionError):
                pass
        for match in JSON_FIELD.finditer(value):
            try:
                key = json.loads('"' + match.group("field") + '"')
                if SENSITIVE.search(key):
                    yield from declared_secrets(json.loads(match.group(3)), seen, True, key)
            except ValueError:
                pass
        return
    if isinstance(value, bytes):
        yield from declared_secrets(value.decode("utf-8", errors="surrogateescape"), seen, credential, key)
        return
    if isinstance(value, subprocess.CompletedProcess):
        yield from declared_secrets({"args": value.args, "returncode": value.returncode,
                                    "stdout": value.stdout, "stderr": value.stderr}, seen)
        return
    if isinstance(value, BaseException):
        fields = {"message": str(value)}
        if isinstance(value, subprocess.TimeoutExpired):
            fields.update({"stdout": value.stdout, "stderr": value.stderr})
        yield from declared_secrets(fields, seen)
        return
    if isinstance(value, (dict, list, tuple, set, frozenset)) or dataclasses.is_dataclass(value):
        context = (id(value), credential, key)
        if context in seen:
            return
        seen.add(context)
    if isinstance(value, dict):
        for key, item in value.items():
            yield from declared_secrets(item, seen, credential or bool(SENSITIVE.search(str(key))), str(key))
    elif isinstance(value, (list, tuple, set, frozenset)):
        for item in value:
            yield from declared_secrets(item, seen, credential, key)
    elif dataclasses.is_dataclass(value) and not isinstance(value, type):
        for field in dataclasses.fields(value):
            yield from declared_secrets(getattr(value, field.name), seen, credential or bool(SENSITIVE.search(field.name)), field.name)


def safe(value, secrets=(), key=""):
    if SENSITIVE.search(key) and key not in {"max_tokens", "input_tokens", "output_tokens", "total_tokens"}:
        return "[REDACTED]"
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        value = URL_SHAPE.sub(redact_url, value)
        for secret in secrets:
            if secret:
                value = value.replace(secret, "[REDACTED]")
        value = TOKEN_SHAPE.sub("[REDACTED]", value)
        if value.lstrip().startswith(("{", "[")):
            try:
                parsed = json.loads(value)
                clean = safe(parsed, secrets)
                if clean != parsed:
                    return json.dumps(clean, ensure_ascii=True, separators=(",", ":"))
            except (ValueError, RecursionError):
                pass
        def redact_fragment(match):
            try:
                field = json.loads('"' + match.group("field") + '"')
            except ValueError:
                return match.group(0)
            return match.group(1) + '"[REDACTED]"' if SENSITIVE.search(field) else match.group(0)
        return JSON_FIELD.sub(redact_fragment, value)
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
        with self.lock:
            self.secrets = sorted(set(self.secrets).union(declared_secrets(value)), key=len, reverse=True)
            secrets = self.secrets
        clean = safe(value, secrets)
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
