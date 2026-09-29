# ABOUTME: Stages and applies a coordinated Hermes, bridge, and LifeOS release.
# ABOUTME: Restores the prior code and LifeOS system files after an incomplete update.

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Callable

from scripts.system_overlay_snapshot import restore_snapshot, take_snapshot, verify_overlay


EXCLUDED = {".git", ".hermes", ".venv", "node_modules", "__pycache__", ".pytest_cache"}


class ReleaseError(Exception):
    pass


def _directory(path: Path) -> Path:
    if path.is_symlink() or not path.is_dir():
        raise ReleaseError(f"release path is not a regular directory: {path}")
    return path.resolve(strict=True)


def _files(root: Path):
    for directory, names, files in os.walk(root, followlinks=False):
        parent = Path(directory)
        names[:] = sorted(name for name in names if name not in EXCLUDED)
        for name in names:
            if (parent / name).is_symlink():
                raise ReleaseError(f"release tree contains a symbolic link: {parent / name}")
        for name in sorted(files):
            if name in EXCLUDED:
                continue
            path = parent / name
            if path.is_symlink() or not path.is_file():
                raise ReleaseError(f"release tree contains a non-regular file: {path}")
            yield path.relative_to(root), path


def _digest_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _digest_tree(root: Path) -> str:
    digest = hashlib.sha256()
    for relative, path in _files(root):
        digest.update(relative.as_posix().encode() + b"\0")
        digest.update(_digest_file(path).encode() + b"\n")
    return digest.hexdigest()


def _copy_tree(source: Path, target: Path) -> None:
    shutil.copytree(source, target, ignore=shutil.ignore_patterns(*EXCLUDED))


def _remove(path: Path) -> None:
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    else:
        path.unlink()


def _sync_tree(source: Path, target: Path) -> None:
    for path in target.iterdir():
        if path.name not in EXCLUDED and not (source / path.name).exists():
            _remove(path)
    for path in source.iterdir():
        if path.name in EXCLUDED:
            continue
        destination = target / path.name
        if path.is_dir():
            if destination.exists() and (destination.is_symlink() or not destination.is_dir()):
                _remove(destination)
            destination.mkdir(exist_ok=True)
            _sync_tree(path, destination)
        else:
            if destination.exists() and not destination.is_file():
                _remove(destination)
            with tempfile.NamedTemporaryFile(dir=target, prefix=f".{path.name}.", delete=False) as staged:
                temporary = Path(staged.name)
            try:
                shutil.copy2(path, temporary)
                os.replace(temporary, destination)
            finally:
                temporary.unlink(missing_ok=True)


def _write_manifest(snapshot: Path, manifest: dict) -> None:
    temporary = snapshot / ".manifest.tmp"
    temporary.write_text(json.dumps(manifest, indent=2) + "\n")
    os.replace(temporary, snapshot / "manifest.json")


def _load_manifest(snapshot: Path) -> dict:
    if snapshot.is_symlink() or not snapshot.is_dir():
        raise ReleaseError(f"release snapshot is missing: {snapshot}")
    return json.loads((snapshot / "manifest.json").read_text())


