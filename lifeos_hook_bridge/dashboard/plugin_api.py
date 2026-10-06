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

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
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
HERMES_HOME = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
# The profile setting selects the LifeOS home; selection and return restart this dashboard.
LIFEOS_HOME = install_module.memory_module('lifeos_installation').selection(HERMES_HOME).home
INSTALLED_ROOT = LIFEOS_HOME / ".claude"
BASELINE_PATH = default_baseline_path(LIFEOS_HOME)
INSTALL_CANDIDATE = Path.home() / ".local/share/lifeos-bridge/lifeos-candidate"
HERMES_CANDIDATE = Path.home() / ".local/share/lifeos-bridge/hermes-candidate"
HOST_PATCH_ROOT = Path.home() / ".local/state/lifeos-hook-bridge/host-patches"
LIFEOS_UPDATE_ROOT = Path.home() / ".local/state/lifeos-hook-bridge/updates"
SELECTION_ROOT = Path.home() / ".local/state/lifeos-hook-bridge/selections"
HOST_SOURCE = None
PATCHED_HOOKS = {"pre_prompt_admission", "pre_command_approval", "augment_tool_result", "pre_turn_stop", "on_turn_result"}


async def _dashboard_origin(request: Request):
    if request.method in {'POST', 'PUT', 'PATCH', 'DELETE'}:
        origin = request.headers.get('origin')
        if origin and origin != request.url.scheme + '://' + request.url.netloc:
            raise HTTPException(status_code=403, detail='Use the installed dashboard origin')


router = APIRouter(dependencies=[Depends(_dashboard_origin)])


class MemoryResponseHeaders:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        path = scope.get('path', '')
        root = scope.get('root_path', '')
        if root and path.startswith(root + '/'):
            path = path[len(root):]
        prefix = '/api/plugins/lifeos-hook-bridge/memory'
        if scope['type'] != 'http' or (path != prefix and not path.startswith(prefix + '/')):
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
                                    Path(sys.executable), PLUGIN_DIR / 'memory_mcp.py')


def _memory_action(action):
    try:
        return action(_memory_preferences())
    except PermissionError as error:
        raise HTTPException(status_code=403, detail='This dashboard account has no installation owner binding') from error
    except (ValueError, OSError, RuntimeError, sqlite3.Error, subprocess.TimeoutExpired) as error:
        raise HTTPException(status_code=409, detail='Memory is unavailable under the current installation policy') from error


def _memory_account(request: Request) -> str:
    try:
        from hermes_cli.dashboard_auth.base import Session
    except ImportError as error:
        raise HTTPException(status_code=503, detail='Memory request authentication is unavailable') from error
    session = getattr(request.state, 'session', None)
    if not isinstance(session, Session):
        raise HTTPException(status_code=401, detail='An authenticated dashboard session is required')
    return f'dashboard:{session.provider}:{session.user_id}'


@router.get('/memory')
def get_memory(account: str = Depends(_memory_account)):
    return _memory_action(lambda preferences:preferences.status(account=account))


def _mount_transaction():
    return install_module.memory_module('mount_transaction').MountTransaction(
        INSTALLED_ROOT, HERMES_HOME, BASELINE_PATH)


def _mount_owner_action(account, action):
    return _installation_action(lambda: _execute_mount_owner_action(account, action))


def _installation_action(action, *, resume_update=False):
    try:
        with install_module.memory_module('installation_lock').installation_lock(HERMES_HOME):
            if not resume_update and get_lifeos_update_status()['state'] in {
                    'queued', 'preparing', 'applying', 'restoring', 'recovering',
                    'interrupted', 'rollback_failed', 'error'}:
                raise HTTPException(status_code=409, detail='A LifeOS update job already owns this installation')
            return action()
    except (OSError, RuntimeError) as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


