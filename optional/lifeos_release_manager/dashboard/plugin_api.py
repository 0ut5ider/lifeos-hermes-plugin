# ABOUTME: Reviews and authorizes complete release operations through authenticated Hermes sessions.
# ABOUTME: Issues native mount grants only for the configured installation owner and fixed job binding.
import importlib
import os
from pathlib import Path
import sys
import types

from fastapi import APIRouter, Depends, HTTPException, Request

directory = Path(__file__).resolve().parents[1]
namespace_name = 'lifeos_release_dashboard'
if namespace_name not in sys.modules:
    namespace = types.ModuleType(namespace_name)
    namespace.__path__ = [str(directory)]
    sys.modules[namespace_name] = namespace
commands = importlib.import_module(namespace_name + '.cli')
worker = importlib.import_module(namespace_name + '.release_worker')
stage = importlib.import_module(namespace_name + '.release_stage')


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
            source = stage.load_bridge(selected / 'plugins/lifeos-hook-bridge')
            configuration = source.memory_module('memory_service').MemoryConfiguration(selected / 'lifeos-memory.json')
            configuration.check_owner(configuration.load(), account)
        except (ValueError, OSError, RuntimeError, PermissionError, ImportError) as error:
            raise HTTPException(status_code=403, detail='The installation owner must review this release') from error
    return account


router = APIRouter(dependencies=[Depends(owner)])


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
    try:
        job, value = commands.operation(profile(), identifier)
        selected, plan = worker.review_operation(job, value)
        return {'identifier': identifier, 'version': value['version'], 'commit': value['commit'],
                'package_sha256': value['package_sha256'], 'fresh': plan['fresh'],
                'native_mount_required': plan['native_mount_required'],
                'restart_required': plan['services'] is not None,
                'state': commands.read_private(job / 'status.json')['state']}
    except (ValueError, OSError, RuntimeError) as error:
        raise HTTPException(status_code=409, detail='The prepared release changes or has unfinished recovery') from error


@router.post('/operations/{identifier}/{action}')
async def apply(identifier: str, action: str, request: Request, account: str = Depends(owner)):
    if action not in {'apply', 'recover', 'restore'} or await request.body() or request.query_params:
        raise HTTPException(status_code=400, detail='Release actions use a fixed prepared operation')
    authorization = None
    try:
        job, value = commands.operation(profile(), identifier)
        if action == 'apply':
            selected, plan = worker.review_operation(job, value)
        else:
            plan = commands.read_private(job / 'plan.json')
            selected = {'installed': Path(value['installed']), 'current': stage.load_bridge(profile() / 'plugins/lifeos-hook-bridge')}
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
