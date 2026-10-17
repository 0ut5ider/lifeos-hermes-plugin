# ABOUTME: Applies, recovers, and restores an in-place LifeOS operation on the owner's Hermes installation.
# ABOUTME: Holds the Hermes update lock, stops every consumer, publishes host patches, and synchronizes dependencies.
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time

from .cli import read_private, write_state
from .inplace_services import inventory, replace_with_units
from .release_catalog import ReleaseRejected, _json
from .release_plan import inspect_operation, service_environment, verify_runtime
from .release_programs import ProgramTransaction, fingerprint, publish
from .release_operation import validate_plan
from .release_stage import run_stage, sha


CREATED_UNITS = {'gateway': 'hermes-gateway.service', 'dashboard': 'hermes-dashboard.service'}


def _systemctl(*arguments):
    result = subprocess.run(['systemctl', '--user', *arguments], capture_output=True, text=True, timeout=90)
    if result.returncode:
        raise ReleaseRejected('The owner service manager refuses ' + ' '.join(arguments[:1]))


def services_for(current, request, plan, installed, lease):
    roles = plan['services']['roles']
    if not roles:
        return None
    from .inplace_services import UNITS
    return current.memory_module('profile_services').ProfileServices(
        Path(request['profile']), installed, units={role: UNITS[role] for role in roles}, roles=roles,
        installation_lease=lease, first_installation=plan['fresh'])


def synchronize(job, request, *, label):
    """Commit the dependency generation for the current configuration under the host interpreter."""
    output = job / (label + '.json')
    output.unlink(missing_ok=True)
    source = request['host']['source']
    environment = {**service_environment(request), 'PYTHONPATH': source}
    run_stage([request['runtime']['python'], '-B', job / 'worker/dependency_plan.py', 'synchronize', source, output],
              job, label, environment=environment)
    return _json(output.read_bytes())


def _terminate(processes):
    for item in processes:
        try:
            os.kill(item['pid'], signal.SIGTERM)
        except ProcessLookupError:
            continue
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        if not any(Path('/proc', str(item['pid'])).exists() for item in processes):
            return
        time.sleep(0.2)
    raise ReleaseRejected('A hand-started Hermes process does not stop; close it and recover the operation')


def _consumers_stopped(request, plan):
    created = [role for role in plan['services']['created'] if role in CREATED_UNITS]
    _terminate(replace_with_units(plan['services']['consumers'], created))
    remaining = inventory(Path(request['host']['source']), Path(request['host']['state_directory']),
                          excluded_pids={os.getpid()})
    if remaining['consumers']:
        names = ', '.join(item['command'] + ' (' + str(item['pid']) + ')' for item in remaining['consumers'])
        raise ReleaseRejected('Hermes processes still use the installation: ' + names)


def _start_created(plan):
    for role in plan['services']['created']:
        if role in CREATED_UNITS:
            _systemctl('enable', '--now', CREATED_UNITS[role])


def _stop_created(plan):
    for role in plan['services']['created']:
        if role in CREATED_UNITS:
            subprocess.run(['systemctl', '--user', 'disable', '--now', CREATED_UNITS[role]],
                           capture_output=True, text=True, timeout=90)


def remove_preview(job):
    preview = job / 'hermes-preview'
    if preview.is_dir() and not preview.is_symlink():
        shutil.rmtree(preview)


def _rollback(job, request, plan, services, programs, restore_mount):
    """Return the host to its prior programs: mount, programs, dependencies, then services."""
    if services is not None:
        services.quiesce()
    _stop_created(plan)
    restore_mount()
    programs.restore()
    _systemctl('daemon-reload')
    try:
        synchronize(job, request, label='dependency-restore')
    except (ReleaseRejected, OSError, ValueError) as error:
        publish(job / 'dependency-restore-failure.json',
                (json.dumps({'error': type(error).__name__}) + '\n').encode())
    if services is not None:
        services.resume()


def run(job, request, action, current, lease, *, checkpoint=lambda point: None):
    """Execute the admitted action while this process holds the Hermes checkout and update locks."""
    from hermes_cli.update_lock import UpdateLock
    update = UpdateLock(install_root=Path(request['host']['source']))
    if not update.acquire():
        raise ReleaseRejected('A Hermes update is running; wait for it to finish, then recover the operation')
    try:
        return _run(job, request, action, current, lease, checkpoint=checkpoint)
    finally:
        update.release()


