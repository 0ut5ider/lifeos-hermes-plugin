# ABOUTME: Exposes the bridge's declared settings to its authenticated dashboard tab.
# ABOUTME: Delegates validation and storage to Hermes's plugin settings service.

import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from hermes_cli.plugins_settings import plugin_settings_fields, save_plugin_settings


PLUGIN_ID = "lifeos-hook-bridge"
PLUGIN_DIR = Path(__file__).resolve().parents[1]
version_spec = importlib.util.spec_from_file_location("lifeos_version_drift", PLUGIN_DIR / "version_drift.py")
if version_spec is None or version_spec.loader is None:
    raise ImportError("LifeOS VersionDrift module is unavailable")
version_module = importlib.util.module_from_spec(version_spec)
version_spec.loader.exec_module(version_module)
install_spec = importlib.util.spec_from_file_location("lifeos_install_source", PLUGIN_DIR / "install_source.py")
if install_spec is None or install_spec.loader is None:
    raise ImportError("LifeOS source installer is unavailable")
install_module = importlib.util.module_from_spec(install_spec)
install_spec.loader.exec_module(install_module)
prepare_latest_lifeos = install_module.prepare_latest_lifeos
validate_prepared_lifeos = install_module.validate_prepared_lifeos
install_prepared_lifeos = install_module.install_prepared_lifeos
finalize_prepared_lifeos = install_module.finalize_prepared_lifeos
prepare_supported_hermes = install_module.prepare_supported_hermes
validate_supported_hermes = install_module.validate_supported_hermes
stage_supported_hermes_patch = install_module.stage_supported_hermes_patch
request_hermes_restore = install_module.request_hermes_restore
cancel_hermes_restore = install_module.cancel_hermes_restore
IncompatibleLifeOS = install_module.IncompatibleLifeOS
baseline_fingerprint = version_module.baseline_fingerprint
adapter_error_path = version_module.adapter_error_path
changed_paths = version_module.changed_paths
create_baseline = version_module.create_baseline
default_baseline_path = version_module.default_baseline_path
load_baseline = version_module.load_baseline
save_baseline = version_module.save_baseline
INSTALLED_ROOT = Path.home() / ".claude"
HERMES_HOME = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
BASELINE_PATH = default_baseline_path()
INSTALL_CANDIDATE = Path.home() / ".local/share/lifeos-bridge/lifeos-candidate"
HERMES_CANDIDATE = Path.home() / ".local/share/lifeos-bridge/hermes-candidate"
HOST_PATCH_ROOT = Path.home() / ".local/state/lifeos-hook-bridge/host-patches"
HOST_SOURCE = None
PATCHED_HOOKS = {"pre_command_approval", "augment_tool_result", "pre_turn_stop", "on_turn_result"}
router = APIRouter()


def _host_source():
    if HOST_SOURCE is not None:
        return HOST_SOURCE
    from hermes_cli import plugins
    module_path = getattr(plugins, "__file__", None)
    if not module_path:
        raise IncompatibleLifeOS("The running Hermes source path is unavailable")
    return Path(module_path).resolve().parents[1]


@router.get("/installation")
def get_installation():
    from hermes_cli.plugins import VALID_HOOKS

    version_file = INSTALLED_ROOT / "LIFEOS/VERSION"
    if not INSTALLED_ROOT.exists() and not INSTALLED_ROOT.is_symlink():
        lifeos = "missing"
    elif version_file.is_file() and (INSTALLED_ROOT / "settings.json").is_file():
        lifeos = "installed"
    else:
        lifeos = "partial"
    if PATCHED_HOOKS <= VALID_HOOKS:
        hermes = "patched_hooks_present"
    elif PATCHED_HOOKS.isdisjoint(VALID_HOOKS):
        hermes = "stock"
    else:
        hermes = "partial"
    candidate = None
    candidate_error = None
    if INSTALL_CANDIDATE.exists() or INSTALL_CANDIDATE.is_symlink():
        try:
            candidate = validate_prepared_lifeos(INSTALL_CANDIDATE)
        except (IncompatibleLifeOS, OSError) as error:
            candidate_error = str(error)
    host_candidate = None
    host_candidate_error = None
    if HERMES_CANDIDATE.exists() or HERMES_CANDIDATE.is_symlink():
        try:
            host_candidate = validate_supported_hermes(HERMES_CANDIDATE)
        except (IncompatibleLifeOS, OSError) as error:
            host_candidate_error = str(error)
    return {
        "lifeos": lifeos,
        "version": version_file.read_text(encoding="utf-8").strip() if version_file.is_file() else None,
        "hermes": hermes,
        "missing_hooks": sorted(PATCHED_HOOKS - VALID_HOOKS),
        "candidate_ready": candidate is not None,
        "candidate_commit": candidate["upstream_commit"] if candidate else None,
        "candidate_patch_count": len(candidate["patches"]) if candidate else None,
        "candidate_error": candidate_error,
        "hermes_candidate_ready": host_candidate is not None,
        "hermes_candidate_commit": host_candidate["base_commit"] if host_candidate else None,
        "hermes_candidate_patch_count": len(host_candidate["patches"]) if host_candidate else None,
        "hermes_candidate_error": host_candidate_error,
        "setup_baseline_exists": BASELINE_PATH.is_file(),
    }


