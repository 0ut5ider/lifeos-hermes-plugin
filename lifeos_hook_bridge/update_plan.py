# ABOUTME: Plans LifeOS system file changes from a fresh candidate installation.
# ABOUTME: Rejects modified or colliding installed files before an update changes them.

from __future__ import annotations

import hashlib
import os
import shutil
import tempfile
from pathlib import Path


SYSTEM_PREFIXES = ("hooks/", "skills/", "agents/", "commands/", "test/", "LIFEOS/")
SKIP_DIRS = frozenset({"node_modules", ".git", ".cache", ".venv", "__pycache__", "dist", "build"})


class UpdateConflict(ValueError):
    pass


def _digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def _system_path(name: str) -> bool:
    if not any(name.startswith(prefix) for prefix in SYSTEM_PREFIXES):
        return False
    path = Path(name)
    return not path.is_absolute() and not any(
        part in SKIP_DIRS or part in {".", "..", "USER", "MEMORY"} for part in path.parts
    )


def _checked_path(root: Path, name: str) -> Path:
    if not _system_path(name):
        raise UpdateConflict(f"Invalid LifeOS system path: {name}")
    path = root
    for part in Path(name).parts:
        path = path / part
        if path.is_symlink():
            raise UpdateConflict(f"LifeOS system path contains a symbolic link: {name}")
    return path


def _reference_files(reference: Path):
    for directory, names, files in os.walk(reference, followlinks=False):
        parent = Path(directory)
        names[:] = [name for name in names if name not in SKIP_DIRS and
                   not (parent / name).is_symlink()]
        for filename in files:
            installed = parent / filename
            name = installed.relative_to(reference).as_posix()
            if _system_path(name):
                yield name, installed


def deployed_system_files(source: Path, reference: Path) -> dict[str, str]:
    if source.is_symlink() or reference.is_symlink() or not source.is_dir() or not reference.is_dir():
        raise UpdateConflict("LifeOS source and reference must be regular directories")
    found = {}
    for name, installed in _reference_files(reference):
        filename = installed.name
        if installed.is_symlink() or not installed.is_file():
            raise UpdateConflict(f"Reference system path is not a regular file: {name}")
        payload = _checked_path(source, name)
        if not payload.is_file():
            continue
        reference_hash = _digest(installed)
        if reference_hash != _digest(payload):
            if filename == "bun.lock":
                continue
            raise UpdateConflict(f"Reference system file differs from source: {name}")
        found[name] = reference_hash
    return dict(sorted(found.items()))


def plan_system_files(current: Path, baseline: dict, source: Path, reference: Path) -> dict:
    if current.is_symlink() or not current.is_dir():
        raise UpdateConflict("Installed LifeOS root must be a regular directory")
    if baseline.get("installed_root") != str(current.resolve()):
        raise UpdateConflict("VersionDrift baseline belongs to another installation")
    previous = baseline.get("files")
    if not isinstance(previous, dict) or not previous:
        raise UpdateConflict("VersionDrift baseline has no system files")
    desired = deployed_system_files(source, reference)
    for name, previous_hash in previous.items():
        path = _checked_path(current, name)
        if not path.is_file() or _digest(path) != previous_hash:
            raise UpdateConflict(f"Installed LifeOS system file changed since baseline: {name}")
    add = []
    replace = []
    for name, desired_hash in desired.items():
        path = _checked_path(current, name)
        if name in previous:
            if previous[name] != desired_hash:
                replace.append(name)
        elif path.exists():
            if not path.is_file() or _digest(path) != desired_hash:
                raise UpdateConflict(f"New LifeOS system file collides with an existing file: {name}")
        else:
            add.append(name)
    dependency_locks = sorted(name for name, path in _reference_files(reference)
                              if path.name == "bun.lock")
    remove = sorted(set(previous) - set(desired) - set(dependency_locks))
    return {"add": add, "replace": replace, "remove": remove,
            "desired": desired, "previous": previous,
            "dependency_locks": dependency_locks}


def apply_system_plan(staged: Path, source: Path, plan: dict) -> None:
    if staged.is_symlink() or not staged.is_dir():
        raise UpdateConflict("Staged LifeOS root must be a regular directory")
    for name in (*plan["replace"], *plan["remove"]):
        target = _checked_path(staged, name)
        if not target.is_file() or _digest(target) != plan["previous"][name]:
            raise UpdateConflict(f"Staged LifeOS system file changed: {name}")
    for name in plan["add"]:
        if _checked_path(staged, name).exists():
            raise UpdateConflict(f"Staged LifeOS system file collides: {name}")
    for name in (*plan["add"], *plan["replace"]):
        payload = _checked_path(source, name)
        if not payload.is_file() or _digest(payload) != plan["desired"][name]:
            raise UpdateConflict(f"Prepared LifeOS source changed: {name}")
    for name in plan["remove"]:
        _checked_path(staged, name).unlink()
    for name in (*plan["add"], *plan["replace"]):
        payload = source / name
        target = staged / name
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=target.parent, prefix=f".{target.name}.",
                                         delete=False) as stream:
            temporary = Path(stream.name)
        try:
            shutil.copy2(payload, temporary)
            os.replace(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)
    for name in (*plan["add"], *plan["replace"]):
        if _digest(staged / name) != plan["desired"][name]:
            raise UpdateConflict(f"Staged LifeOS system file differs from source: {name}")
