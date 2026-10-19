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

from .cli import write_state
from .inplace_services import OFFERABLE, UNITS, inventory, replace_with_units, show
from .release_catalog import ReleaseRejected, parse_json
from .release_plan import inspect_operation, service_environment, verify_runtime
from .release_programs import ProgramTransaction, fingerprint, publish
from .release_operation import validate_plan
from .release_stage import run_stage, sha
from .removal_configuration import PLUGINS as OWNED_PLUGINS


DEPENDENCY_RESTORE_ERROR = ('The programs are restored, but Hermes could not rebuild its Python environment. '
                            'Run hermes pm install to rebuild it.')
# The standard units that an operation may create for a hand-started gateway or dashboard.
CREATED_UNITS = {role: UNITS[role] for role in OFFERABLE}


def _systemctl(*arguments):
    result = subprocess.run(['systemctl', '--user', *arguments], capture_output=True, text=True, timeout=90)
    if result.returncode:
        raise ReleaseRejected('The owner service manager refuses ' + ' '.join(arguments[:1]))


def services_for(job, request, plan, installed, lease):
    """Bind the reviewed service roles with the operation's own validated bridge."""
    roles = plan['services']['roles']
    if not roles:
        return None
    from .release_stage import load_bridge
    return load_bridge(job / 'package/lifeos_hook_bridge').memory_module('profile_services').ProfileServices(
        Path(request['profile']), installed, units={role: UNITS[role] for role in roles}, roles=roles,
        installation_lease=lease, first_installation=plan['fresh'])


def synchronize_source(job, source, environment, *, label, failure=None):
    """Commit the dependency generation for the current configuration of ``source`` under its interpreter.

    The stage output goes to ``job`` under ``label``. ``failure`` replaces the release-preparation refusal.
    """
    output = job / (label + '.json')
    output.unlink(missing_ok=True)
    from .inplace_preparation import host_python
    try:
        run_stage([host_python(source), '-B', Path(__file__).with_name('dependency_plan.py'), 'synchronize', source,
                   output], job, label, environment={**environment, 'PYTHONPATH': source})
    except ReleaseRejected:
        if failure is None:
            raise
        raise ReleaseRejected(failure) from None
    return parse_json(output.read_bytes())


def synchronize(job, request, *, label):
    """Commit the dependency generation for the current configuration under the host interpreter."""
    return synchronize_source(job, request['host']['source'], service_environment(request), label=label)


def host_synchronizer(profile, job, *, label):
    """Return a callable that synchronizes an in-place host's dependencies, or None for another installation.

    A provider return changes which plugins Hermes enables. Synchronizing before the services restart keeps
    Hermes from finishing the environment itself at gateway launch, under the update lock.
    """
    from .host_record import load_record
    from .release_accounts import account_home
    from .release_stage import user_runtime_directory
    record = load_record(profile)
    if record is None:
        return None
    environment = dict(os.environ, HOME=str(account_home(profile)), HERMES_HOME=str(profile),
                       XDG_RUNTIME_DIR=user_runtime_directory(),
                       DBUS_SESSION_BUS_ADDRESS='unix:path=' + user_runtime_directory() + '/bus',
                       PYTHONDONTWRITEBYTECODE='1')
    return lambda: synchronize_source(job, record['source'], environment, label=label,
                                      failure='The Hermes dependencies cannot synchronize, so the Hermes services stay '
                                              'stopped. Recover the memory workflow, or restore the previous provider settings.')


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
    raise ReleaseRejected('A hand-started Hermes process does not stop; close it, then prepare the operation again')


def check_reviewed_services(reviewed, current):
    """Refuse an apply whose services differ from the reviewed plan before any service stops.

    The worker stops, creates, and replaces exactly what the owner reviewed; a host that changed since,
    or a plan sealed by another process that saw different consumers, refuses here instead of rolling back.
    """
    def identity(value):
        if value is None:
            return None
        return (sorted(value['roles']), sorted(value['created']),
                sorted((item['pid'], item['start_time'], item['role']) for item in value['consumers']))
    if identity(reviewed) != identity(current):
        raise ReleaseRejected('The Hermes services changed after review; prepare the operation again')


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
        from .consumer_scan import process_names
        raise ReleaseRejected('Hermes processes still use the installation: ' + process_names(remaining['consumers']))


def _start_created(plan):
    for role in plan['services']['created']:
        if role in CREATED_UNITS:
            _systemctl('enable', '--now', CREATED_UNITS[role])


def _stop_created(plan):
    for role in plan['services']['created']:
        if role in CREATED_UNITS:
            subprocess.run(['systemctl', '--user', 'disable', '--now', CREATED_UNITS[role]],
                           capture_output=True, text=True, timeout=90)