@router.post("/installation/prepare")
def prepare_installation():
    if INSTALLED_ROOT.exists() or INSTALLED_ROOT.is_symlink():
        raise HTTPException(status_code=409, detail="A .claude directory exists. Use the update path after reviewing it.")
    if INSTALL_CANDIDATE.exists() or INSTALL_CANDIDATE.is_symlink():
        raise HTTPException(status_code=409, detail="A LifeOS candidate already exists. Review it before preparing another.")
    try:
        return prepare_latest_lifeos(INSTALL_CANDIDATE)
    except IncompatibleLifeOS as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.post("/installation/apply")
def apply_installation():
    if INSTALLED_ROOT.exists() or INSTALLED_ROOT.is_symlink():
        raise HTTPException(status_code=409, detail="A .claude directory exists. The fresh installer will not overwrite it.")
    try:
        validate_prepared_lifeos(INSTALL_CANDIDATE)
        failed = INSTALL_CANDIDATE.parent / f"failed-install-{uuid4().hex}"
        return install_prepared_lifeos(INSTALL_CANDIDATE, INSTALLED_ROOT, failed)
    except (IncompatibleLifeOS, OSError) as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.post("/installation/finalize")
def finalize_installation():
    if not (INSTALLED_ROOT / "LIFEOS/VERSION").is_file() or not (INSTALLED_ROOT / "settings.json").is_file():
        raise HTTPException(status_code=409, detail="Install LifeOS before finishing setup")
    if BASELINE_PATH.exists() or BASELINE_PATH.is_symlink():
        raise HTTPException(status_code=409, detail="A VersionDrift baseline already exists")
    try:
        return finalize_prepared_lifeos(INSTALL_CANDIDATE, INSTALLED_ROOT, HERMES_HOME,
                                        BASELINE_PATH, create_baseline, save_baseline)
    except (IncompatibleLifeOS, OSError, ValueError, subprocess.TimeoutExpired) as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.post("/installation/prepare-hermes")
def prepare_hermes_installation():
    if not (INSTALLED_ROOT / "LIFEOS/VERSION").is_file() or not (INSTALLED_ROOT / "settings.json").is_file():
        raise HTTPException(status_code=409, detail="Install LifeOS before preparing the Hermes extension")
    if HERMES_CANDIDATE.exists() or HERMES_CANDIDATE.is_symlink():
        raise HTTPException(status_code=409, detail="A Hermes candidate already exists. Review it before preparing another.")
    try:
        return prepare_supported_hermes(_host_source(), HERMES_CANDIDATE)
    except (IncompatibleLifeOS, OSError) as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


def _latest_host_patch():
    if not HOST_PATCH_ROOT.is_dir() or HOST_PATCH_ROOT.is_symlink():
        return None
    snapshots = [path for path in HOST_PATCH_ROOT.iterdir()
                 if path.is_dir() and not path.is_symlink() and (path / "manifest.json").is_file()]
    return max(snapshots, key=lambda path: path.stat().st_mtime_ns) if snapshots else None


@router.get("/installation/host-patch")
def get_host_patch_status():
    snapshot = _latest_host_patch()
    if snapshot is None:
        return {"state": "none"}
    try:
        manifest = json.loads((snapshot / "manifest.json").read_text())
    except (OSError, ValueError):
        return {"state": "error", "snapshot": str(snapshot)}
    return {"state": manifest.get("state", "error"), "snapshot": str(snapshot),
            "error": manifest.get("error")}


def _launch_host_patch(snapshot: Path, action: str):
    service = subprocess.run(["systemctl", "--user", "is-active", "hermes-gateway.service"],
                             text=True, capture_output=True, timeout=15)
    if service.returncode or service.stdout.strip() != "active":
        raise IncompatibleLifeOS("A running Hermes gateway user service is required")
    command = ["systemd-run", "--user", "--collect",
               f"--unit=lifeos-bridge-{action}-{uuid4().hex}",
               f"--setenv=HERMES_HOME={HERMES_HOME}", sys.executable,
               str(PLUGIN_DIR / "install_source.py"), action, str(snapshot)]
    launched = subprocess.run(command, text=True, capture_output=True, timeout=30)
    if launched.returncode:
        raise IncompatibleLifeOS(f"Could not start the Hermes patch worker: {launched.returncode}")