def _execute_mount_owner_action(account, action):
    administration = install_module.memory_administration()
    if administration.required(INSTALLED_ROOT, HERMES_HOME):
        configuration = _memory_preferences().configuration
        binding = {'action':'recover'} if action == 'recover' else None
        with administration.lease(configuration, account, binding=binding) as authorization:
            if action == 'recover':
                administration.validate(configuration, authorization, purpose='recover', check_binding=True, binding=binding)
                return _mount_transaction().recover()
            environment = administration.mount_environment(INSTALLED_ROOT, HERMES_HOME, authorization)
            return _execute_mount(environment)
    if action == 'recover':
        return _mount_transaction().recover()
    return _execute_mount(administration.mount_environment(INSTALLED_ROOT, HERMES_HOME))


def _execute_mount(environment):
    bun, hermes = shutil.which('bun'), shutil.which('hermes')
    if not bun or not hermes:
        raise RuntimeError('Bun and the Hermes command are required to mount LifeOS')
    return _mount_transaction().execute(environment, bun, hermes)


async def _fixed_mount_request(request: Request):
    await _dashboard_origin(request)
    if request.query_params or await request.body():
        raise HTTPException(status_code=400, detail='Mount requests use the installed owner configuration')


@router.post('/memory/owner')
async def claim_memory_owner(request: Request, account: str = Depends(_memory_account)):
    await _fixed_mount_request(request)
    return await run_in_threadpool(_memory_action, lambda preferences: preferences.claim(account=account))


@router.post('/memory/remount')
async def remount_memory(request: Request, account: str = Depends(_memory_account)):
    await _fixed_mount_request(request)
    headers = {'Cache-Control':'no-store'}
    try:
        configuration = _memory_preferences().configuration
        configuration_value = configuration.load()
        configuration.check_owner(configuration_value, account)
        binding = install_module.memory_module('memory_http').installation_binding(configuration_value, configuration.path)
        result = await run_in_threadpool(_mount_owner_action, account, 'mount')
        return JSONResponse({'ok':True, 'exitCode':0, 'output':result['output'], 'error':None,
                             'mount':{'state':result['state'], 'restart_required':True}},
                            headers={**headers, 'X-LifeOS-Memory-Installation':binding})
    except PermissionError:
        return JSONResponse({'error':'The installation owner must authorize mounting'}, status_code=403, headers=headers)
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired, sqlite3.Error):
        return JSONResponse({'error':'Mounting is unavailable. Check setup and recovery in the LifeOS plugin.'},
                            status_code=409, headers=headers)


@router.post('/installation/mount/recover')
async def recover_mount(request: Request, account: str = Depends(_memory_account)):
    await _fixed_mount_request(request)
    try:
        return await run_in_threadpool(_mount_owner_action, account, 'recover')
    except PermissionError as error:
        raise HTTPException(status_code=403, detail='The installation owner must authorize recovery') from error
    except (OSError, ValueError, RuntimeError) as error:
        raise HTTPException(status_code=409, detail='Recovery cannot overwrite a later edit or invalid snapshot') from error


@router.get('/memory/pulse/{view}')
def get_memory_pulse(view: Literal['snapshot', 'state', 'health', 'runs', 'graph', 'telos_freshness',
                                  'telos_stale', 'telos_freshness_summary', 'context_freshness',
                                  'context_freshness_summary', 'telos_health'], request: Request,
                     account: str = Depends(_memory_account)):
    headers = {'Cache-Control': 'no-store'}
    if request.query_params:
        return JSONResponse({'error': 'Memory views use the installed owner configuration'}, status_code=400, headers=headers)
    try:
        result, binding = _memory_preferences().pulse_response(view, account=account)
    except PermissionError:
        return JSONResponse({'error': 'This dashboard account has no installation owner binding'},
                            status_code=403, headers=headers)
    except (ValueError, OSError, RuntimeError, sqlite3.Error, subprocess.TimeoutExpired):
        return JSONResponse({'error': 'Memory is unavailable under the current installation policy'},
                            status_code=503, headers=headers)
    return JSONResponse(result, headers={**headers,'X-LifeOS-Memory-Installation':binding})


