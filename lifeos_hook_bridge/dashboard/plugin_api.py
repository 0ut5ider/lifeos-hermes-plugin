# ABOUTME: Exposes the bridge's declared settings to its authenticated dashboard tab.
# ABOUTME: Delegates validation and storage to Hermes's plugin settings service.

import importlib.util
from pathlib import Path
import subprocess
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
IncompatibleLifeOS = install_module.IncompatibleLifeOS
baseline_fingerprint = version_module.baseline_fingerprint
adapter_error_path = version_module.adapter_error_path
changed_paths = version_module.changed_paths
create_baseline = version_module.create_baseline
default_baseline_path = version_module.default_baseline_path
load_baseline = version_module.load_baseline
save_baseline = version_module.save_baseline
INSTALLED_ROOT = Path.home() / ".claude"
BASELINE_PATH = default_baseline_path()
INSTALL_CANDIDATE = Path.home() / ".local/share/lifeos-bridge/lifeos-candidate"
PATCHED_HOOKS = {"pre_command_approval", "augment_tool_result", "pre_turn_stop", "on_turn_result"}
router = APIRouter()


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
    return {
        "lifeos": lifeos,
        "version": version_file.read_text(encoding="utf-8").strip() if version_file.is_file() else None,
        "hermes": hermes,
        "missing_hooks": sorted(PATCHED_HOOKS - VALID_HOOKS),
        "candidate_ready": candidate is not None,
        "candidate_commit": candidate["upstream_commit"] if candidate else None,
        "candidate_patch_count": len(candidate["patches"]) if candidate else None,
        "candidate_error": candidate_error,
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
