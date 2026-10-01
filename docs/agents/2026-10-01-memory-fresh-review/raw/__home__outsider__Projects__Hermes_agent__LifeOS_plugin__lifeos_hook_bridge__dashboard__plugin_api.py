# ABOUTME: Exposes the bridge's declared settings to its authenticated dashboard tab.
# ABOUTME: Delegates validation and storage to Hermes's plugin settings service.

import importlib.util
import importlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import types
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
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
LIFEOS_UPDATE_ROOT = Path.home() / ".local/state/lifeos-hook-bridge/updates"
HOST_SOURCE = None
PATCHED_HOOKS = {"pre_prompt_admission", "pre_command_approval", "augment_tool_result", "pre_turn_stop", "on_turn_result"}
router = APIRouter()


class MemoryResponseHeaders:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        path = scope.get('path', '')
        root = scope.get('root_path', '')
        if root and path.startswith(root + '/'):
            path = path[len(root):]
        if scope['type'] != 'http' or not path.startswith('/api/plugins/lifeos-hook-bridge/memory/pulse/'):
            return await self.app(scope, receive, send)

        async def send_private(message):
            if message['type'] == 'http.response.start':
                headers = [(key, value) for key, value in message.get('headers', [])
                           if key.lower() not in (b'cache-control', b'etag', b'last-modified')]
                message = {**message, 'headers': [*headers, (b'cache-control', b'no-store')]}
            await send(message)

        await self.app(scope, receive, send_private)


def install_memory_cache_headers(app: FastAPI) -> None:
    if not getattr(app.state, 'lifeos_memory_cache_headers', False):
        app.add_middleware(MemoryResponseHeaders)
        app.state.lifeos_memory_cache_headers = True


# Hermes imports plugin routers while assembling its app, before its middleware stack starts.
_dashboard_host = sys.modules.get('hermes_cli.web_server')
if _dashboard_host is not None and isinstance(getattr(_dashboard_host, 'app', None), FastAPI):
    install_memory_cache_headers(_dashboard_host.app)


def _memory_preferences():
    name = 'lifeos_memory_settings'
    if name not in sys.modules:
        package = types.ModuleType(name)
        package.__path__ = [str(PLUGIN_DIR)]
        sys.modules[name] = package
    module = importlib.import_module(name + '.memory_preferences')
    return module.MemoryPreferences(HERMES_HOME / 'lifeos-memory.json', INSTALLED_ROOT,
                                    Path.home() / '.ssh/authorized_keys', Path(sys.executable),
                                    PLUGIN_DIR / 'memory_mcp.py')


def _memory_action(action):
    try:
        return action(_memory_preferences())
    except (ValueError, OSError, RuntimeError) as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.get('/memory')
def get_memory():
    return _memory_action(lambda preferences:preferences.status())


@router.get('/memory/pulse/{view}')
def get_memory_pulse(view: Literal['snapshot', 'state', 'health', 'runs'], request: Request):
    headers = {'Cache-Control': 'no-store'}
    try:
        from hermes_cli.dashboard_auth.base import Session
    except ImportError:
        return JSONResponse({'error': 'Memory request authentication is unavailable'}, status_code=503, headers=headers)
    session = getattr(request.state, 'session', None)
    if not isinstance(session, Session):
        return JSONResponse({'error': 'An authenticated dashboard session is required'}, status_code=401, headers=headers)
    if request.query_params:
        return JSONResponse({'error': 'Memory views use the installed owner configuration'}, status_code=400, headers=headers)
    try:
        result = _memory_preferences().pulse_snapshot(view, account=f'dashboard:{session.provider}:{session.user_id}')
    except PermissionError:
        return JSONResponse({'error': 'This dashboard account has no installation owner binding'},
                            status_code=403, headers=headers)
    except (ValueError, OSError, RuntimeError, sqlite3.Error, subprocess.TimeoutExpired):
        return JSONResponse({'error': 'Memory is unavailable under the current installation policy'},
                            status_code=503, headers=headers)
    return JSONResponse(result, headers=headers)