def stage_release(snapshot: Path, hermes_current: Path, hermes_next: Path,
                  plugin_current: Path, plugin_next: Path, lifeos_payload: Path,
                  lifeos_target: Path, hermes_config: Path) -> dict:
    paths = {name: _directory(path) for name, path in (
        ("hermes_current", hermes_current), ("hermes_next", hermes_next),
        ("plugin_current", plugin_current), ("plugin_next", plugin_next),
        ("lifeos_payload", lifeos_payload), ("lifeos_target", lifeos_target),
    )}
    config = hermes_config.resolve(strict=True)
    if hermes_config.is_symlink() or not config.is_file():
        raise ReleaseError(f"Hermes config is not a regular file: {hermes_config}")
    if any(config.is_relative_to(path) for path in paths.values()):
        raise ReleaseError("Hermes config must be outside the managed code trees")
    if len(set(paths.values())) != len(paths):
        raise ReleaseError("release source and target paths must be distinct")
    if any(left.is_relative_to(right) or right.is_relative_to(left)
           for index, left in enumerate(paths.values())
           for right in list(paths.values())[index + 1:]):
        raise ReleaseError("release source and target directories must not overlap")
    snapshot = snapshot.absolute()
    if snapshot.exists() or snapshot.is_symlink():
        raise ReleaseError(f"release snapshot already exists: {snapshot}")
    if any(snapshot.is_relative_to(path) for path in paths.values()):
        raise ReleaseError("release snapshot must be outside the managed trees")
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".{snapshot.name}.", dir=snapshot.parent))
    stage.chmod(0o700)
    try:
        hashes = {
            "hermes_before": _digest_tree(paths["hermes_current"]),
            "hermes_after": _digest_tree(paths["hermes_next"]),
            "plugin_before": _digest_tree(paths["plugin_current"]),
            "plugin_after": _digest_tree(paths["plugin_next"]),
            "config_before": _digest_file(config),
        }
        _copy_tree(paths["hermes_current"], stage / "hermes")
        _copy_tree(paths["plugin_current"], stage / "plugin")
        shutil.copy2(config, stage / "config.yaml")
        take_snapshot(paths["lifeos_payload"], paths["lifeos_target"], stage / "lifeos")
        manifest = {"state": "staged", "paths": {key: str(value) for key, value in paths.items()},
                    "config": str(config), "hashes": hashes}
        _write_manifest(stage, manifest)
        os.replace(stage, snapshot)
        return manifest
    finally:
        if stage.exists():
            shutil.rmtree(stage)


def restore_release(snapshot: Path) -> dict:
    manifest = _load_manifest(snapshot)
    paths = {key: Path(value) for key, value in manifest["paths"].items()}
    hashes = manifest["hashes"]
    if _digest_tree(snapshot / "hermes") != hashes["hermes_before"]:
        raise ReleaseError("Hermes backup differs from the staged snapshot")
    if _digest_tree(snapshot / "plugin") != hashes["plugin_before"]:
        raise ReleaseError("plugin backup differs from the staged snapshot")
    if _digest_file(snapshot / "config.yaml") != hashes["config_before"]:
        raise ReleaseError("Hermes config backup differs from the staged snapshot")
    _sync_tree(snapshot / "hermes", _directory(paths["hermes_current"]))
    _sync_tree(snapshot / "plugin", _directory(paths["plugin_current"]))
    shutil.copy2(snapshot / "config.yaml", Path(manifest["config"]))
    restore_snapshot(snapshot / "lifeos", paths["lifeos_target"], preserve_divergent=True)
    if _digest_tree(paths["hermes_current"]) != hashes["hermes_before"]:
        raise ReleaseError("Hermes code did not restore to the staged revision")
    if _digest_tree(paths["plugin_current"]) != hashes["plugin_before"]:
        raise ReleaseError("plugin code did not restore to the staged revision")
    manifest["state"] = "rolled_back"
    _write_manifest(snapshot, manifest)
    return manifest


