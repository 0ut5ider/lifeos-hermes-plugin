# ABOUTME: Applies a LifeOS update through a staged directory and recoverable swap.
# ABOUTME: Restores LifeOS, Hermes mount files, and the baseline if verification fails.

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

from .update_dependencies import sync_dependencies
from .update_hooks import replace_owned_hooks
from .update_plan import apply_system_plan, plan_system_files


MOUNT_FILES = ("config.yaml", "SOUL.md", ".env")
MOUNT_DIRS = ("plugins/lifeos",)


class UpdateTransactionError(RuntimeError):
    pass


def _write_json(path: Path, data: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        os.fchmod(stream.fileno(), 0o600)
        json.dump(data, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def _copy_tree(source: Path, target: Path) -> None:
    result = subprocess.run(["cp", "-a", "--reflink=auto", str(source), str(target)],
                            capture_output=True, text=True, timeout=300)
    if result.returncode:
        raise UpdateTransactionError(f"LifeOS copy failed with code {result.returncode}")


def _snapshot_mount(hermes_home: Path, snapshot: Path, baseline: Path) -> None:
    saved = snapshot / "mount"
    saved.mkdir()
    present = []
    for name in (*MOUNT_FILES, *MOUNT_DIRS):
        source = hermes_home / name
        if source.is_symlink():
            raise UpdateTransactionError(f"Hermes mount is a symbolic link: {name}")
        if source.is_file():
            destination = saved / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            present.append(name)
        elif source.is_dir():
            destination = saved / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            _copy_tree(source, destination)
            present.append(name)
        elif source.exists():
            raise UpdateTransactionError(f"Hermes mount has unsupported type: {name}")
    shutil.copy2(baseline, snapshot / "baseline.json")
    _write_json(snapshot / "mount-manifest.json", {"present": present})


def _restore_mount(hermes_home: Path, snapshot: Path, baseline: Path) -> None:
    present = set(json.loads((snapshot / "mount-manifest.json").read_text())["present"])
    for name in (*MOUNT_FILES, *MOUNT_DIRS):
        destination = hermes_home / name
        if destination.is_symlink():
            raise UpdateTransactionError(f"Hermes mount became a symbolic link: {name}")
        if destination.is_dir():
            shutil.rmtree(destination)
        elif destination.exists():
            destination.unlink()
        if name in present:
            source = snapshot / "mount" / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            if source.is_dir():
                _copy_tree(source, destination)
            else:
                shutil.copy2(source, destination)
    temporary = baseline.with_suffix(baseline.suffix + ".restore")
    shutil.copy2(snapshot / "baseline.json", temporary)
    os.replace(temporary, baseline)


def _source_hooks(source: Path) -> dict:
    manifest = json.loads((source / "hooks/hooks.json").read_text(encoding="utf-8"))
    return manifest["hooks"]


def _memory_digest(root: Path) -> dict[str, str]:
    hashes = {}
    for name in ("LIFEOS/MEMORY", "LIFEOS/USER", "USER.md", "MEMORY.md"):
        path = root / name
        if path.is_file():
            hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
        elif path.is_dir():
            for file in path.rglob("*"):
                if file.is_symlink():
                    raise UpdateTransactionError(f"User data contains a symbolic link: {file}")
                if file.is_file():
                    relative = file.relative_to(root).as_posix()
                    hashes[relative] = hashlib.sha256(file.read_bytes()).hexdigest()
    return hashes


def apply_update(installed: Path, hermes_home: Path, prior_source: Path,
                 selected_source: Path, reference: Path, baseline_path: Path,
                 snapshot: Path, *, stop, start, mount, renew, verify,
                 verify_restored=None) -> dict:
    paths = (installed, hermes_home, prior_source, selected_source, reference)
    if any(path.is_symlink() or not path.is_dir() for path in paths):
        raise UpdateTransactionError("Update paths must be regular directories")
    if baseline_path.is_symlink() or not baseline_path.is_file() or snapshot.exists():
        raise UpdateTransactionError("Baseline is missing or update snapshot already exists")
    if installed.stat().st_dev != snapshot.parent.stat().st_dev:
        raise UpdateTransactionError("Update snapshot must be on the LifeOS filesystem")
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    plan = plan_system_files(installed, baseline, selected_source, reference)
    current_settings = json.loads((installed / "settings.json").read_text(encoding="utf-8"))
    selected_settings, hook_counts = replace_owned_hooks(
        current_settings, _source_hooks(prior_source), _source_hooks(selected_source))
    snapshot.mkdir(mode=0o700, parents=False)
    manifest = {"state": "prepared", "installed": str(installed.resolve()),
                "hermes_home": str(hermes_home.resolve()), "baseline": str(baseline_path.resolve()),
                "plan_counts": {key: len(plan[key]) for key in ("add", "replace", "remove")},
                "hook_counts": hook_counts}
    manifest_path = snapshot / "manifest.json"
    _write_json(manifest_path, manifest)
    stopped = False
    swapped = False
    try:
        _snapshot_mount(hermes_home, snapshot, baseline_path)
        stopped = True
        stop()
        manifest["state"] = "stopped"
        _write_json(manifest_path, manifest)
        plan = plan_system_files(installed, baseline, selected_source, reference)
        _copy_tree(installed, snapshot / "staged")
        staged = snapshot / "staged"
        apply_system_plan(staged, selected_source, plan)
        dependency_report = sync_dependencies(staged, prior_source, selected_source, reference)
        _write_json(staged / "settings.json", selected_settings)
        os.replace(installed, snapshot / "live-prior")
        os.replace(staged, installed)
        swapped = True
        manifest["state"] = "swapped"
        _write_json(manifest_path, manifest)
        mount()
        renew(installed, selected_source)
        start()
        verify()
        manifest["state"] = "applied"
        manifest["package_roots"] = dependency_report["package_roots"]
        manifest["user_data"] = _memory_digest(installed)
        _write_json(manifest_path, manifest)
        return manifest
    except Exception as error:
        if not stopped:
            manifest["state"] = "failed_before_stop"
            _write_json(manifest_path, manifest)
            raise UpdateTransactionError(str(error)) from error
        try:
            stop()
            if swapped:
                os.replace(installed, snapshot / "failed-selected")
            if (snapshot / "live-prior").exists():
                os.replace(snapshot / "live-prior", installed)
            _restore_mount(hermes_home, snapshot, baseline_path)
            start()
            if verify_restored is not None:
                verify_restored()
            manifest["state"] = "rolled_back"
            _write_json(manifest_path, manifest)
        except Exception as rollback_error:
            manifest["state"] = "rollback_failed"
            manifest["rollback_error"] = str(rollback_error)
            _write_json(manifest_path, manifest)
            raise UpdateTransactionError(
                f"Update failed: {error}; rollback failed: {rollback_error}") from error
        raise UpdateTransactionError(str(error)) from error


def restore_update(snapshot: Path, *, stop, start, verify) -> dict:
    manifest_path = snapshot / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest["state"] != "applied":
        raise UpdateTransactionError("Only an applied update can be restored")
    installed = Path(manifest["installed"])
    if _memory_digest(installed) != manifest["user_data"]:
        raise UpdateTransactionError("User data changed after update; automatic restore refused")
    manifest["state"] = "restoring"
    _write_json(manifest_path, manifest)
    stop()
    os.replace(installed, snapshot / "restored-selected")
    os.replace(snapshot / "live-prior", installed)
    _restore_mount(Path(manifest["hermes_home"]), snapshot, Path(manifest["baseline"]))
    start()
    verify()
    manifest["state"] = "rolled_back"
    _write_json(manifest_path, manifest)
    return manifest


def recover_update(snapshot: Path, *, stop, start, verify) -> dict:
    manifest_path = snapshot / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest["state"] not in {"stopped", "swapped", "restoring", "rollback_failed"}:
        raise UpdateTransactionError("Update snapshot does not need interrupted recovery")
    installed = Path(manifest["installed"])
    prior = snapshot / "live-prior"
    stop()
    if prior.exists():
        if installed.exists():
            archive = snapshot / "interrupted-selected"
            if archive.exists():
                raise UpdateTransactionError("Interrupted selected archive already exists")
            os.replace(installed, archive)
        os.replace(prior, installed)
    elif not installed.is_dir():
        raise UpdateTransactionError("Neither installed LifeOS nor prior snapshot exists")
    _restore_mount(Path(manifest["hermes_home"]), snapshot, Path(manifest["baseline"]))
    start()
    verify()
    manifest["state"] = "rolled_back"
    _write_json(manifest_path, manifest)
    return manifest
