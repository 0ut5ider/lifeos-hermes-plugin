# ABOUTME: Saves files that a LifeOS system overlay will change.
# ABOUTME: Restores those files only when the installed update still matches the snapshot.

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path


SYSTEM_TREES = (
    "hooks", "skills", "agents", "LIFEOS/TOOLS", "LIFEOS/DOCUMENTATION",
    "LIFEOS/ALGORITHM", "LIFEOS/RULES", "LIFEOS/PULSE",
)
SYSTEM_FILES = (
    ("LIFEOS/LIFEOS_SYSTEM_PROMPT.md", "LIFEOS/LIFEOS_SYSTEM_PROMPT.md"),
    ("skills/LifeOS/install/CLAUDE.template.md", "CLAUDE.md"),
    ("LIFEOS/VERSION", "LIFEOS/VERSION"),
)
SKIP_DIRS = {"node_modules", ".git", "MEMORY", "USER", "out", ".next"}


class SnapshotError(Exception):
    pass


def digest(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            sha.update(chunk)
    return sha.hexdigest()


def source_files(payload: Path):
    for tree in SYSTEM_TREES:
        root = payload / tree
        if not root.is_dir() or root.is_symlink():
            continue
        for directory, dirs, files in os.walk(root, followlinks=False):
            dirs[:] = [name for name in dirs if name not in SKIP_DIRS and not (Path(directory) / name).is_symlink()]
            for name in files:
                source = Path(directory) / name
                if source.is_file() and not source.is_symlink():
                    yield source, source.relative_to(payload)
    for source_name, target_name in SYSTEM_FILES:
        source = payload / source_name
        if source.is_file() and not source.is_symlink():
            yield source, Path(target_name)


def checked_target(root: Path, relative: Path) -> Path:
    if relative.is_absolute() or ".." in relative.parts or not relative.parts:
        raise SnapshotError(f"unsafe target path: {relative}")
    target = root / relative
    for path in (target, *target.parents):
        if path == root.parent:
            break
        if path.is_symlink():
            raise SnapshotError(f"target has a symbolic link: {path}")
    return target


def take_snapshot(payload: Path, target_root: Path, snapshot: Path) -> dict:
    payload = payload.resolve(strict=True)
    target_root = target_root.resolve(strict=True)
    snapshot = snapshot.absolute()
    if not payload.is_dir() or not target_root.is_dir():
        raise SnapshotError("payload and target must be directories")
    if snapshot.exists() or snapshot.is_symlink():
        raise SnapshotError(f"snapshot already exists: {snapshot}")
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".{snapshot.name}.", dir=snapshot.parent))
    try:
        files = []
        seen = set()
        for source, relative in source_files(payload):
            name = relative.as_posix()
            if name in seen:
                raise SnapshotError(f"duplicate system target: {name}")
            seen.add(name)
            target = checked_target(target_root, relative)
            if relative == Path("LIFEOS/VERSION"):
                after = hashlib.sha256(source.read_text().strip().encode()).hexdigest()
            else:
                after = digest(source)
            before = digest(target) if target.is_file() else None
            if before == after:
                continue
            if target.exists() and not target.is_file():
                raise SnapshotError(f"system target is not a file: {target}")
            if before is not None:
                backup = stage / "files" / relative
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(target, backup)
            files.append({"path": name, "before": before, "after": after})
        files.sort(key=lambda item: item["path"])
        manifest = {"payload": str(payload), "target": str(target_root), "files": files}
        (stage / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        os.replace(stage, snapshot)
        return manifest
    finally:
        if stage.exists():
            shutil.rmtree(stage)


def inspect_snapshot(snapshot: Path, target_root: Path, *, allow_before: bool = False) -> tuple[dict, list[str]]:
    manifest = json.loads((snapshot / "manifest.json").read_text())
    target_root = target_root.resolve(strict=True)
    if str(target_root) != manifest.get("target"):
        raise SnapshotError("snapshot belongs to a different target root")
    names = set()
    divergent = []
    for item in manifest["files"]:
        relative = Path(item["path"])
        target = checked_target(target_root, relative)
        if item["path"] in names:
            raise SnapshotError(f"duplicate manifest path: {relative}")
        names.add(item["path"])
        if allow_before and item["before"] is None and not target.exists():
            continue
        if not target.is_file():
            raise SnapshotError(f"installed file is missing or not regular: {target}")
        current = digest(target)
        if current != item["after"] and not (allow_before and current == item["before"]):
            divergent.append(item["path"])
        if item["before"] is not None:
            backup = snapshot / "files" / relative
            if not backup.is_file() or digest(backup) != item["before"]:
                raise SnapshotError(f"snapshot backup is missing or damaged: {backup}")
    return manifest, divergent


def verify_overlay(snapshot: Path, target_root: Path) -> dict:
    manifest, divergent = inspect_snapshot(snapshot, target_root)
    if divergent:
        raise SnapshotError(f"installed file differs from staged update: {target_root / divergent[0]}")
    return manifest


def restore_snapshot(snapshot: Path, target_root: Path, *, preserve_divergent: bool = False) -> dict:
    manifest, divergent = inspect_snapshot(snapshot, target_root, allow_before=True)
    if divergent and not preserve_divergent:
        raise SnapshotError(f"installed file differs from staged update: {target_root / divergent[0]}")
    target_root = target_root.resolve(strict=True)
    if divergent:
        archive = snapshot / "divergent"
        if archive.exists() or archive.is_symlink():
            raise SnapshotError(f"divergent archive already exists: {archive}")
        stage = Path(tempfile.mkdtemp(prefix=".divergent.", dir=snapshot))
        try:
            for name in divergent:
                source = checked_target(target_root, Path(name))
                destination = stage / name
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination)
            os.replace(stage, archive)
        finally:
            if stage.exists():
                shutil.rmtree(stage)
    for item in manifest["files"]:
        relative = Path(item["path"])
        target = checked_target(target_root, relative)
        if item["before"] is None:
            target.unlink(missing_ok=True)
        else:
            backup = snapshot / "files" / relative
            with tempfile.NamedTemporaryFile(dir=target.parent, prefix=f".{target.name}.", delete=False) as staged:
                temporary = Path(staged.name)
            try:
                shutil.copy2(backup, temporary)
                os.replace(temporary, target)
            finally:
                temporary.unlink(missing_ok=True)
    return {**manifest, "preserved_divergent": divergent}