@router.post("/installation/apply-hermes")
def apply_hermes_installation():
    if not (INSTALLED_ROOT / "LIFEOS/VERSION").is_file():
        raise HTTPException(status_code=409, detail="Install LifeOS before patching Hermes")
    previous = get_host_patch_status()
    if previous["state"] in {"staged", "applying", "applied", "restore_failed", "rollback_failed"}:
        raise HTTPException(status_code=409, detail="A Hermes patch job already owns this installation")
    if HOST_PATCH_ROOT.is_symlink():
        raise HTTPException(status_code=409, detail="Hermes patch state directory cannot be a symbolic link")
    HOST_PATCH_ROOT.mkdir(parents=True, exist_ok=True, mode=0o700)
    snapshot = HOST_PATCH_ROOT / f"patch-{uuid4().hex}"
    try:
        stage_supported_hermes_patch(snapshot, _host_source(), HERMES_CANDIDATE,
                                      HERMES_HOME / "config.yaml")
        _launch_host_patch(snapshot, "apply")
    except (IncompatibleLifeOS, OSError, ValueError, subprocess.CalledProcessError,
            subprocess.TimeoutExpired) as error:
        if snapshot.exists():
            shutil.rmtree(snapshot)
        raise HTTPException(status_code=409, detail=str(error)) from error
    return {"state": "staged", "snapshot": str(snapshot)}


@router.post("/installation/restore-hermes")
def restore_hermes_installation():
    previous = get_host_patch_status()
    if previous["state"] != "applied":
        raise HTTPException(status_code=409, detail="There is no applied Hermes patch to restore")
    snapshot = Path(previous["snapshot"])
    requested = False
    try:
        request_hermes_restore(snapshot)
        requested = True
        _launch_host_patch(snapshot, "restore")
    except (IncompatibleLifeOS, OSError, subprocess.TimeoutExpired) as error:
        if requested:
            cancel_hermes_restore(snapshot, str(error))
        raise HTTPException(status_code=409, detail=str(error)) from error
    return {"state": "restoring", "snapshot": str(snapshot)}


@router.get("/settings")
def get_settings():
    return {"fields": plugin_settings_fields(PLUGIN_ID, PLUGIN_DIR)}


@router.put("/settings")
def put_settings(values: dict):
    try:
        saved = save_plugin_settings(PLUGIN_ID, PLUGIN_DIR, values)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    return {"saved": saved, "restart_required": bool(saved)}


def _candidate(request: dict):
    source = request.get("source")
    if not isinstance(source, str) or not Path(source).is_absolute():
        raise HTTPException(status_code=400, detail="Enter an absolute LifeOS source install path")
    try:
        return create_baseline(Path(source), INSTALLED_ROOT)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.get("/version-drift")
def get_version_drift():
    diagnostic = adapter_error_path(BASELINE_PATH)
    if diagnostic.exists():
        try:
            import json
            message = json.loads(diagnostic.read_text(encoding="utf-8"))["message"]
        except (OSError, ValueError, KeyError, TypeError):
            message = "VersionDrift adapter failed; inspect the private diagnostic file"
        return {"state": "error", "message": message, "baseline_exists": BASELINE_PATH.exists()}
    try:
        baseline = load_baseline(BASELINE_PATH, INSTALLED_ROOT)
        changed = changed_paths(baseline, INSTALLED_ROOT)
        installed_version = (INSTALLED_ROOT / "LIFEOS/VERSION").read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return {"state": "missing", "baseline_exists": False}
    except (OSError, ValueError, KeyError, TypeError) as error:
        return {"state": "error", "message": str(error), "baseline_exists": BASELINE_PATH.exists()}
    return {
        "state": "ready", "baseline_exists": True, "version": baseline["version"],
        "source_commit": baseline["source_commit"], "created_at": baseline["created_at"],
        "file_count": len(baseline["files"]), "changed_count": len(changed),
        "installed_version": installed_version, "version_mismatch": installed_version != baseline["version"],
    }


@router.post("/version-drift/preview")
def preview_version_drift(request: dict):
    baseline = _candidate(request)
    return {
        "version": baseline["version"], "source_commit": baseline["source_commit"],
        "file_count": len(baseline["files"]), "files": list(baseline["files"]),
        "fingerprint": baseline_fingerprint(baseline),
    }


@router.post("/version-drift")
def apply_version_drift(request: dict):
    baseline = _candidate(request)
    if request.get("fingerprint") != baseline_fingerprint(baseline):
        raise HTTPException(status_code=409, detail="LifeOS files changed since the preview. Preview again.")
    try:
        save_baseline(baseline, BASELINE_PATH, renew=request.get("renew") is True)
    except FileExistsError as error:
        raise HTTPException(status_code=409, detail="A baseline exists. Review it before renewal.") from error
    except (OSError, ValueError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    adapter_error_path(BASELINE_PATH).unlink(missing_ok=True)
    return get_version_drift()