@router.post('/memory/review')
def review_memory(request: dict):
    if set(request) != {'tool','arguments'} or not isinstance(request['tool'], str) or not isinstance(request['arguments'], dict):
        raise HTTPException(status_code=400, detail='Choose a memory action and its arguments')
    return _memory_action(lambda preferences:preferences.review(request['tool'], request['arguments']))


@router.post('/memory/adoption/preview')
def preview_memory_adoption(request: dict):
    if request:
        raise HTTPException(status_code=400, detail='Source preview uses the installed LifeOS configuration')
    return _memory_action(lambda preferences:preferences.preview_adoption())


@router.post('/memory/adoption')
def adopt_memory_sources(request: dict):
    if set(request) != {'signature','projects','request_id'}:
        raise HTTPException(status_code=400, detail='Provide the reviewed source preview, project assignments, and request identifier')
    return _memory_action(lambda preferences:preferences.adopt(request))


@router.post('/memory/sharing')
def set_memory_sharing(request: dict):
    if set(request) != {'enabled'} or type(request['enabled']) is not bool:
        raise HTTPException(status_code=400, detail='Choose whether memory sharing is enabled')
    return _memory_action(lambda preferences:preferences.sharing(request['enabled']))


@router.post('/memory/connections')
def enroll_memory_connection(request: dict):
    return _memory_action(lambda preferences:preferences.enroll(request))


@router.delete('/memory/connections/{client}')
def revoke_memory_connection(client: str):
    return _memory_action(lambda preferences:preferences.revoke(client))


def _host_source():
    if HOST_SOURCE is not None:
        return HOST_SOURCE
    from hermes_cli import plugins
    module_path = getattr(plugins, "__file__", None)
    if not module_path:
        raise IncompatibleLifeOS("The running Hermes source path is unavailable")
    return Path(module_path).resolve().parents[1]


def _candidate_path():
    marker = INSTALL_CANDIDATE.with_name(INSTALL_CANDIDATE.name + ".selected.json")
    if not marker.exists():
        return INSTALL_CANDIDATE
    if marker.is_symlink() or not marker.is_file():
        raise IncompatibleLifeOS("LifeOS candidate selection file is invalid")
    selected = json.loads(marker.read_text(encoding="utf-8"))["name"]
    if (not isinstance(selected, str) or not selected.startswith(INSTALL_CANDIDATE.name + "-")
            or Path(selected).name != selected):
        raise IncompatibleLifeOS("LifeOS candidate selection is invalid")
    return INSTALL_CANDIDATE.with_name(selected)


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
    selected_candidate = _candidate_path()
    if selected_candidate.exists() or selected_candidate.is_symlink():
        try:
            candidate = validate_prepared_lifeos(selected_candidate)
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
        "candidate_newer": bool(candidate and BASELINE_PATH.is_file() and
                                candidate["upstream_commit"] != json.loads(BASELINE_PATH.read_text()).get("source_commit")),
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
        if (INSTALLED_ROOT.is_symlink() or not (INSTALLED_ROOT / "LIFEOS/VERSION").is_file()
                or not BASELINE_PATH.is_file()):
            raise HTTPException(status_code=409, detail="An existing LifeOS installation needs a VersionDrift baseline before update preparation")
    selected_candidate = _candidate_path()
    target = selected_candidate
    if selected_candidate.exists() or selected_candidate.is_symlink():
        baseline_source = None
        if BASELINE_PATH.is_file():
            try:
                baseline_source = json.loads(BASELINE_PATH.read_text(encoding="utf-8")).get("source_root")
            except (OSError, ValueError):
                pass
        current_candidate = baseline_source == str((selected_candidate / "LifeOS/install").resolve())
        if (not INSTALLED_ROOT.is_dir() or not BASELINE_PATH.is_file()
                or (get_lifeos_update_status()["state"] != "applied" and not current_candidate)):
            raise HTTPException(status_code=409, detail="A LifeOS candidate already exists. Review it before preparing another.")
        target = INSTALL_CANDIDATE.with_name(f"{INSTALL_CANDIDATE.name}-{uuid4().hex}")
    try:
        result = prepare_latest_lifeos(target)
        if target != selected_candidate:
            marker = INSTALL_CANDIDATE.with_name(INSTALL_CANDIDATE.name + ".selected.json")
            temporary = marker.with_suffix(".tmp")
            with temporary.open("w", encoding="utf-8") as stream:
                os.fchmod(stream.fileno(), 0o600)
                json.dump({"name": target.name}, stream)
                stream.write("\n")
            os.replace(temporary, marker)
        return result
    except IncompatibleLifeOS as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.post("/installation/apply")