def _run(job, request, action, current, lease, *, checkpoint):
    from .release_worker import (_fresh_native, _restore_mount, _revoke, check_mount_recovery, check_restore,
                                 record_failure)
    profile = Path(request['profile'])
    plan = validate_plan(job, request)
    fresh_recovery = action == 'recover' and plan['fresh']
    if action == 'apply' or fresh_recovery:
        selected = inspect_operation(job, request, installation_lease=lease, fresh_recovery=fresh_recovery)
    else:
        if str(current.memory_module('lifeos_installation').selection(profile).installed) != request['installed']:
            raise ReleaseRejected('The recovery changes its selected native installation')
        selected = {'profile': profile, 'installed': Path(request['installed']), 'current': current,
                    'baseline': current.memory_module('version_drift').default_baseline_path(Path(request['installed']).parent)}
    services = services_for(current, request, plan, selected['installed'], lease)
    administration = current.memory_administration()
    environment = service_environment(request)
    if plan['native_mount_required']:
        environment = administration.mount_environment(selected['installed'], profile,
            request.get('memory_authorization'), binding=administration.job_binding(job, request, action))
        environment.update(PATH=service_environment(request)['PATH'])
    programs = ProgramTransaction(job / 'program-snapshot', expected_entries_sha256=plan['program_entries_sha256'])
    mount = current.memory_module('mount_transaction').MountTransaction(selected['installed'], profile, selected['baseline'])
    restore_mount = lambda: _restore_mount(job, request, mount)
    try:
        if action != 'apply' and not fresh_recovery:
            manifest = check_mount_recovery(job, request, mount)
            if action == 'restore':
                check_restore(job, request, plan, mount)
            else:
                overrides = {} if manifest is None or manifest['state'] == 'rolled_back' else {
                    entry['target']: fingerprint(entry['target']) for entry in manifest['entries']}
                programs.check_recovery(overrides=overrides)
            write_state(job, 'recovering' if action == 'recover' else 'restoring')
            _rollback(job, request, plan, services, programs, restore_mount)
            verify_runtime(request, restored=True)
            write_state(job, 'rolled_back')
            remove_preview(job)
            return {'state': 'rolled_back'}
        if not fresh_recovery and sha(profile / 'config.yaml') != request['configuration_sha256']:
            raise ReleaseRejected('The profile configuration changes before program selection')
        if not fresh_recovery:
            from .release_worker import _program_plan
            directories, files, dependencies = _program_plan(job, request, selected)
            programs.check_plan(directories=directories, files=files, dependencies=dependencies)
            programs.check_prepared()
        write_state(job, 'recovering' if fresh_recovery else 'applying')
        native_started = fresh_recovery
        try:
            if services is not None:
                if fresh_recovery and services.status()['state'] != 'none':
                    services.quiesce()
                else:
                    services.drain(signature=plan['services']['signature'])
                services.verify_stopped()
            if not fresh_recovery:
                _consumers_stopped(request, plan)
            if fresh_recovery:
                _restore_mount(job, request, mount)
            for entry in programs._load()['entries']:
                Path(entry['target']).parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            if selected['fresh']:
                native_started = True
                _fresh_native(job, request, selected, checkpoint=checkpoint)
            if fresh_recovery:
                programs.resume(checkpoint=checkpoint)
            else:
                programs.apply(checkpoint=checkpoint)
            checkpoint('programs-published')
            _systemctl('daemon-reload')
            synchronized = synchronize(job, request, label='dependency-synchronization')
            if synchronized['lock_sha256'] != request['dependencies']['lock_sha256']:
                raise ReleaseRejected('The synchronized dependencies differ from the reviewed resolution')
            checkpoint('dependencies-synchronized')
            if plan['native_mount_required']:
                import importlib
                mounted_module = importlib.reload(current.memory_module('mount_transaction'))
                mount = mounted_module.MountTransaction(selected['installed'], profile, selected['baseline'])
                drift = current.memory_module('version_drift')
                baseline = drift.create_baseline(selected['native'], selected['installed'])
                prior = sha(mount.journal) if mount.journal.is_file() else None
                publish(job / 'mount-intent.json', (json.dumps({'prior_journal_sha256': prior, 'action': action}) + '\n').encode())
                mount.execute(environment, request['runtime']['bun'], request['runtime']['hermes'],
                    baseline_data=(json.dumps(baseline) + '\n').encode(),
                    binding=administration.job_binding(job, request, action), retain_for_rollback=True)
            checkpoint('native-mounted')
            verify_runtime(request)
            if services is not None:
                services.resume()
            _start_created(plan)
            write_state(job, 'applied')
            remove_preview(job)
            return {'state': 'applied'}
        except BaseException as error:
            record_failure(job, error)
            if selected['fresh'] and native_started:
                if services is not None:
                    services.quiesce()
                _stop_created(plan)
                _restore_mount(job, request, mount)
                write_state(job, 'recovery_required',
                            error='The first installation stopped after LifeOS was initialized. Recover it to finish.')
                raise
            _rollback(job, request, plan, services, programs, lambda: _restore_mount(job, request, mount))
            write_state(job, 'rolled_back')
            raise
    finally:
        _revoke(administration, profile, request)