@router.post('/memory/review')
def review_memory(request: dict, account: str = Depends(_memory_account)):
    if set(request) != {'tool','arguments'} or not isinstance(request['tool'], str) or not isinstance(request['arguments'], dict):
        raise HTTPException(status_code=400, detail='Choose a memory action and its arguments')
    return _memory_action(lambda preferences:preferences.review(request['tool'], request['arguments'], account=account))


@router.get('/memory/wiki')
def get_memory_wiki(request: Request, account: str = Depends(_memory_account)):
    return _memory_source_read('wiki', request, account)


@router.get('/memory/knowledge')
def get_memory_knowledge(request: Request, account: str = Depends(_memory_account)):
    return _memory_source_read('knowledge', request, account)


def _memory_source_read(view: Literal['wiki', 'knowledge'], request: Request, account: str):
    preferences = _memory_preferences()
    request_target = importlib.import_module('lifeos_memory_settings.memory_' + view).request_target
    headers = {'Cache-Control': 'no-store'}
    try:
        if list(request.query_params.keys()) != ['target'] or len(request.query_params.getlist('target')) != 1:
            raise ValueError('Source reads require one fixed route')
        target = request_target(request.query_params['target'])
    except LookupError:
        return JSONResponse({'error': 'This source route is not a governed read view'}, status_code=404, headers=headers)
    except ValueError:
        return JSONResponse({'error': 'Invalid source read route'}, status_code=400, headers=headers)
    try:
        operation = preferences.wiki_response if view == 'wiki' else preferences.knowledge_response
        result, binding = operation(target, account=account)
    except PermissionError:
        return JSONResponse({'error': 'This dashboard account has no installation owner binding'}, status_code=403, headers=headers)
    except (ValueError, OSError, RuntimeError, sqlite3.Error, subprocess.TimeoutExpired):
        return JSONResponse({'error': 'Memory is unavailable under the current installation policy'}, status_code=503, headers=headers)
    return JSONResponse(result['body'], status_code=result['status'],
                        headers={**headers, 'X-LifeOS-Memory-Installation': binding})


@router.post('/memory/prompt/preview')
def preview_memory_prompt(request: dict, account: str = Depends(_memory_account)):
    if set(request) != {'keep_output_format'} or type(request['keep_output_format']) is not bool:
        raise HTTPException(status_code=400, detail='Choose whether to retain the native output format')
    return _memory_action(lambda preferences: preferences.preview_prompt(**request, account=account))


@router.post('/memory/prompt')
def publish_memory_prompt(request: dict, account: str = Depends(_memory_account)):
    return _memory_action(lambda preferences: preferences.publish_prompt(request, account=account))


@router.post('/memory/adoption/preview')
def preview_memory_adoption(request: dict, account: str = Depends(_memory_account)):
    if request:
        raise HTTPException(status_code=400, detail='Source preview uses the installed LifeOS configuration')
    return _memory_action(lambda preferences:preferences.preview_adoption(account=account))


@router.post('/memory/import/preview')
def preview_memory_import(request: dict, account: str = Depends(_memory_account)):
    if request:
        raise HTTPException(status_code=400, detail='Import review uses the installed Hermes profile')
    return _memory_action(lambda preferences: preferences.preview_import(account=account))


@router.post('/memory/import/snapshot')
def prepare_memory_import(request: dict, account: str = Depends(_memory_account)):
    if set(request) != {'signature'}:
        raise HTTPException(status_code=400, detail='Provide the reviewed Hermes import signature')
    return _memory_action(lambda preferences: preferences.prepare_import(request, account=account))


@router.post('/memory/fresh/prepare')
async def prepare_fresh_store(request: dict, account: str = Depends(_memory_account)):
    if (set(request) != {'principal_name','assistant_name'}
            or any(not isinstance(value,str) for value in request.values())):
        raise HTTPException(status_code=400, detail='Provide the principal and assistant display names')
    return await run_in_threadpool(_memory_action, lambda preferences: preferences.prepare_fresh(
        INSTALL_CANDIDATE, **request, account=account))


