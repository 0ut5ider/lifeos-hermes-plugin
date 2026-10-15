# ABOUTME: Reviews and authorizes complete release operations through authenticated Hermes sessions.
# ABOUTME: Issues native mount grants only for the configured installation owner and fixed job binding.
import importlib
import os
from pathlib import Path
import sys
import types

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

directory = Path(__file__).resolve().parents[1]
namespace_name = 'lifeos_release_dashboard'
if namespace_name not in sys.modules:
    namespace = types.ModuleType(namespace_name)
    namespace.__path__ = [str(directory)]
    sys.modules[namespace_name] = namespace
commands = importlib.import_module(namespace_name + '.cli')
preparation = importlib.import_module(namespace_name + '.release_preparation')
worker = importlib.import_module(namespace_name + '.release_worker')
stage = importlib.import_module(namespace_name + '.release_stage')
services = importlib.import_module(namespace_name + '.release_services')
memory_workflow = importlib.import_module(namespace_name + '.memory_workflow')


def profile():
    from hermes_constants import get_hermes_home
    return get_hermes_home()


def owner(request: Request):
    from hermes_cli.dashboard_auth.base import Session
    session = getattr(request.state, 'session', None)
    if not isinstance(session, Session):
        raise HTTPException(status_code=401, detail='An authenticated Hermes dashboard session is required')
    if request.method != 'GET':
        origin = request.headers.get('origin')
        if origin and origin != request.url.scheme + '://' + request.url.netloc:
            raise HTTPException(status_code=403, detail='Use the installed dashboard origin')
    account = 'dashboard:' + session.provider + ':' + session.user_id
    selected = profile()
    if (selected / 'lifeos-memory.json').exists():
        try:
            active = selected / 'plugins/lifeos-hook-bridge'
            if active.is_dir():
                source = stage.load_bridge(active)
            else:
                identifier = request.path_params.get('identifier')
                if identifier is None:
                    raise PermissionError('Select the interrupted release for owner recovery')
                job, value = commands.operation(selected, identifier)
                source = worker.recovery_bridge(job, selected)
            configuration = source.memory_module('memory_service').MemoryConfiguration(selected / 'lifeos-memory.json')
            configuration.check_owner(configuration.load(), account)
        except (ValueError, OSError, RuntimeError, PermissionError, ImportError) as error:
            raise HTTPException(status_code=403, detail='The installation owner must review this release') from error
    return account


router = APIRouter(dependencies=[Depends(owner)])


@router.get('/memory-workflows')
def memory_workflows(account: str = Depends(owner)):
    try:
        return JSONResponse(memory_workflow.status(profile(),owner=account),headers={'Cache-Control':'no-store'})
    except (ValueError,OSError,RuntimeError) as error:
        raise HTTPException(status_code=409,detail='Memory workflow status is unavailable under this profile') from error


@router.post('/memory-workflows',status_code=202)
async def prepare_memory_workflow(request: Request, account: str = Depends(owner)):
    data=bytearray()
    async for chunk in request.stream():
        if len(data)+len(chunk)>384*1024:
            raise HTTPException(status_code=413,detail='Use a bounded reviewed memory workflow')
        data.extend(chunk)
    if request.query_params:raise HTTPException(status_code=400,detail='Use the reviewed memory workflow fields')
    try:selection=memory_workflow.selection(commands._json(data))
    except ValueError as error:raise HTTPException(status_code=400,detail=str(error)) from error
    try:
        return await run_in_threadpool(memory_workflow.queue,profile(),selection,owner=account,launch=memory_workflow.launch)
    except PermissionError as error:
        raise HTTPException(status_code=403,detail='The installation owner must authorize this memory workflow') from error
    except (ValueError,OSError,RuntimeError) as error:
        raise HTTPException(status_code=409,detail='Complete or recover the pending memory operation first') from error


