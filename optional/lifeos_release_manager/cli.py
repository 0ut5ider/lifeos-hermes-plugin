# ABOUTME: Prepares and starts complete qualified integration releases through Hermes commands.
# ABOUTME: Reports private operation state and keeps management separate from the active bridge.
from __future__ import annotations

import argparse
import fcntl
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

from .release_catalog import ReleaseCatalog, ReleaseRejected, extract_package, parse_json
from .release_accounts import account_home
from .release_programs import publish
from .release_stage import (load_bridge, prepare_runtime, sha, validate_package, runtime_source_fingerprint,
                            validate_files, run_stage, stage_environment, user_runtime_directory)

IDENTIFIER = re.compile('[0-9a-f]{32}')


def configure(parser: argparse.ArgumentParser):
    actions = parser.add_subparsers(dest='action', required=True)
    prepare = actions.add_parser('prepare', help='Download and prepare the complete release before any live change.')
    prepare.add_argument('--version', dest='release_version', help='Select an exact published integration version instead of the latest stable release.')
    prepare.add_argument('--name', default='User', help='Set the name only for a fresh native installation.')
    prepare.add_argument('--assistant', default='Hermes', help='Set the assistant name only for a fresh native installation.')
    actions.add_parser('compatibility', help='Check, without changes, whether LifeOS can patch this Hermes installation.')
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
        return parse_json(stream.read(limit + 1))


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


def prepare(profile, version=None, *, name='User', assistant='Hermes', catalog=None, job=None, intent=None):
    profile = profile_directory(profile)
    account_home(profile)
    for value in (name, assistant):
        if not isinstance(value, str) or not value.strip() or len(value) > 100 or any(ord(c) < 32 for c in value):
            raise ReleaseRejected('Fresh installation names require bounded text')
    if job is None:
        from .release_preparation import preparation_admission
        with preparation_admission(profile):
            return _prepare(profile, version, name=name, assistant=assistant, catalog=catalog, intent=intent)
    return _prepare(profile, version, name=name, assistant=assistant, catalog=catalog, job=job, intent=intent)


def _prepare(profile, version=None, *, name, assistant, catalog=None, job=None, intent=None):
    home = account_home(profile)
    state = profile / '.lifeos-releases'
    state.mkdir(mode=0o700, exist_ok=True)
    if state.resolve() != state or state.stat().st_uid != os.getuid() or state.stat().st_mode & 0o077:
        raise ReleaseRejected('Release staging requires private profile storage')
    if job is None:
        job = state / uuid4().hex
        job.mkdir(mode=0o700)
        from .release_operation import process_stamp
        publish(job / 'preparation-worker.json', json.dumps({'pid': os.getpid(),
            'start_time': process_stamp(os.getpid())}).encode())
        write_state(job, 'preparing')
    else:
        job = job_directory(profile, Path(job).name)
        if read_private(job / 'status.json')['state'] != 'preparing' or (job / 'request.json').exists():
            raise ReleaseRejected('The preparation already starts or completes')
    try:
        return _prepare_inplace_operation(profile, job, version, name=name, assistant=assistant,
                                          catalog=catalog, intent=intent)
    except BaseException as error:
        write_state(job, 'preparation_failed', error=_preparation_error(job, error))
        raise


def owner_message(error):
    """Return the text of a release refusal or a LifeOS service refusal, written for the owner; None otherwise."""
    # Each loaded bridge has its own memory_access module, so the refusal class is matched by its name.
    if isinstance(error, ReleaseRejected) or any(kind.__name__ == 'MemoryUnavailable' and kind.__module__.endswith('.memory_access')
                                                 for kind in type(error).__mro__):
        return str(error)
    return None


def _preparation_error(job, error):
    """Return the owner-facing reason for a failed preparation; refusals explain themselves."""
    reason = owner_message(error)
    if reason is not None and reason.startswith('Release preparation fails at '):
        reason = None
    if reason is None and (job / 'worker-failure.json').is_file():
        try:
            reason = read_private(job / 'worker-failure.json').get('message')
        except (ValueError, OSError):
            reason = None
    unchanged = 'Preparation did not change the active installation.'
    return unchanged if not reason else reason + ' ' + unchanged