def verify_registration(request, plan, *, unit=CREATED_UNITS['gateway']):
    """Require the restarted gateway's main process to register the installed bridge in patched mode."""
    if 'gateway' not in plan['services']['roles'] and 'gateway' not in plan['services']['created']:
        return None
    from .release_stage import load_bridge
    profile = Path(request['profile'])
    registration = load_bridge(profile / 'plugins/lifeos-hook-bridge').memory_module('registration')
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        result = subprocess.run(['systemctl', '--user', 'show', unit, '--property=MainPID,ActiveState'],
                                capture_output=True, text=True, timeout=45)
        values = dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)
        if values.get('ActiveState') not in {'active', 'activating'}:
            if values.get('ActiveState') == 'inactive' and not _gateway_expected(plan):
                return None
            raise ReleaseRejected('The gateway does not run after the operation')
        receipt = registration.read_receipt(profile, int(values.get('MainPID') or 0))
        if receipt is not None:
            return check_receipt(receipt, request)
        time.sleep(1)
    raise ReleaseRejected('The restarted gateway did not register the bridge')


def check_receipt(receipt, request):
    """Require a patched registration from the installed Hermes checkout, not from another runtime."""
    if receipt['mode'] != 'patched':
        raise ReleaseRejected('The restarted gateway loaded the bridge without the patched host hooks')
    if receipt.get('source') != str(Path(request['host']['source']).resolve()):
        raise ReleaseRejected('The restarted gateway runs another Hermes checkout than the installation')
    return receipt


def boot_ticks():
    """Return the time since boot in the clock ticks that ``/proc/<pid>/stat`` uses for process start times."""
    return int(time.clock_gettime(time.CLOCK_BOOTTIME) * os.sysconf('SC_CLK_TCK'))


def check_restarted(units, drained):
    """Require each restarted unit to be active with a main process that started after the drain."""
    from .consumer_scan import start_time
    for unit in units:
        values = show(unit, 'MainPID', 'ActiveState')
        pid = int(values.get('MainPID') or 0)
        try:
            started = start_time(pid) if pid else None
        except (FileNotFoundError, ProcessLookupError):
            started = None
        if values.get('ActiveState') != 'active' or started is None or started <= drained:
            raise ReleaseRejected('The ' + unit + ' service does not run a new main process after the operation')


def check_enabled(recorded):
    """Require each bound unit to keep the enablement (``UnitFileState``) recorded at review."""
    for unit, state in recorded.items():
        if show(unit, 'UnitFileState').get('UnitFileState') != state:
            raise ReleaseRejected('The operation changed whether ' + unit + ' starts with your account')


def verify_restart(request, plan, entry, started, drained, configuration_before, *, fresh, python, units=None):
    """Verify the restarted host: new main processes, kept enablement, host capabilities, and the memory provider.

    ``started`` names the bound roles that the service controller restarted; created units started too.
    The capability probe runs ``python`` against the installed source in a fresh process.
    """
    from .host_capabilities import probe_capabilities
    from .host_configuration import check_memory_provider
    units = UNITS if units is None else units
    created = [role for role in plan['services']['created'] if role in CREATED_UNITS]
    check_restarted([units[role] for role in [*started, *created]], drained)
    check_enabled({units[role]: state for role, state in plan['services']['enabled'].items()})
    probe_capabilities(python, request['host']['source'], entry, environment=service_environment(request))
    check_memory_provider(configuration_before, (Path(request['profile']) / 'config.yaml').read_bytes(), owned=fresh)


def _journaled(services):
    """True when the operation binds services and their drain journal exists, so they were stopped."""
    return services is not None and services.status()['state'] != 'none'


def adopt_units(services, request):
    """Bind each stopped transition role to whichever reviewed unit file is on disk, managed or stock."""
    units = request['host'].get('transition_units') or {}
    if not units or not _journaled(services):
        return
    # A replaced unit file reports NeedDaemonReload until the manager reloads, and inspection refuses that state.
    _systemctl('daemon-reload')
    for role, hashes in units.items():
        if role in services.units:
            services.adopt_definition(role, {hashes['before'], hashes['after']})


def _tree_digest(root):
    import hashlib
    from .integration_package import source_paths
    digest = hashlib.sha256()
    for path in source_paths(root):
        digest.update(path.relative_to(root).as_posix().encode() + b'\0')
        if path.is_symlink():
            digest.update(b'link\0' + os.readlink(path).encode())
        elif path.is_file():
            digest.update(bytes.fromhex(sha(path)))
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
    if _journaled(services):
        services.quiesce()


def _resume(services):
    if _journaled(services):
        services.resume()


