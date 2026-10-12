# ABOUTME: Binds reviewed release plans to admitted actions and private operation state.
# ABOUTME: Serializes review and execution and rejects changed plans before service interruption.
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
import stat
import subprocess
from pathlib import Path

from .cli import read_private
from .release_catalog import ReleaseRejected
from .release_programs import publish
from .release_stage import sha


def request_digest(request):
    value = {key: item for key, item in request.items() if key != 'memory_authorization'}
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


class OperationBusy(RuntimeError):
    pass


@contextmanager
def operation_lock(job, *, name='operation.lock'):
    descriptor = os.open(job / name, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise ReleaseRejected('An operation lock requires private owner storage')
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise OperationBusy('The release operation is running') from error
        yield
    finally:
        os.close(descriptor)


def process_stamp(pid):
    if type(pid) is not int or pid <= 0:
        raise ReleaseRejected('The worker process identity is invalid')
    try:
        process = Path('/proc') / str(pid)
        if process.stat().st_uid != os.getuid():
            raise ReleaseRejected('The worker belongs to another account')
        fields = (process / 'stat').read_text().rsplit(')', 1)[1].split()
        return None if fields[0] in {'Z', 'X'} else fields[19]
    except FileNotFoundError:
        return None


def record_worker(job, pid):
    publish(job / 'worker-launch.json', json.dumps({'kind': 'process', 'pid': pid,
            'start_time': process_stamp(pid)}).encode())


def worker_running(job):
    if not (job / 'worker-launch.json').exists():
        return None
    value = read_private(job / 'worker-launch.json')
    if value.get('kind') == 'process' and set(value) == {'kind', 'pid', 'start_time'}:
        current = process_stamp(value['pid'])
        return current is not None and current == value['start_time']
    if value == {'kind': 'service', 'unit': 'lifeos-release-' + job.name}:
        result = subprocess.run(['systemctl', '--user', 'show', value['unit'], '--property=ActiveState', '--value'],
            capture_output=True, text=True, timeout=10)
        if result.returncode:
            raise ReleaseRejected('The worker service state is unavailable')
        return result.stdout.strip() in {'active', 'activating', 'deactivating', 'reloading'}
    raise ReleaseRejected('The worker receipt changes its fixed identity')


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