def apply_installation():
    if INSTALLED_ROOT.exists() or INSTALLED_ROOT.is_symlink():
        raise HTTPException(status_code=409, detail="A .claude directory exists. The fresh installer will not overwrite it.")
    try:
        candidate = _candidate_path()
        validate_prepared_lifeos(candidate)
        failed = candidate.parent / f"failed-install-{uuid4().hex}"
        return install_prepared_lifeos(candidate, INSTALLED_ROOT, failed)
    except (IncompatibleLifeOS, OSError) as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.post("/installation/finalize")
def finalize_installation():
    if not (INSTALLED_ROOT / "LIFEOS/VERSION").is_file() or not (INSTALLED_ROOT / "settings.json").is_file():
        raise HTTPException(status_code=409, detail="Install LifeOS before finishing setup")
    if BASELINE_PATH.exists() or BASELINE_PATH.is_symlink():
        raise HTTPException(status_code=409, detail="A VersionDrift baseline already exists")
    try:
        return finalize_prepared_lifeos(_candidate_path(), INSTALLED_ROOT, HERMES_HOME,
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


def _latest_lifeos_update():
    if not LIFEOS_UPDATE_ROOT.is_dir() or LIFEOS_UPDATE_ROOT.is_symlink():
        return None
    jobs = [path for path in LIFEOS_UPDATE_ROOT.iterdir()
            if path.is_dir() and not path.is_symlink() and (path / "request.json").is_file()]
    return max(jobs, key=lambda path: path.stat().st_mtime_ns) if jobs else None


@router.get("/installation/update")
def get_lifeos_update_status():
    job = _latest_lifeos_update()
    if job is None:
        return {"state": "none"}
    try:
        status = json.loads((job / "status.json").read_text(encoding="utf-8"))
        snapshot = job / "snapshot/manifest.json"
        if snapshot.is_file():
            transaction = json.loads(snapshot.read_text(encoding="utf-8"))
            status["transaction_state"] = transaction.get("state")
            if transaction.get("state") in {"applied", "rolled_back"} and status.get("state") in {"queued", "preparing", "applying"}:
                status["state"] = transaction["state"]
        if status.get("state") in {"preparing", "applying", "restoring", "recovering"} and status.get("unit"):
            active = subprocess.run(["systemctl", "--user", "is-active", status["unit"]],
                                    text=True, capture_output=True, timeout=15)
            if active.returncode or active.stdout.strip() != "active":
                status["state"] = "interrupted"
        return {**status, "job": str(job)}
    except (OSError, ValueError, TypeError):
        return {"state": "error", "job": str(job), "error": "Update status could not be read"}


def _launch_lifeos_update(job: Path, action: str = "apply"):
    if action != "recover":
        service = subprocess.run(["systemctl", "--user", "is-active", "hermes-gateway.service"],
                                 text=True, capture_output=True, timeout=15)
        if service.returncode or service.stdout.strip() != "active":
            raise IncompatibleLifeOS("A running Hermes gateway user service is required")
    unit = f"lifeos-bridge-update-{uuid4().hex}"
    status = json.loads((job / "status.json").read_text(encoding="utf-8"))
    status["unit"] = unit
    with (job / "status.json").open("w", encoding="utf-8") as stream:
        os.fchmod(stream.fileno(), 0o600)
        json.dump(status, stream)
        stream.write("\n")
    command = ["systemd-run", "--user", "--collect",
               f"--unit={unit}",
               f"--setenv=HERMES_HOME={HERMES_HOME}", sys.executable,
               str(PLUGIN_DIR / "update_worker.py"), str(job)]
    if action != "apply":
        command.extend(["--action", action])
    launched = subprocess.run(command, text=True, capture_output=True, timeout=30)
    if launched.returncode:
        raise IncompatibleLifeOS(f"Could not start the LifeOS update worker: {launched.returncode}")


@router.post("/installation/update")
def apply_lifeos_update():
    if not (INSTALLED_ROOT / "LIFEOS/VERSION").is_file() or not BASELINE_PATH.is_file():
        raise HTTPException(status_code=409, detail="An installed LifeOS and VersionDrift baseline are required")
    previous = get_lifeos_update_status()
    if previous["state"] in {"queued", "preparing", "applying", "rollback_failed", "interrupted"}:
        raise HTTPException(status_code=409, detail="A LifeOS update job already owns this installation")
    try:
        selected_candidate = _candidate_path()
        candidate = validate_prepared_lifeos(selected_candidate)
        baseline = load_baseline(BASELINE_PATH, INSTALLED_ROOT)
        if previous["state"] == "applied" and candidate["upstream_commit"] == baseline["source_commit"]:
            raise IncompatibleLifeOS("The prepared LifeOS commit is already installed")
        prior_source = Path(baseline["source_root"])
        if prior_source.is_symlink() or not prior_source.is_dir():
            raise IncompatibleLifeOS("The prior LifeOS source is unavailable")
        if LIFEOS_UPDATE_ROOT.is_symlink():
            raise IncompatibleLifeOS("LifeOS update state directory cannot be a symbolic link")
        LIFEOS_UPDATE_ROOT.mkdir(parents=True, exist_ok=True, mode=0o700)
        job = LIFEOS_UPDATE_ROOT / f"update-{uuid4().hex}"
        job.mkdir(mode=0o700)
        request = {"installed": str(INSTALLED_ROOT), "hermes_home": str(HERMES_HOME),
                   "baseline": str(BASELINE_PATH), "candidate": str(selected_candidate),
                   "prior_source": str(prior_source), "candidate_commit": candidate["upstream_commit"],
                   "hermes_command": str(_host_source() / ".hermes/bin/hermes")}
        for name, data in (("request.json", request), ("status.json", {"state": "queued"})):
            with (job / name).open("w", encoding="utf-8") as stream:
                os.fchmod(stream.fileno(), 0o600)
                json.dump(data, stream)
                stream.write("\n")
        _launch_lifeos_update(job)
    except (IncompatibleLifeOS, OSError, ValueError, KeyError, subprocess.TimeoutExpired) as error:
        if "job" in locals() and job.is_dir():
            shutil.rmtree(job)
        raise HTTPException(status_code=409, detail=str(error)) from error
    return {"state": "queued", "job": str(job)}


@router.post("/installation/update/recover")
def recover_lifeos_update():
    previous = get_lifeos_update_status()
    if previous["state"] != "interrupted" or previous.get("transaction_state") not in {
        "stopped", "swapped", "restoring", "rollback_failed"
    }:
        raise HTTPException(status_code=409, detail="There is no interrupted LifeOS swap to recover")
    job = Path(previous["job"])
    try:
        (job / "status.json").write_text(json.dumps({"state": "recovering"}) + "\n", encoding="utf-8")
        _launch_lifeos_update(job, "recover")
    except (IncompatibleLifeOS, OSError, ValueError, subprocess.TimeoutExpired) as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return {"state": "recovering", "job": str(job)}


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