@router.post('/memory-workflows/{identifier}/{action}',status_code=202)
async def apply_memory_workflow(identifier: str, action: str, request: Request, account: str = Depends(owner)):
    body=await request.body()
    try:value=commands._json(body) if len(body)<=1024 else None
    except ValueError:value=None
    if (action not in {'apply','recover','rollback'} or not isinstance(value,dict) or set(value)!={'signature'}
            or not isinstance(value['signature'],str) or memory_workflow.SIGNATURE.fullmatch(value['signature']) is None
            or memory_workflow.IDENTIFIER.fullmatch(identifier) is None or request.query_params):
        raise HTTPException(status_code=400,detail='Use the server-issued workflow identifier and exact reviewed signature')
    try:
        return await run_in_threadpool(memory_workflow.admit,profile(),identifier,action,value['signature'],
            owner=account,launch=memory_workflow.launch)
    except PermissionError as error:
        raise HTTPException(status_code=403,detail='The installation owner must authorize memory recovery') from error
    except (ValueError,OSError,RuntimeError) as error:
        raise HTTPException(status_code=409,detail='The memory workflow changed or is still running') from error


@router.get('/installation')
def installation():
    selected = commands.profile_directory(profile())
    existing = any(path.exists() or path.is_symlink() for path in (
        selected / 'integration-release.json', selected / 'lifeos-installation.json', Path.home() / '.claude'))
    return {'installed': existing}


@router.post('/prepare', status_code=202)
async def prepare(request: Request):
    body = await request.body()
    if request.query_params or len(body) > 4096:
        raise HTTPException(status_code=400, detail='Use a bounded release selection')
    try:
        value = preparation.selection(commands._json(body))
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    try:
        return await run_in_threadpool(preparation.queue, profile(), value)
    except (ValueError, OSError, RuntimeError) as error:
        raise HTTPException(status_code=409, detail='Preparation is unavailable or already running under this profile') from error


@router.get('/operations')
def operations():
    try:
        return commands.status(profile())
    except (ValueError, OSError, RuntimeError) as error:
        raise HTTPException(status_code=409, detail='Release status is unavailable under this profile') from error


@router.post('/operations/{identifier}/review')
async def review(identifier: str, request: Request):
    if await request.body() or request.query_params:
        raise HTTPException(status_code=400, detail='Release review uses the prepared operation')
    return await run_in_threadpool(review_release, identifier)


def review_release(identifier):
    try:
        job, value = commands.operation(profile(), identifier)
        selected, plan = worker.review_operation(job, value)
        return {'identifier': identifier, 'version': value['version'], 'commit': value['commit'],
                'package_sha256': value['package_sha256'], 'fresh': plan['fresh'],
                'native_mount_required': plan['native_mount_required'],
                'restart_required': plan['services'] is not None,
                'state': commands.read_private(job / 'status.json')['state']}
    except services.FirstInstallationUnavailable as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except (ValueError, OSError, RuntimeError) as error:
        raise HTTPException(status_code=409, detail='The prepared release changes or has unfinished recovery') from error


@router.post('/operations/{identifier}/{action}')
async def apply(identifier: str, action: str, request: Request, account: str = Depends(owner)):
    if action not in {'apply', 'recover', 'restore'} or await request.body() or request.query_params:
        raise HTTPException(status_code=400, detail='Release actions use a fixed prepared operation')
    return await run_in_threadpool(apply_release, identifier, action, account)


def apply_release(identifier, action, account):
    authorization = None
    try:
        job, value = commands.operation(profile(), identifier)
        if action == 'apply':
            selected, plan = worker.review_operation(job, value)
        else:
            plan = worker.validate_plan(job, value)
            selected = {'installed': Path(value['installed']), 'current': worker.recovery_bridge(job, profile())}
        administration = selected['current'].memory_administration()
        if plan['native_mount_required'] and administration.required(selected['installed'], profile()):
            configuration = administration.MemoryConfiguration(profile() / 'lifeos-memory.json')
            authorization = administration.issue(configuration, account, ttl=3600,
                binding=administration.job_binding(job, value, action))
        result = commands.launch(profile(), identifier, action, authorization=authorization)
        authorization = None
        return result
    except PermissionError as error:
        raise HTTPException(status_code=403, detail='The installation owner must authorize native mounting') from error
    except (ValueError, OSError, RuntimeError) as error:
        raise HTTPException(status_code=409, detail='The release operation is unavailable under the current profile') from error
    finally:
        if authorization is not None:
            administration.revoke(configuration, authorization)
