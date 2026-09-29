# ABOUTME: Installs dependency trees from a fresh LifeOS candidate installation.
# ABOUTME: Keeps package changes inside source-owned roots in a staged LifeOS tree.

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


SKIP = frozenset({"node_modules", ".git", ".cache", "__pycache__", "dist", "build"})


class UpdateDependencyConflict(ValueError):
    pass


def _digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def _package_roots(source: Path) -> set[Path]:
    if source.is_symlink() or not source.is_dir():
        raise UpdateDependencyConflict("LifeOS package source must be a regular directory")
    roots = set()
    for directory, names, files in os.walk(source, followlinks=False):
        parent = Path(directory)
        names[:] = [name for name in names if name not in SKIP and
                   not (parent / name).is_symlink()]
        if "package.json" not in files:
            continue
        package = parent / "package.json"
        if package.is_symlink() or not package.is_file():
            raise UpdateDependencyConflict(f"LifeOS package is not regular: {package}")
        relative = parent.relative_to(source)
        if any(part in {"USER", "MEMORY"} for part in relative.parts):
            raise UpdateDependencyConflict("LifeOS package is inside user data")
        roots.add(relative)
    return roots


def _checked(root: Path, relative: Path) -> Path:
    path = root
    for part in relative.parts:
        path = path / part
        if path.is_symlink():
            raise UpdateDependencyConflict(f"LifeOS package path contains a symbolic link: {relative}")
    return path


def _copy_file(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=target.parent, prefix=f".{target.name}.",
                                     delete=False) as stream:
        temporary = Path(stream.name)
    try:
        shutil.copy2(source, temporary)
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)


def _copy_tree(source: Path, target: Path) -> None:
    result = subprocess.run(["cp", "-a", "--reflink=auto", str(source), str(target)],
                            text=True, capture_output=True, timeout=300)
    if result.returncode:
        raise UpdateDependencyConflict(f"Dependency copy failed with code {result.returncode}")


def sync_dependencies(staged: Path, prior_source: Path, selected_source: Path,
                      reference: Path) -> dict:
    if staged.is_symlink() or reference.is_symlink() or not staged.is_dir() or not reference.is_dir():
        raise UpdateDependencyConflict("Staged LifeOS and reference must be regular directories")
    prior_roots = _package_roots(prior_source)
    selected_roots = _package_roots(selected_source)
    for relative in selected_roots:
        chosen = _checked(selected_source, relative) / "package.json"
        installed = _checked(reference, relative) / "package.json"
        target = _checked(staged, relative) / "package.json"
        if not installed.is_file() or installed.is_symlink() or _digest(installed) != _digest(chosen):
            raise UpdateDependencyConflict(f"Reference package differs from source: {relative}")
        if target.exists():
            if target.is_symlink() or not target.is_file():
                raise UpdateDependencyConflict(f"Package target is not regular: {relative}")
            allowed = {_digest(chosen)}
            if relative in prior_roots:
                allowed.add(_digest(prior_source / relative / "package.json"))
            if _digest(target) not in allowed:
                raise UpdateDependencyConflict(f"Selected LifeOS package collides with an existing package: {relative}")
        for name in ("bun.lock", "node_modules"):
            path = _checked(staged, relative) / name
            if path.is_symlink():
                raise UpdateDependencyConflict(f"Package target is a symbolic link: {relative / name}")
    for relative in prior_roots - selected_roots:
        target = _checked(staged, relative)
        if (target / "node_modules").is_dir():
            shutil.rmtree(target / "node_modules")
        (target / "bun.lock").unlink(missing_ok=True)
        package = target / "package.json"
        if package.is_file() and _digest(package) == _digest(prior_source / relative / "package.json"):
            package.unlink()
    for relative in sorted(selected_roots):
        target = _checked(staged, relative)
        selected = _checked(reference, relative)
        target.mkdir(parents=True, exist_ok=True)
        _copy_file(selected / "package.json", target / "package.json")
        for name in ("bun.lock", "node_modules"):
            destination = target / name
            if destination.is_dir():
                shutil.rmtree(destination)
            elif destination.exists():
                destination.unlink()
            incoming = selected / name
            if incoming.is_symlink():
                raise UpdateDependencyConflict(f"Reference package path is a symbolic link: {relative / name}")
            if incoming.is_dir():
                _copy_tree(incoming, destination)
            elif incoming.is_file():
                _copy_file(incoming, destination)
    return {"package_roots": sorted(path.as_posix() for path in selected_roots)}