def _launch_fresh_store(arguments, unit):
    from hermes_cli import _launchers
    code = "worker = sys.argv.pop(1)\nsys.argv[0] = worker\nrunpy.run_path(worker, run_name='__main__')\n"
    runtime = _launchers.runtime_command(_host_source(), [str(PLUGIN_DIR / 'fresh_store_worker.py'), *arguments],
                                         code=code, python=sys.executable)
    command = ['systemd-run', '--user', '--collect', f'--unit={unit}', f'--setenv=HOME={Path.home()}',
               f'--setenv=HERMES_HOME={HERMES_HOME}', f"--setenv=PATH={os.environ.get('PATH', os.defpath)}", *runtime]
    launched = subprocess.run(command, text=True, capture_output=True, timeout=30)
    if launched.returncode:
        raise RuntimeError('Could not start the fresh store preparation')


@router.post('/memory/fresh/start', status_code=202)
def start_fresh_store(request: dict, account: str = Depends(_memory_account)):
    if (set(request) != {'principal_name', 'assistant_name'}
            or any(not isinstance(value, str) for value in request.values())):
        raise HTTPException(status_code=400, detail='Provide the principal and assistant display names')

    def start(preferences):
        from lifeos_memory_settings.fresh_store import _name
        preferences._configuration(account=account)
        _name(request['principal_name']); _name(request['assistant_name'])
        identifier = uuid4().hex
        _launch_fresh_store(['--configuration', str(preferences.configuration.path), '--candidate', str(INSTALL_CANDIDATE),
                             '--identifier', identifier, '--principal-name', request['principal_name'],
                             '--assistant-name', request['assistant_name'], '--account', account],
                            'lifeos-fresh-store-' + identifier)
        return {'identifier': identifier, 'state': 'preparing'}
    return _memory_action(start)


@router.delete('/memory/fresh/stores/{identifier}')
def remove_fresh_store(identifier: str, account: str = Depends(_memory_account)):
    return _memory_action(lambda preferences: preferences.remove_fresh(identifier, account=account))


@router.get('/memory/fresh/status')
def get_fresh_store_status(request: Request, account: str = Depends(_memory_account)):
    if request.query_params:
        raise HTTPException(status_code=400, detail='Fresh store status uses the installed owner configuration')
    return _memory_action(lambda preferences: preferences.fresh_status(account=account))


@router.post('/memory/sources/preview')
def preview_memory_sources(request: dict, account: str = Depends(_memory_account)):
    if set(request) != {'paths'}:
        raise HTTPException(status_code=400, detail='Choose installed source paths for review')
    return _memory_action(lambda preferences: preferences.preview_sources(request['paths'], account=account))


@router.post('/memory/sources')
def approve_memory_sources(request: dict, account: str = Depends(_memory_account)):
    return _memory_action(lambda preferences: preferences.approve_sources(request, account=account))


@router.post('/memory/adoption')
def adopt_memory_sources(request: dict, account: str = Depends(_memory_account)):
    if set(request) != {'signature','projects','request_id'}:
        raise HTTPException(status_code=400, detail='Provide the reviewed source preview, project assignments, and request identifier')
    return _memory_action(lambda preferences:preferences.adopt(request, account=account))


@router.post('/memory/sharing')
def set_memory_sharing(request: dict, account: str = Depends(_memory_account)):
    if set(request) != {'enabled'} or type(request['enabled']) is not bool:
        raise HTTPException(status_code=400, detail='Choose whether memory sharing is enabled')
    return _memory_action(lambda preferences:preferences.sharing(request['enabled'], account=account))


@router.post('/memory/connections')
def enroll_memory_connection(request: dict, account: str = Depends(_memory_account)):
    return _memory_action(lambda preferences:preferences.enroll(request, account=account))


