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


DEPENDENCY_RESTORE_ERROR = ('The programs are restored, but Hermes could not rebuild its Python environment. '
                            'Run hermes pm install to rebuild it.')
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
    from .inplace_preparation import host_python
    run_stage([host_python(source), '-B', job / 'worker/dependency_plan.py', 'synchronize', source, output],
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
    # The command that launched this worker exits right after the launch; give it a moment to finish.
    deadline = time.monotonic() + 15
    while True:
        remaining = inventory(Path(request['host']['source']), Path(request['host']['state_directory']),
                              excluded_pids={os.getpid()})
        if not remaining['consumers'] or time.monotonic() > deadline:
            break
        time.sleep(0.5)
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


def verify_registration(request, plan):
    """Require the restarted gateway's main process to register the installed bridge in patched mode."""
    if 'gateway' not in plan['services']['roles'] and 'gateway' not in plan['services']['created']:
        return None
    from .release_stage import load_bridge
    profile = Path(request['profile'])
    registration = load_bridge(profile / 'plugins/lifeos-hook-bridge').memory_module('registration')
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        result = subprocess.run(['systemctl', '--user', 'show', 'hermes-gateway.service', '--property=MainPID,ActiveState'],
                                capture_output=True, text=True, timeout=45)
        values = dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)
        if values.get('ActiveState') not in {'active', 'activating'}:
            if values.get('ActiveState') == 'inactive' and not _gateway_expected(plan):
                return None
            raise ReleaseRejected('The gateway does not run after the operation')
        receipt = registration.read_receipt(profile, int(values.get('MainPID') or 0))
        if receipt is not None:
            if receipt['mode'] != 'patched':
                raise ReleaseRejected('The restarted gateway loaded the bridge without the patched host hooks')
            return receipt
        time.sleep(1)
    raise ReleaseRejected('The restarted gateway did not register the bridge')


OWNED_PLUGINS = ('lifeos', 'lifeos-hook-bridge', 'lifeos-release-manager')


def _tree_digest(root):
    import hashlib
    digest = hashlib.sha256()
    for path in sorted(Path(root).rglob('*')):
        if '__pycache__' in path.parts or path.suffix == '.pyc':
            continue
        digest.update(path.relative_to(root).as_posix().encode() + b'\0')
        if path.is_symlink():
            digest.update(b'link\0' + os.readlink(path).encode())
        elif path.is_file():
            digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def inventory_snapshot(request):
    """Record the other plugins, their enablement, and the locked packages that the operation must keep."""
    from ruamel.yaml import YAML
    from .dependency_plan import locked_packages, selected_lock
    profile = Path(request['profile'])
    plugins = profile / 'plugins'
    directories = {path.name: _tree_digest(path) for path in sorted(plugins.iterdir())
                   if path.name not in OWNED_PLUGINS and path.is_dir()} if plugins.is_dir() else {}
    configuration = YAML(typ='safe').load((profile / 'config.yaml').read_text()) or {}
    selected = (configuration.get('plugins') or {}) if isinstance(configuration, dict) else {}
    enabled = sorted(name for name in selected.get('enabled') or [] if name not in OWNED_PLUGINS)
    return {'plugins': directories, 'enabled': enabled,
            'packages': locked_packages(selected_lock(Path(request['host']['source'])))}


def check_inventory(before, after, added):
    """Refuse when the operation changed another plugin, its enablement, or an existing package version."""
    if before['plugins'] != after['plugins'] or before['enabled'] != after['enabled']:
        raise ReleaseRejected('The operation changed another Hermes plugin or its enablement')
    changed = [name for name, versions in before['packages'].items() if after['packages'].get(name) != versions]
    unexpected = sorted(set(after['packages']) - set(before['packages']) - set(added))
    if changed or unexpected:
        raise ReleaseRejected('The operation changed Python packages outside the review: ' + ', '.join(changed + unexpected))


def _gateway_expected(plan):
    """The gateway must run afterwards when it ran before the operation or the operation created its unit."""
    return 'gateway' in plan['services']['created'] or plan['services']['active'].get('gateway', False)


