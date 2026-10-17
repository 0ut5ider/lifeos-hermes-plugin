# ABOUTME: Starts owner-requested release preparation in a detached process with a private profile lock.
# ABOUTME: Validates bounded UI selections and retains preparation status without selecting active programs.
from __future__ import annotations

import fcntl
from contextlib import contextmanager
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
from threading import Thread
import types
from uuid import uuid4

if not __package__:
    namespace = types.ModuleType('lifeos_release_preparation')
    namespace.__path__ = [str(Path(__file__).resolve().parent)]
    sys.modules[namespace.__name__] = namespace
    __package__ = namespace.__name__

from .cli import job_directory, prepare, profile_directory, read_private, status, write_state
from .release_catalog import ReleaseRejected, VERSION
from .release_accounts import account_home
from .release_operation import OperationBusy, process_stamp
from .release_programs import publish
from .release_services import FirstInstallationUnavailable


def selection(value):
    if not isinstance(value, dict) or set(value) - {'intent', 'version', 'name', 'assistant'}:
        raise ReleaseRejected('Choose the installation or update action and optional release version')
    if not isinstance(value.get('intent'), str) or value['intent'] not in {'install', 'update', 'plugin'}:
        raise ReleaseRejected('Choose Install LifeOS, Update LifeOS, or Update plugin')
    version = value.get('version')
    if version is not None and (not isinstance(version, str) or VERSION.fullmatch(version) is None):
        raise ReleaseRejected('Choose an exact integration version or the latest stable release')
    names = {key: value.get(key, default) for key, default in (('name', 'User'), ('assistant', 'Hermes'))}
    for name in names.values():
        if not isinstance(name, str) or not name.strip() or len(name) > 100 or any(ord(c) < 32 for c in name):
            raise ReleaseRejected('Fresh installation names require bounded text')
    return {'intent': value['intent'], 'version': version,
            **{key: name.strip() for key, name in names.items()}}


@contextmanager
def preparation_admission(profile, intent=None):
    profile = profile_directory(profile)
    marker=profile/'.lifeos-removal.json'
    if marker.exists() or marker.is_symlink():
        from .removal_workflow import retire_verified_removal
        if intent != 'install' or not retire_verified_removal(profile):
            raise ReleaseRejected('Recover or roll back the selected software removal before release preparation')
    state = profile / '.lifeos-releases'
    state.mkdir(mode=0o700, exist_ok=True)
    info = state.lstat()
    if state.resolve() != state or not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise ReleaseRejected('Release staging requires private owner storage')
    descriptor = os.open(state / 'preparation.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise ReleaseRejected('Preparation requires a private owner lock')
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise OperationBusy('A release preparation is already running') from error
        for operation in status(profile)['operations']:
            phase = operation['state']
            if phase == 'preparing':
                worker_file = state / operation['identifier'] / 'preparation-worker.json'
                if worker_file.exists():
                    worker = read_private(worker_file)
                    stamp = process_stamp(worker['pid'])
                    if stamp is not None and stamp == worker['start_time']:
                        raise OperationBusy('A release preparation is already running')
            if phase.startswith('queued-') or phase in {'applying', 'recovering', 'restoring', 'recovery_required'}:
                raise OperationBusy('Finish the release operation or recovery before another preparation')
        yield descriptor
    finally:
        os.close(descriptor)


def queue(profile, value):
    value = selection(value)
    profile = profile_directory(profile)
    home = account_home(profile)
    state = profile / '.lifeos-releases'
    with preparation_admission(profile, value['intent']) as descriptor:
        job = state / uuid4().hex
        job.mkdir(mode=0o700)
        write_state(job, 'preparing')
        publish(job / 'preparation.json', (json.dumps(value) + '\n').encode())
        environment = dict(os.environ, HOME=str(home), HERMES_HOME=str(profile), PYTHONDONTWRITEBYTECODE='1')
        with (job / 'preparation.stdout').open('ab') as stdout, (job / 'preparation.stderr').open('ab') as stderr:
            os.fchmod(stdout.fileno(), 0o600)
            os.fchmod(stderr.fileno(), 0o600)
            try:
                process = subprocess.Popen([sys.executable, '-B', str(Path(__file__).resolve()), str(profile), job.name],
                    env=environment, cwd=home, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr,
                    start_new_session=True, pass_fds=(descriptor,))
            except OSError:
                write_state(job, 'preparation_failed', error='The preparation process does not start.')
                raise
        Thread(target=process.wait, daemon=True).start()
        publish(job / 'preparation-worker.json', json.dumps({'pid': process.pid,
                'start_time': process_stamp(process.pid)}).encode())
        return {'identifier': job.name, 'state': 'preparing', 'active_unchanged': True}


def main():
    profile = profile_directory(sys.argv[1])
    job = job_directory(profile, sys.argv[2])
    try:
        value = selection(read_private(job / 'preparation.json'))
        prepare(profile, value['version'], name=value['name'], assistant=value['assistant'],
                intent=value['intent'], job=job)
    except FirstInstallationUnavailable as error:
        write_state(job, 'preparation_failed', error=str(error))
        raise
    except BaseException:
        write_state(job, 'preparation_failed', error='Preparation did not change the active installation.')
        raise


if __name__ == '__main__':
    os.umask(0o077)
    main()