def _rollback(job, request, plan, services, programs, restore_mount, *, release_update):
    """Return the host to its prior programs: mount, programs, dependencies, then services."""
    adopt_units(services, request)
    _quiesce(services)
    _stop_created(plan)
    restore_mount()
    programs.restore()
    _systemctl('daemon-reload')
    adopt_units(services, request)
    try:
        synchronize(job, request, label='dependency-restore')
    except (ReleaseRejected, OSError, ValueError) as error:
        publish(job / 'dependency-restore-failure.json',
                (json.dumps({'error': type(error).__name__}) + '\n').encode())
        restored_dependencies = False
    else:
        restored_dependencies = True
    # Restarted Hermes processes refuse to boot under a live update marker; the checkout is complete.
    release_update()
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


def _run(job, request, action, current, lease, *, checkpoint, release_update):
    from .release_worker import (initialize_native, restore_native_mount, revoke_authorization, check_mount_recovery, check_restore,
                                 record_failure)
    profile = Path(request['profile'])
    plan = validate_plan(job, request)
    fresh_recovery = action == 'recover' and plan['fresh']
    if action == 'apply' or fresh_recovery:
        selected = inspect_operation(job, request, installation_lease=lease, fresh_recovery=fresh_recovery)
        if action == 'apply':
            check_reviewed_services(plan['services'], selected['services'])
    else:
        if str(current.memory_module('lifeos_installation').selection(profile).installed) != request['installed']:
            raise ReleaseRejected('The recovery changes its selected native installation')
        selected = {'profile': profile, 'installed': Path(request['installed']), 'current': current,
                    'baseline': current.memory_module('version_drift').default_baseline_path(Path(request['installed']).parent)}
    services = services_for(job, request, plan, selected['installed'], lease)
    administration = current.memory_administration()
    environment = service_environment(request)
    if plan['native_mount_required']:
        environment = administration.mount_environment(selected['installed'], profile,
            request.get('memory_authorization'), binding=administration.job_binding(job, request, action))
        environment.update(PATH=service_environment(request)['PATH'])
    programs = ProgramTransaction(job / 'program-snapshot', expected_entries_sha256=plan['program_entries_sha256'])
    mount = current.memory_module('mount_transaction').MountTransaction(selected['installed'], profile, selected['baseline'])
    restore_mount = lambda: restore_native_mount(job, request, mount)
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
            adopt_units(services, request)
            _quiesce(services)
            _consumers_stopped(request, {**plan, 'services': {**plan['services'], 'consumers': [], 'created': []}})
            restored_dependencies = _rollback(job, request, plan, services, programs, restore_mount,
                                              release_update=release_update)
            verify_runtime(request, restored=True)
            from .host_configuration import record_restored
            record_restored(profile)
            write_state(job, 'rolled_back', error=None if restored_dependencies else DEPENDENCY_RESTORE_ERROR)
            remove_preview(job)
            return {'state': 'rolled_back'}
        if not fresh_recovery and sha(profile / 'config.yaml') != request['configuration_sha256']:
            raise ReleaseRejected('The profile configuration changes before program selection')
        if not fresh_recovery:
            from .release_worker import program_plan
            directories, files, dependencies = program_plan(job, request, selected)
            programs.check_plan(directories=directories, files=files, dependencies=dependencies)
            programs.check_prepared()
        write_state(job, 'recovering' if fresh_recovery else 'applying')
        native_started = fresh_recovery
        configuration_before = (profile / 'config.yaml').read_bytes()
        inventory_before = inventory_snapshot(request)
        try:
            if services is not None:
                if fresh_recovery and _journaled(services):
                    services.quiesce()
                else:
                    services.drain(signature=plan['services']['signature'])
                services.verify_stopped()
            _consumers_stopped(request, plan)
            drained = boot_ticks()
            if fresh_recovery:
                restore_native_mount(job, request, mount)
            for entry in programs.entries():
                Path(entry['target']).parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            if selected['fresh']:
                native_started = True
                initialize_native(job, request, selected, checkpoint=checkpoint)
            if fresh_recovery:
                programs.resume(checkpoint=checkpoint)
            else:
                programs.apply(checkpoint=checkpoint)
            checkpoint('programs-published')
            clear_bytecode(request, [entry['target'] for entry in programs.entries()])
            _systemctl('daemon-reload')
            adopt_units(services, request)
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
            started = services.resume()['services_started'] if services is not None else []
            _start_created(plan)
            receipt = verify_registration(request, plan)
            from .inplace_preparation import host_python
            verify_restart(request, plan, selected['entry'], started, drained, configuration_before,
                           fresh=selected['fresh'], python=host_python(request['host']['source']))
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
                restore_native_mount(job, request, mount)
                write_state(job, 'recovery_required',
                            error='The first installation stopped after LifeOS was initialized. Recover it to finish.')
                raise
            restored = _rollback(job, request, plan, services, programs, lambda: restore_native_mount(job, request, mount),
                                 release_update=release_update)
            write_state(job, 'rolled_back', error=None if restored else DEPENDENCY_RESTORE_ERROR)
            raise
    finally:
        revoke_authorization(administration, profile, request)
