# ABOUTME: Binds reviewed release plans to admitted actions and private operation state.
# ABOUTME: Serializes review and execution and rejects changed plans before service interruption.
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
import stat

from .cli import read_private
from .release_catalog import ReleaseRejected
from .release_programs import publish
from .release_stage import sha


def request_digest(request):
    value = {key: item for key, item in request.items() if key != 'memory_authorization'}
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


@contextmanager
def operation_lock(job):
    descriptor = os.open(job / 'operation.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise ReleaseRejected('An operation lock requires private owner storage')
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise RuntimeError('The release operation is running') from error
        yield
    finally:
        os.close(descriptor)


def action_state(job, action):
    allowed = {'apply': {'ready'}, 'restore': {'applied'},
               'recover': {'applying', 'restoring', 'recovering', 'recovery_required',
                           'queued-apply', 'queued-restore', 'queued-recover'}}
    if action not in allowed or read_private(job / 'status.json')['state'] not in allowed[action]:
        raise ReleaseRejected('The release action does not match its current state')


def seal_plan(job, request, plan):
    action_state(job, 'apply')
    publish(job / 'plan.json', (json.dumps(plan, sort_keys=True, indent=2) + '\n').encode())
    request['plan_sha256'] = sha(job / 'plan.json')
    publish(job / 'request.json', (json.dumps(request, indent=2) + '\n').encode())


def validate_plan(job, request):
    if sha(job / 'plan.json') != request.get('plan_sha256'):
        raise ReleaseRejected('The reviewed plan changes before the release action')
    return read_private(job / 'plan.json')


def write_admission(job, request, action):
    validate_plan(job, request)
    value = {'format': 1, 'action': action, 'request_sha256': request_digest(request)}
    publish(job / 'admission.json', (json.dumps(value) + '\n').encode())


def validate_admission(job, request, action):
    value = read_private(job / 'admission.json')
    if value != {'format': 1, 'action': action, 'request_sha256': request_digest(request)}:
        raise ReleaseRejected('The admitted request or action changes before execution')
    validate_plan(job, request)
    if read_private(job / 'status.json')['state'] != 'queued-' + action:
        raise ReleaseRejected('The release operation is no longer queued for this action')