def _prepare_managed_package(profile, home, job, version, *, name, assistant, catalog=None, intent=None):
    """Prepare a format 1 release that publishes a complete managed runtime beside the profile."""
    downloaded = (catalog or ReleaseCatalog()).download(job / 'download', version)
    package = job / 'package'
    extract_package(downloaded['archive'], package)
    manifest = validate_package(package, downloaded['certificate'])
    source = load_bridge(package / 'lifeos_hook_bridge')
    names = source.memory_module('fresh_store')
    names._name(name.strip())
    names._name(assistant.strip())
    selected = source.memory_module('lifeos_installation').selection(profile)
    if not selected.installed.exists():
        from .release_services import require_fresh_services
        require_fresh_services(source)
    if intent == 'install' and (selected.installed.exists() or selected.installed.is_symlink()):
        raise ReleaseRejected('Use an update for the existing LifeOS installation')
    if intent in {'update', 'plugin'} and not selected.installed.is_dir():
        raise ReleaseRejected('Install LifeOS before requesting an update')
    runtime = prepare_runtime(job, package, Path(downloaded['dashboard']), profile)
    request = {'format': 1, 'identifier': job.name, 'profile': str(profile),
        'account_home': str(home), 'installed': str(selected.installed),
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
    return _ready_operation(job, request, manifest['manager_files'])


def _prepare_inplace_operation(profile, job, version, *, name, assistant, catalog=None, intent=None):
    from .inplace_preparation import prepare_inplace
    request, manifest = prepare_inplace(profile, job, version, name=name.strip(), assistant=assistant.strip(),
                                        intent=intent, catalog=catalog)
    return _ready_operation(job, request, manifest['manager_files'])


def _ready_operation(job, request, files):
    """Run the candidate program review of a prepared request and return the ready operation for the owner."""
    prepare_plan(job, request, files)
    if read_private(job / 'status.json')['state'] != 'ready':
        raise ReleaseRejected('The candidate does not complete its program review')
    return {'identifier': job.name, 'state': 'ready', 'version': request['version'],
        'commit': request['commit'], 'package_sha256': request['package_sha256'], 'active_unchanged': True,
        'next': 'Use the release dashboard to review the operation, or run hermes lifeos-release start ' + job.name}


def prepare_plan(job, request, files):
    validate_files(job / 'worker', files, forbid_bytecode=True)
    environment = stage_environment(Path(request['profile']), home=Path(request['account_home']),
                               source=Path(request['runtime']['source']))
    environment.update(XDG_RUNTIME_DIR=user_runtime_directory(),
                       DBUS_SESSION_BUS_ADDRESS='unix:path=' + user_runtime_directory() + '/bus')
    run_stage([request['runtime']['python'], '-B', job / 'worker/release_worker.py', job,
               '--action', 'prepare'], job, 'candidate-review', environment=environment)


def preparation_status(job, value):
    if value['state'] == 'preparing':
        from .release_operation import process_stamp
        if (job / 'preparation-worker.json').exists():
            worker = read_private(job / 'preparation-worker.json')
            if set(worker) != {'pid', 'start_time'}:
                raise ReleaseRejected('The preparation worker identity changes')
            stamp = process_stamp(worker['pid'])
            if stamp is not None and stamp == worker['start_time']:
                return value
        # The parent holds this lease before spawning; the detached child inherits it.
        try:
            descriptor = os.open(job.parent / 'preparation.lock', os.O_RDWR | os.O_NOFOLLOW)
        except FileNotFoundError:
            descriptor = None
        if descriptor is not None:
            try:
                info = os.fstat(descriptor)
                if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
                    raise ReleaseRejected('Preparation requires a private owner lock')
                try:
                    fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    return value
            finally:
                os.close(descriptor)
        return {**value, 'state': 'preparation_interrupted',
                'error': 'Preparation stops before a ready plan. Prepare another release. Active programs stay in place.'}
    return value


def status(profile, identifier=None):
    profile = profile_directory(profile)
    state = profile / '.lifeos-releases'
    if identifier is not None:
        job = job_directory(profile, identifier)
        if not (job / 'request.json').exists():
            if not (job / 'status.json').exists() and not (job / 'status.json').is_symlink() and not (job / 'plan.json').exists():
                return preparation_status(job, {'identifier': job.name, 'state': 'preparing'})
            return preparation_status(job, read_private(job / 'status.json'))
        job, request = operation(profile, identifier)
        value = {**preparation_status(job, read_private(job / 'status.json')), 'version': request['version'], 'commit': request['commit'],
                 'restore_available': False, 'recover_available': False}
        if (job / 'plan.json').exists():
            from .release_operation import validate_plan, operation_lock, OperationBusy, worker_running
            plan = validate_plan(job, request)
            if value['state'] == 'applied':
                from .release_worker import restore_available
                value['restore_available'] = restore_available(job, request, plan)
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
    from .release_worker import validate_operation_package
    manifest = validate_operation_package(job, request)
    validate_files(job / 'worker', manifest['manager_files'], forbid_bytecode=True)
    admit_operation(job, request, action, authorization=authorization)
    python = request['runtime']['python']
    if request.get('format') == 2:
        from .inplace_preparation import host_python
        python = str(host_python(request['host']['source']))
    command = [python, '-B', str(job / 'worker/release_worker.py'), str(job), '--action', action]
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
            value = prepare(profile, args.release_version, name=args.name, assistant=args.assistant)
        elif args.action == 'compatibility':
            from .host_compatibility import check
            value = check(profile)
            print(json.dumps(value, indent=2))
            return 0 if value['compatible'] or value['installed'] else 1
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
