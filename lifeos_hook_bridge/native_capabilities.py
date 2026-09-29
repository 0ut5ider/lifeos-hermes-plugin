# ABOUTME: Verifies installed native hook contracts against the bundled capability record.
# ABOUTME: Rejects missing provenance and changed hook bytes without invoking hooks.

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path


RECORD_NAME = "lifeos-bridge-capabilities.json"


def capability_record() -> dict:
    return json.loads(Path(__file__).with_name("native_capabilities.json").read_text())


def install_capability_record(payload: Path) -> None:
    expected = capability_record()
    hooks = payload / "hooks"
    if not hooks.is_dir():
        return
    for name, digest in expected["files"].items():
        path = hooks / name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            return
    shutil.copyfile(Path(__file__).with_name("native_capabilities.json"), hooks / RECORD_NAME)


def supports_task_count(root: Path) -> bool:
    try:
        expected = capability_record()
        record = root / "hooks" / RECORD_NAME
        if record.is_symlink() or json.loads(record.read_text()) != expected:
            return False
        return all(hashlib.sha256((root / "hooks" / name).read_bytes()).hexdigest() == digest
                   for name, digest in expected["files"].items())
    except (OSError, ValueError, TypeError):
        return False