@router.delete('/memory/connections/{client}')
def revoke_memory_connection(client: str, account: str = Depends(_memory_account)):
    return _memory_action(lambda preferences:preferences.revoke(client, account=account))


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
    # The dashboard keeps the hook list it loaded at start; a later host change needs a restart.
    host_state = get_host_patch_status()['state']
    restart_required = ((host_state == 'applied' and hermes != 'patched_hooks_present')
                        or (host_state == 'rolled_back' and hermes == 'patched_hooks_present'))
    mount = {'state':'none', 'recovery_required':False}
    if (HERMES_HOME / '.lifeos-mount').exists():
        try:
            mount = _mount_transaction().status()
        except (ValueError, OSError, RuntimeError):
            mount = {'state':'unavailable', 'recovery_required':False}
    return {
        'mount': mount,
        "lifeos": lifeos,
        "version": version_file.read_text(encoding="utf-8").strip() if version_file.is_file() else None,
        "hermes": hermes,
        "dashboard_restart_required": restart_required,
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


@router.post("/installation/prepare", dependencies=[Depends(_fixed_mount_request)])
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


@router.post("/installation/apply", dependencies=[Depends(_fixed_mount_request)])
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


@router.post("/installation/finalize", dependencies=[Depends(_memory_account), Depends(_fixed_mount_request)])
def finalize_installation(account: str = Depends(_memory_account)):
    return _installation_action(lambda: _finalize_installation(account))


def _finalize_installation(account: str):
    if not (INSTALLED_ROOT / "LIFEOS/VERSION").is_file() or not (INSTALLED_ROOT / "settings.json").is_file():
        raise HTTPException(status_code=409, detail="Install LifeOS before finishing setup")
    if BASELINE_PATH.exists() or BASELINE_PATH.is_symlink():
        raise HTTPException(status_code=409, detail="A VersionDrift baseline already exists")
    try:
        if install_module.memory_administration().required(INSTALLED_ROOT, HERMES_HOME):
            preferences = _memory_preferences()
            authorization = preferences.authorize_mount(account=account)
            try:
                return finalize_prepared_lifeos(_candidate_path(), INSTALLED_ROOT, HERMES_HOME,
                    BASELINE_PATH, create_baseline, save_baseline, memory_authorization=authorization)
            finally:
                preferences.revoke_mount(authorization)
        return finalize_prepared_lifeos(_candidate_path(), INSTALLED_ROOT, HERMES_HOME,
                                        BASELINE_PATH, create_baseline, save_baseline)
    except PermissionError as error:
        raise HTTPException(status_code=403, detail='The installation owner must authorize managed setup') from error
    except (IncompatibleLifeOS, OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.post("/installation/prepare-hermes", dependencies=[Depends(_fixed_mount_request)])
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
                status["state"] = (status.get('transaction_state') if status.get('transaction_state')
                                   in {'applied', 'rolled_back'} else 'interrupted')
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
    from hermes_cli import _launchers
    arguments = [str(PLUGIN_DIR / "update_worker.py"), str(job)]
    if action != "apply":
        arguments.extend(["--action", action])
    code = "worker = sys.argv.pop(1)\nsys.argv[0] = worker\nrunpy.run_path(worker, run_name='__main__')\n"
    runtime = _launchers.runtime_command(_host_source(), arguments, code=code, python=sys.executable)
    command = ["systemd-run", "--user", "--collect", f"--unit={unit}",
               f"--setenv=HOME={INSTALLED_ROOT.parent}", f"--setenv=HERMES_HOME={HERMES_HOME}",
               f"--setenv=PATH={os.environ.get('PATH', os.defpath)}"]
    if 'PULSE_URL' in os.environ:
        command.append(f"--setenv=PULSE_URL={os.environ['PULSE_URL']}")
    command.extend(runtime)
    launched = subprocess.run(command, text=True, capture_output=True, timeout=30)
    if launched.returncode:
        raise IncompatibleLifeOS(f"Could not start the LifeOS update worker: {launched.returncode}")


@router.post("/installation/update", dependencies=[Depends(_memory_account), Depends(_fixed_mount_request)])
def apply_lifeos_update(account: str = Depends(_memory_account)):
    return _installation_action(lambda: _apply_lifeos_update(account))


def _apply_lifeos_update(account: str):
    if not (INSTALLED_ROOT / "LIFEOS/VERSION").is_file() or not BASELINE_PATH.is_file():
        raise HTTPException(status_code=409, detail="An installed LifeOS and VersionDrift baseline are required")
    previous = get_lifeos_update_status()
    if previous["state"] in {"queued", "preparing", "applying", "restoring", "recovering", "rollback_failed", "interrupted", "error"}:
        raise HTTPException(status_code=409, detail="A LifeOS update job already owns this installation")
    if get_host_patch_status()['state'] in {'staged', 'applying', 'restoring', 'restore_failed', 'rollback_failed', 'error'}:
        raise HTTPException(status_code=409, detail='A Hermes patch job already owns this installation')
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
        if install_module.memory_administration().required(INSTALLED_ROOT, HERMES_HOME):
            preferences = _memory_preferences()
            authorization = preferences.authorize_mount(account=account, ttl=3600,
                binding=install_module.memory_administration().job_binding(job, request, 'apply'))
            request['memory_authorization'] = str(authorization)
        for name, data in (("request.json", request), ("status.json", {"state": "queued"})):
            with (job / name).open("w", encoding="utf-8") as stream:
                os.fchmod(stream.fileno(), 0o600)
                json.dump(data, stream)
                stream.write("\n")
        _launch_lifeos_update(job)
    except (IncompatibleLifeOS, OSError, ValueError, RuntimeError, KeyError, subprocess.TimeoutExpired) as error:
        if 'authorization' in locals():
            preferences.revoke_mount(authorization)
        if "job" in locals() and job.is_dir():
            shutil.rmtree(job)
        if isinstance(error, PermissionError):
            raise HTTPException(status_code=403, detail='The installation owner must authorize managed updates') from error
        raise HTTPException(status_code=409, detail=str(error)) from error
    return {"state": "queued", "job": str(job)}


@router.post("/installation/update/recover")
async def recover_lifeos_update(request: Request, account: str = Depends(_memory_account)):
    await _fixed_mount_request(request)
    return await run_in_threadpool(_recover_lifeos_update, account)


def _recover_lifeos_update(account: str):
    return _installation_action(lambda: _recover_lifeos_update_locked(account), resume_update=True)


def _recover_lifeos_update_locked(account: str):
    previous = get_lifeos_update_status()
    if previous["state"] != "interrupted" or previous.get("transaction_state") not in {
        "stopped", "swapped", "restore_stopping", "restoring", "rollback_failed"
    }:
        raise HTTPException(status_code=409, detail="There is no interrupted LifeOS swap to recover")
    return _resume_lifeos_update(previous, account, 'recover')


@router.post("/installation/update/restore")
async def restore_lifeos_update(request: Request, account: str = Depends(_memory_account)):
    await _fixed_mount_request(request)
    return await run_in_threadpool(_restore_lifeos_update, account)


def _restore_lifeos_update(account: str):
    return _installation_action(lambda: _restore_lifeos_update_locked(account), resume_update=True)


def _restore_lifeos_update_locked(account: str):
    previous = get_lifeos_update_status()
    if previous['state'] != 'applied' or previous.get('transaction_state') != 'applied':
        raise HTTPException(status_code=409, detail='There is no applied LifeOS update to restore')
    return _resume_lifeos_update(previous, account, 'restore')


def _resume_lifeos_update(previous: dict, account: str, action: str):
    job = Path(previous["job"])
    changed = False
    try:
        original_request = (job / 'request.json').read_bytes()
        original_status = (job / 'status.json').read_bytes()
        if install_module.memory_administration().required(INSTALLED_ROOT, HERMES_HOME):
            request = json.loads(original_request)
            if Path(request['installed']).absolute() != INSTALLED_ROOT.absolute() or Path(request['hermes_home']).absolute() != HERMES_HOME.absolute():
                raise PermissionError('The update job belongs to another installation')
            preferences = _memory_preferences()
            authorization = preferences.authorize_mount(account=account, ttl=3600,
                binding=install_module.memory_administration().job_binding(job, request, action))
            request['memory_authorization'] = str(authorization)
        if action == 'restore':
            install_module.memory_module('update_transaction').validate_restore(
                job / 'snapshot', installed=INSTALLED_ROOT)
        if 'authorization' in locals():
            changed = True
            install_module.memory_administration().publish(job / 'request.json',
                (json.dumps(request) + '\n').encode())
        changed = True
        install_module.memory_administration().publish(job / 'status.json',
            (json.dumps({'state': 'recovering' if action == 'recover' else 'restoring'}) + '\n').encode())
        _launch_lifeos_update(job, action)
    except (IncompatibleLifeOS, OSError, ValueError, RuntimeError, KeyError, subprocess.TimeoutExpired) as error:
        if 'authorization' in locals():
            preferences.revoke_mount(authorization)
        if changed:
            install_module.memory_administration().publish(job / 'request.json', original_request)
            install_module.memory_administration().publish(job / 'status.json', original_status)
        if isinstance(error, PermissionError):
            raise HTTPException(status_code=403, detail='The installation owner must authorize this update action') from error
        raise HTTPException(status_code=409, detail=str(error)) from error
    return {"state": "recovering" if action == 'recover' else 'restoring', "job": str(job)}


def _latest_selection():
    if not SELECTION_ROOT.is_dir() or SELECTION_ROOT.is_symlink():
        return None
    jobs = [path for path in SELECTION_ROOT.iterdir()
            if path.is_dir() and not path.is_symlink() and (path / 'request.json').is_file()]
    return max(jobs, key=lambda path: path.stat().st_mtime_ns) if jobs else None


def _selection_status():
    job = _latest_selection()
    if job is None:
        return {'state': 'none'}
    try:
        status = json.loads((job / 'status.json').read_text(encoding='utf-8'))
        if status.get('state') in {'queued', 'running', 'recovering'} and status.get('unit'):
            active = subprocess.run(['systemctl', '--user', 'is-active', status['unit']],
                                    text=True, capture_output=True, timeout=15)
            if active.returncode or active.stdout.strip() != 'active':
                journal = job / 'transaction/journal.json'
                state = json.loads(journal.read_text())['state'] if journal.is_file() else 'failed'
                status['state'] = state if state in {'applied', 'rolled_back'} else 'interrupted'
        return {**status, 'job': str(job)}
    except (OSError, ValueError, KeyError, subprocess.TimeoutExpired):
        return {'state': 'error', 'job': str(job)}


@router.get('/installation/selection')
def get_installation_selection(account: str = Depends(_memory_account)):
    selected = install_module.memory_module('lifeos_installation').selection(HERMES_HOME)
    return {'configured': selected.configured, 'home': str(selected.home),
            'running_home': str(LIFEOS_HOME), 'job': _selection_status()}


def _launch_selection(job: Path, action: str):
    from hermes_cli import _launchers
    unit = f'lifeos-bridge-selection-{uuid4().hex}'
    status = {'state': 'queued' if action == 'select' else 'recovering', 'unit': unit}
    (job / 'status.json').write_text(json.dumps(status) + '\n')
    os.chmod(job / 'status.json', 0o600)
    arguments = [str(PLUGIN_DIR / 'selection_worker.py'), str(job), '--action', action]
    code = "worker = sys.argv.pop(1)\nsys.argv[0] = worker\nrunpy.run_path(worker, run_name='__main__')\n"
    runtime = _launchers.runtime_command(_host_source(), arguments, code=code, python=sys.executable)
    command = ['systemd-run', '--user', '--collect', f'--unit={unit}', f'--setenv=HOME={Path.home()}',
               f'--setenv=HERMES_HOME={HERMES_HOME}', f"--setenv=PATH={os.environ.get('PATH', os.defpath)}",
               *runtime]
    launched = subprocess.run(command, text=True, capture_output=True, timeout=30)
    if launched.returncode:
        raise IncompatibleLifeOS('Could not start the LifeOS selection worker')


def _queue_selection(account: str, store: str | None):
    if _selection_status()['state'] in {'queued', 'running', 'recovering', 'interrupted', 'rolling_back'}:
        raise HTTPException(status_code=409, detail='A LifeOS selection job already owns this installation')
    selected = install_module.memory_module('lifeos_installation').selection(HERMES_HOME)
    request = {'profile': str(HERMES_HOME), 'target_home': None, 'candidate': None,
               'hermes_command': str(_host_source() / '.hermes/bin/hermes')}
    try:
        if store is None:
            if not selected.configured:
                raise HTTPException(status_code=409, detail='The account LifeOS home is already selected')
            _memory_preferences()._configuration(account=account)
        else:
            home, review = _memory_preferences().fresh_home(store, account=account)
            if selected.configured and selected.home == home:
                raise HTTPException(status_code=409, detail='This fresh store is already selected')
            if install_module.memory_administration().required(home / '.claude', HERMES_HOME):
                raise HTTPException(status_code=409, detail='Selecting a managed memory installation is not supported yet')
            candidate = _candidate_path()
            if validate_prepared_lifeos(candidate) != review.get('source'):
                raise HTTPException(status_code=409, detail='The fresh store was prepared from another LifeOS candidate')
            request.update(target_home=str(home), candidate=str(candidate))
        SELECTION_ROOT.mkdir(parents=True, exist_ok=True, mode=0o700)
        job = SELECTION_ROOT / f'selection-{uuid4().hex}'
        job.mkdir(mode=0o700)
        (job / 'request.json').write_text(json.dumps(request) + '\n')
        os.chmod(job / 'request.json', 0o600)
        _launch_selection(job, 'select')
    except PermissionError as error:
        raise HTTPException(status_code=403, detail='The installation owner must select the LifeOS home') from error
    except (IncompatibleLifeOS, OSError, ValueError, RuntimeError) as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return {'state': 'queued', 'job': str(job)}


@router.post('/installation/selection')
async def select_installation(request: Request, account: str = Depends(_memory_account)):
    body = await request.json()
    if (not isinstance(body, dict) or set(body) != {'store'} or not isinstance(body['store'], str)
            or request.query_params):
        raise HTTPException(status_code=400, detail='Choose one reviewed fresh store')
    return await run_in_threadpool(_installation_action, lambda: _queue_selection(account, body['store']))


@router.post('/installation/selection/return')
async def return_installation(request: Request, account: str = Depends(_memory_account)):
    await _fixed_mount_request(request)
    return await run_in_threadpool(_installation_action, lambda: _queue_selection(account, None))


@router.post('/installation/selection/recover')
async def recover_installation_selection(request: Request, account: str = Depends(_memory_account)):
    await _fixed_mount_request(request)

    def recover():
        status = _selection_status()
        if status['state'] != 'interrupted':
            raise HTTPException(status_code=409, detail='There is no interrupted LifeOS selection to recover')
        try:
            _memory_preferences()._configuration(account=account)
            _launch_selection(Path(status['job']), 'recover')
        except PermissionError as error:
            raise HTTPException(status_code=403, detail='The installation owner must recover the selection') from error
        except (IncompatibleLifeOS, OSError, ValueError, RuntimeError) as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        return {'state': 'recovering', 'job': status['job']}
    return await run_in_threadpool(_installation_action, recover)


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


@router.post("/installation/apply-hermes", dependencies=[Depends(_fixed_mount_request)])
def apply_hermes_installation():
    return _installation_action(_apply_hermes_installation)


def _apply_hermes_installation():
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


@router.post("/installation/restore-hermes", dependencies=[Depends(_fixed_mount_request)])
def restore_hermes_installation():
    return _installation_action(_restore_hermes_installation)


def _restore_hermes_installation():
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