def main() -> int:
    parser = argparse.ArgumentParser(description="Snapshot and restore LifeOS system overlay files")
    sub = parser.add_subparsers(dest="action", required=True)
    stage = sub.add_parser("snapshot")
    stage.add_argument("payload", type=Path, help="LifeOS/install directory in the prepared source")
    stage.add_argument("target", type=Path, help="installed .claude directory")
    stage.add_argument("snapshot", type=Path, help="new snapshot directory")
    check = sub.add_parser("verify")
    check.add_argument("snapshot", type=Path)
    check.add_argument("target", type=Path)
    restore = sub.add_parser("restore")
    restore.add_argument("snapshot", type=Path)
    restore.add_argument("target", type=Path)
    restore.add_argument("--preserve-divergent", action="store_true")
    args = parser.parse_args()
    try:
        if args.action == "snapshot":
            manifest = take_snapshot(args.payload, args.target, args.snapshot)
        elif args.action == "verify":
            manifest = verify_overlay(args.snapshot, args.target)
        else:
            manifest = restore_snapshot(args.snapshot, args.target, preserve_divergent=args.preserve_divergent)
    except (OSError, ValueError, SnapshotError) as error:
        parser.exit(1, f"System overlay {args.action} failed: {error}\n")
    print(json.dumps({"action": args.action, "changed_files": len(manifest["files"]),
                      "preserved_divergent": manifest.get("preserved_divergent", [])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