def apply_release(snapshot: Path, *, overlay: Callable[[], None], verify: Callable[[], None],
                  stop: Callable[[], None] | None = None,
                  start: Callable[[], None] | None = None) -> dict:
    manifest = _load_manifest(snapshot)
    if manifest.get("state") != "staged":
        raise ReleaseError("release snapshot is not staged")
    paths = {key: _directory(Path(value)) for key, value in manifest["paths"].items()}
    hashes = manifest["hashes"]
    for label, tree in (("hermes_before", paths["hermes_current"]),
                        ("hermes_after", paths["hermes_next"]),
                        ("plugin_before", paths["plugin_current"]),
                        ("plugin_after", paths["plugin_next"])):
        if _digest_tree(tree) != hashes[label]:
            raise ReleaseError(f"release tree changed since staging: {label}")
    if _digest_file(Path(manifest["config"])) != hashes["config_before"]:
        raise ReleaseError("Hermes config changed since staging")
    if stop is not None:
        stop()
    started = False
    try:
        _sync_tree(paths["hermes_next"], paths["hermes_current"])
        _sync_tree(paths["plugin_next"], paths["plugin_current"])
        if _digest_tree(paths["hermes_current"]) != hashes["hermes_after"]:
            raise ReleaseError("Hermes code did not match the staged revision")
        if _digest_tree(paths["plugin_current"]) != hashes["plugin_after"]:
            raise ReleaseError("plugin code did not match the staged revision")
        overlay()
        verify_overlay(snapshot / "lifeos", paths["lifeos_target"])
        if start is not None:
            start()
            started = True
        verify()
    except BaseException:
        if started and stop is not None:
            stop()
        try:
            restore_release(snapshot)
            if start is not None:
                start()
        except BaseException as rollback_error:
            manifest["state"] = "rollback_failed"
            _write_manifest(snapshot, manifest)
            raise ReleaseError(f"release rollback failed: {rollback_error}") from rollback_error
        raise
    manifest["state"] = "applied"
    _write_manifest(snapshot, manifest)
    return manifest


def _run(*command: str) -> None:
    subprocess.run(command, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Stage and apply a tested LifeOS bridge release")
    sub = parser.add_subparsers(dest="action", required=True)
    stage = sub.add_parser("stage")
    stage.add_argument("snapshot", type=Path)
    stage.add_argument("hermes_current", type=Path)
    stage.add_argument("hermes_next", type=Path)
    stage.add_argument("plugin_current", type=Path)
    stage.add_argument("plugin_next", type=Path)
    stage.add_argument("lifeos_payload", type=Path)
    stage.add_argument("lifeos_target", type=Path)
    stage.add_argument("hermes_config", type=Path)
    for action in ("apply", "restore"):
        command = sub.add_parser(action)
        command.add_argument("snapshot", type=Path)
        service = command.add_mutually_exclusive_group(required=True)
        service.add_argument("--service", help="systemd user gateway service")
        service.add_argument("--no-gateway", action="store_true", help="use only when no gateway is running")
        if action == "apply":
            command.add_argument("--verify-script", type=Path, required=True,
                                 help="executable that verifies the running release; receives the snapshot path")
    args = parser.parse_args()
    try:
        if args.action == "stage":
            manifest = stage_release(args.snapshot, args.hermes_current, args.hermes_next,
                                     args.plugin_current, args.plugin_next, args.lifeos_payload,
                                     args.lifeos_target, args.hermes_config)
        else:
            stop = (lambda: _run("systemctl", "--user", "stop", args.service)) if args.service else None
            start = (lambda: _run("systemctl", "--user", "start", args.service)) if args.service else None
            if args.action == "restore":
                if stop is not None:
                    stop()
                manifest = restore_release(args.snapshot)
                if start is not None:
                    start()
            else:
                staged = _load_manifest(args.snapshot)
                paths = staged["paths"]
                source = Path(paths["lifeos_payload"])
                target = Path(paths["lifeos_target"])
                overlay_script = source.parent / "Tools/OverlaySystem.ts"
                if not overlay_script.is_file():
                    raise ReleaseError(f"LifeOS overlay tool is missing: {overlay_script}")
                if not args.verify_script.is_file() or not os.access(args.verify_script, os.X_OK):
                    raise ReleaseError(f"release verifier is not executable: {args.verify_script}")
                manifest = apply_release(
                    args.snapshot,
                    overlay=lambda: _run("bun", str(overlay_script), "--config-root", str(target),
                                         "--skill-root", str(source.parent), "--apply"),
                    verify=lambda: _run(str(args.verify_script), str(args.snapshot)),
                    stop=stop, start=start,
                )
    except (OSError, ValueError, ReleaseError, subprocess.CalledProcessError) as error:
        print(f"Release {args.action} failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps({"action": args.action, "state": manifest["state"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
