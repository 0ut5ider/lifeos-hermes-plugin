# ABOUTME: Prepares and starts complete qualified integration releases through Hermes commands.
# ABOUTME: Reports private operation state and keeps management separate from the active bridge.
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
from uuid import uuid4
from threading import Thread

from .release_catalog import ReleaseCatalog, ReleaseRejected, extract_package, _json
from .release_programs import publish
from .release_stage import load_bridge, prepare_runtime, sha, validate_package, runtime_source_fingerprint

IDENTIFIER = re.compile('[0-9a-f]{32}')


def configure(parser: argparse.ArgumentParser):
    actions = parser.add_subparsers(dest='action', required=True)
    prepare = actions.add_parser('prepare', help='Download and prepare the complete release before any live change.')
    prepare.add_argument('--version', help='Select an exact published integration version instead of the latest stable release.')
    prepare.add_argument('--name', default='User', help='Set the name only for a fresh native installation.')
    prepare.add_argument('--assistant', default='Hermes', help='Set the assistant name only for a fresh native installation.')
    status = actions.add_parser('status', help='Report release operations under this profile.')
    status.add_argument('identifier', nargs='?')
    for action in ('start', 'recover', 'rollback'):
        command = actions.add_parser(action)
        command.add_argument('identifier', help='Select a prepared operation identifier from this profile.')


def profile_directory(profile):
    profile = Path(profile).absolute()
    info = profile.stat()
    if (profile.resolve() != profile or not stat.S_ISDIR(info.st_mode)
            or info.st_uid != os.getuid() or info.st_mode & 0o022):
        raise ReleaseRejected('Release management requires the selected owner profile')
    return profile


def read_private(path, *, limit=2 * 1024 * 1024):
    path = Path(path).absolute()
    if path.parent.resolve() != path.parent:
        raise ReleaseRejected('The operation changes its physical directory')
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(descriptor, 'rb') as stream:
        info = os.fstat(stream.fileno())
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077
                or info.st_size > limit):
            raise ReleaseRejected('The operation requires a bounded private owner file')
        return _json(stream.read(limit + 1))


def job_directory(profile, identifier):
    if not isinstance(identifier, str) or IDENTIFIER.fullmatch(identifier) is None:
        raise ReleaseRejected('Choose an operation identifier returned by release preparation')
    profile = profile_directory(profile)
    job = profile / '.lifeos-releases' / identifier
    info = job.lstat()
    if (job.resolve() != job or not stat.S_ISDIR(info.st_mode)
            or info.st_uid != os.getuid() or info.st_mode & 0o077):
        raise ReleaseRejected('The release operation requires private profile storage')
    return job


def operation(profile, identifier):
    job = job_directory(profile, identifier)
    profile = Path(profile).absolute()
    request = read_private(job / 'request.json')
    if request.get('profile') != str(profile) or request.get('identifier') != identifier:
        raise ReleaseRejected('The operation belongs to another profile')
    return job, request


def write_state(job, state, *, error=None):
    value = {'identifier': job.name, 'state': state}
    if error is not None:
        value['error'] = error
    publish(job / 'status.json', (json.dumps(value) + '\n').encode())