def clear_bytecode(request, plan_files):
    """Remove cached bytecode of the changed Hermes modules so no process can load a stale compiled copy."""
    source = Path(request['host']['source'])
    for target in plan_files:
        target = Path(target)
        if target.suffix != '.py' or not target.is_relative_to(source):
            continue
        cache = target.parent / '__pycache__'
        if cache.is_dir() and not cache.is_symlink():
            for compiled in cache.glob(target.stem + '.*.pyc'):
                compiled.unlink(missing_ok=True)


def remove_preview(job):
    preview = job / 'hermes-preview'
    if preview.is_dir() and not preview.is_symlink():
        shutil.rmtree(preview)


def _quiesce(services):
    """Stop the bound services again when an earlier drain published its journal; otherwise nothing stopped."""
    if services is not None and services.status()['state'] != 'none':
        services.quiesce()


def _resume(services):
    if services is not None and services.status()['state'] != 'none':
        services.resume()


def _rollback(job, request, plan, services, programs, restore_mount):
    """Return the host to its prior programs: mount, programs, dependencies, then services."""
    _quiesce(services)
    _stop_created(plan)
    restore_mount()
    programs.restore()
    _systemctl('daemon-reload')
    try:
        synchronize(job, request, label='dependency-restore')
    except (ReleaseRejected, OSError, ValueError) as error:
        publish(job / 'dependency-restore-failure.json',
                (json.dumps({'error': type(error).__name__}) + '\n').encode())
        restored_dependencies = False
    else:
        restored_dependencies = True
    _resume(services)
    return restored_dependencies


def run(job, request, action, current, lease, *, checkpoint=lambda point: None):
    """Execute the admitted action while this process holds the Hermes checkout and update locks."""
    from hermes_cli.update_lock import UpdateLock
    update = UpdateLock(install_root=Path(request['host']['source']))
    if not update.acquire():
        raise ReleaseRejected('A Hermes update is running; wait for it to finish, then recover the operation')
    try:
        return _run(job, request, action, current, lease, checkpoint=checkpoint, release_update=update.release)
    finally:
        update.release()


def _run(job, request, action, current, lease, *, checkpoint, release_update=lambda: None):
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
            _quiesce(services)
            _consumers_stopped(request, {**plan, 'services': {**plan['services'], 'consumers': [], 'created': []}})
            restored_dependencies = _rollback(job, request, plan, services, programs, restore_mount)
            verify_runtime(request, restored=True)
            from .host_configuration import RECORD, record
            if (profile / RECORD).exists():
                current = (profile / 'config.yaml').read_bytes()
                record(profile, current, current)
            write_state(job, 'rolled_back', error=None if restored_dependencies else DEPENDENCY_RESTORE_ERROR)
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
        configuration_before = (profile / 'config.yaml').read_bytes()
        inventory_before = inventory_snapshot(request)
        try:
            if services is not None:
                if fresh_recovery and services.status()['state'] != 'none':
                    services.quiesce()
                else:
                    services.drain(signature=plan['services']['signature'])
                services.verify_stopped()
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
            clear_bytecode(request, [entry['target'] for entry in programs._load()['entries']])
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
            from .host_configuration import check_preserved, record
            configuration_after = (profile / 'config.yaml').read_bytes()
            check_preserved(configuration_before, configuration_after)
            check_inventory(inventory_before, inventory_snapshot(request), request['dependencies']['added'])
            verify_runtime(request)
            # Restarted Hermes processes refuse to boot under a live update marker; the checkout is complete.
            release_update()
            if services is not None:
                services.resume()
            _start_created(plan)
            receipt = verify_registration(request, plan)
            publish(job / 'registration.json', (json.dumps(receipt) + '\n').encode())
            record(profile, configuration_before, configuration_after)
            write_state(job, 'applied')
            remove_preview(job)
            return {'state': 'applied'}
        except BaseException as error:
            record_failure(job, error)
            if selected['fresh'] and native_started:
                _quiesce(services)
                _stop_created(plan)
                _restore_mount(job, request, mount)
                write_state(job, 'recovery_required',
                            error='The first installation stopped after LifeOS was initialized. Recover it to finish.')
                raise
            restored = _rollback(job, request, plan, services, programs, lambda: _restore_mount(job, request, mount))
            write_state(job, 'rolled_back', error=None if restored else DEPENDENCY_RESTORE_ERROR)
            raise
    finally:
        _revoke(administration, profile, request)