def prepare(profile, version=None, *, name='User', assistant='Hermes', catalog=None):
    profile = profile_directory(profile)
    for value in (name, assistant):
        if not isinstance(value, str) or not value.strip() or len(value) > 100 or any(ord(c) < 32 for c in value):
            raise ReleaseRejected('Fresh installation names require bounded text')
    state = profile / '.lifeos-releases'
    state.mkdir(mode=0o700, exist_ok=True)
    if state.resolve() != state or state.stat().st_uid != os.getuid() or state.stat().st_mode & 0o077:
        raise ReleaseRejected('Release staging requires private profile storage')
    job = state / uuid4().hex
    job.mkdir(mode=0o700)
    write_state(job, 'preparing')
    try:
        downloaded = (catalog or ReleaseCatalog()).download(job / 'download', version)
        package = job / 'package'
        extract_package(downloaded['archive'], package)
        manifest = validate_package(package, downloaded['certificate'])
        source = load_bridge(package / 'lifeos_hook_bridge')
        names = source.memory_module('fresh_store')
        names._name(name.strip())
        names._name(assistant.strip())
        selected = source.memory_module('lifeos_installation').selection(profile)
        runtime = prepare_runtime(job, package, Path(downloaded['dashboard']), profile)
        request = {'format': 1, 'identifier': job.name, 'profile': str(profile),
            'account_home': str(Path.home()), 'installed': str(selected.installed),
            'version': manifest['version'], 'commit': manifest['head'],
            'package_sha256': sha(downloaded['archive']), 'certificate': downloaded['certificate'],
            'configuration_sha256': sha(profile / 'config.yaml'),
            'runtime': runtime, 'runtime_fingerprint': runtime_source_fingerprint(Path(runtime['source'])),
            'runtime_metadata_sha256': sha(job / 'manifest.json'),
            'python_lock_sha256': sha(package / 'python-runtime/uv.lock'),
            'name': name.strip(), 'assistant': assistant.strip()}
        publish(job / 'request.json', (json.dumps(request, indent=2) + '\n').encode())
        shutil.copytree(package / 'optional/lifeos_release_manager', job / 'worker',
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        write_state(job, 'ready')
        return {'identifier': job.name, 'state': 'ready', 'version': request['version'],
            'commit': request['commit'], 'package_sha256': request['package_sha256'], 'active_unchanged': True,
            'next': 'Use the release dashboard to review the operation, or run hermes lifeos-release start ' + job.name}
    except BaseException:
        write_state(job, 'preparation_failed', error='Preparation did not change the active installation.')
        raise


def status(profile, identifier=None):
    profile = profile_directory(profile)
    state = profile / '.lifeos-releases'
    if identifier is not None:
        job = job_directory(profile, identifier)
        if not (job / 'request.json').exists():
            return read_private(job / 'status.json')
        job, request = operation(profile, identifier)
        value = {**read_private(job / 'status.json'), 'version': request['version'], 'commit': request['commit'],
                 'restore_available': False, 'recover_available': False}
        if (job / 'plan.json').exists():
            from .release_operation import validate_plan, operation_lock, OperationBusy, worker_running
            plan = validate_plan(job, request)
            value['restore_available'] = value['state'] == 'applied' and not plan['fresh']
            if value['state'] in {'applying', 'recovering', 'restoring', 'recovery_required'} or value['state'].startswith('queued-'):
                try:
                    with operation_lock(job, name='launch.lock'), operation_lock(job):
                        running = worker_running(job)
                        value['recover_available'] = running is not True
                except OperationBusy:
                    pass
        return value
    operations = []
    if state.exists():
        for path in sorted(state.iterdir()):
            if IDENTIFIER.fullmatch(path.name):
                operations.append(status(profile, path.name))
    return {'operations': operations}


def launch(profile, identifier, action, *, authorization=None):
    from .release_operation import operation_lock
    job, request = operation(profile, identifier)
    with operation_lock(job, name='launch.lock'):
        return launch_worker(profile, identifier, action, authorization=authorization)


def launch_worker(profile, identifier, action, *, authorization=None):
    from .release_worker import admit_operation
    from .release_operation import record_worker
    job, request = operation(profile, identifier)
    admit_operation(job, request, action, authorization=authorization)
    command = [request['runtime']['python'], '-B', str(job / 'worker/release_worker.py'), str(job), '--action', action]
    environment = {'HOME': request['account_home'], 'HERMES_HOME': request['profile'],
        'PATH': os.environ.get('PATH', os.defpath), 'PYTHONDONTWRITEBYTECODE': '1'}
    if read_private(job / 'plan.json')['services']:
        unit = 'lifeos-release-' + identifier
        launched = subprocess.run(['systemd-run', '--user', '--collect', '--unit=' + unit,
            *['--setenv=' + key + '=' + value for key, value in environment.items()], *command],
            text=True, capture_output=True, timeout=30)
        if launched.returncode:
            write_state(job, 'ready' if action == 'apply' else 'recovery_required',
                error='The detached release worker does not start.')
            raise ReleaseRejected('The owner service manager cannot start the release worker')
        publish(job / 'worker-launch.json', json.dumps({'kind': 'service', 'unit': unit}).encode())
    else:
        try:
            pid = spawn_worker(job, command, environment, request['account_home'])
        except OSError:
            write_state(job, 'ready' if action == 'apply' else 'recovery_required',
                error='The detached release worker does not start.')
            raise
        record_worker(job, pid)
    return {'identifier': identifier, 'state': 'queued', 'action': action}


def spawn_worker(job, command, environment, cwd):
    with (job / 'worker.stdout').open('ab') as stdout, (job / 'worker.stderr').open('ab') as stderr:
        os.fchmod(stdout.fileno(), 0o600); os.fchmod(stderr.fileno(), 0o600)
        process = subprocess.Popen(command, cwd=cwd, env=environment, stdin=subprocess.DEVNULL,
            stdout=stdout, stderr=stderr, start_new_session=True)
    Thread(target=process.wait, daemon=True).start()
    return process.pid


def run(args):
    from hermes_constants import get_hermes_home
    sys.dont_write_bytecode = True
    profile = get_hermes_home()
    try:
        if args.action == 'prepare':
            value = prepare(profile, args.version, name=args.name, assistant=args.assistant)
        elif args.action == 'status':
            value = status(profile, args.identifier)
        else:
            value = launch(profile, args.identifier, {'start': 'apply', 'recover': 'recover', 'rollback': 'restore'}[args.action])
    except PermissionError:
        value = {'status': 'rejected', 'message': 'The installation owner must approve native mounting in the authenticated release dashboard.'}
    except (ValueError, OSError, RuntimeError, KeyError, ImportError, subprocess.SubprocessError):
        value = {'status': 'rejected', 'message': 'The complete release operation is unavailable under this profile. Check its safe status and private preparation logs.'}
    print(json.dumps(value, indent=2))
    return 1 if value.get('status') == 'rejected' else 0
