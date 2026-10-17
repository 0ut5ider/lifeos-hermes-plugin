# ABOUTME: Applies complete integration programs from a detached, profile-bound release operation.
# ABOUTME: Preserves user-data roots and uses governed mount recovery for native configuration changes.
from __future__ import annotations

import argparse
import io
import importlib
import json
import os
import re
import stat
from pathlib import Path
import sys
import types
import traceback

if not __package__:
    namespace = types.ModuleType('lifeos_release_worker')
    namespace.__path__ = [str(Path(__file__).resolve().parent)]
    sys.modules[namespace.__name__] = namespace
    __package__ = namespace.__name__

from .cli import operation, read_private, write_state
from .release_catalog import ReleaseRejected, _json
from .release_plan import inspect_operation, service_environment, verify_runtime
from .release_programs import ProgramTransaction, fingerprint, launcher_script, publish
from .release_stage import load_bridge, sha, run_stage, _environment
from .release_operation import (action_state, operation_lock, seal_plan,
    validate_admission, validate_plan, write_admission, request_digest)
from .release_operation import worker_running, OperationBusy


def review_operation(job, request):
    with operation_lock(job):
        return _review_operation(job, request)


def _review_operation(job, request, *, installation_lease=None, preparing=False):
    if preparing:
        if read_private(job / 'status.json')['state'] != 'preparing':
            raise ReleaseRejected('The candidate review requires an unfinished preparation')
    else:
        action_state(job, 'apply')
    selected = inspect_operation(job, request, installation_lease=installation_lease)
    plan = {'fresh': selected['fresh'], 'native_mount_required': selected['native_changes'],
            'launchers': [str(path) for path in selected['launchers']], 'services': selected['services']}
    expected = None
    if (job / 'plan.json').is_file():
        expected = validate_plan(job, request)['program_entries_sha256']
    programs = ProgramTransaction(job / 'program-snapshot', expected_entries_sha256=expected)
    if programs.journal.is_file():
        programs.check_prepared()
    else:
        directories, files, dependencies = _program_plan(job, request, selected)
        programs.prepare(directories=directories, files=files, dependencies=dependencies)
    plan['program_entries_sha256'] = programs.entries_digest()
    seal_plan(job, request, plan, preparing=preparing)
    return selected, plan


def admit_operation(job, request, action, *, authorization=None):
    profile = Path(request['profile'])
    current = recovery_bridge(job, profile)
    lock = current.memory_module('installation_lock').installation_lock
    with operation_lock(job), lock(profile) as lease:
        marker=profile/'.lifeos-removal.json'
        if marker.exists() or marker.is_symlink():
            raise ReleaseRejected('Recover the selected software removal before another release action')
        if read_private(job / 'request.json') != request:
            raise ReleaseRejected('The operation changes after owner review')
        for sibling in job.parent.iterdir():
            if sibling != job and sibling.is_dir() and (sibling / 'status.json').is_file():
                state = read_private(sibling / 'status.json')['state']
                if state.startswith('queued-') or state in {'applying', 'recovering', 'restoring', 'recovery_required'}:
                    raise ReleaseRejected('Finish the active release operation before another action')
        return _admit_operation(job, request, action, authorization=authorization, installation_lease=lease)


def _admit_operation(job, request, action, *, authorization=None, installation_lease=None):
    if action not in {'apply', 'recover', 'restore'}:
        raise ReleaseRejected('Choose an apply, recovery, or rollback action')
    action_state(job, action)
    if action == 'recover' and read_private(job / 'status.json')['state'].startswith('queued-') and worker_running(job) is True:
        raise ReleaseRejected('The queued worker is running')
    if action == 'apply':
        selected, plan = _review_operation(job, request, installation_lease=installation_lease)
        if sha(Path(request['profile']) / 'config.yaml') != request['configuration_sha256']:
            raise ReleaseRejected('The profile configuration changes after preparation')
    else:
        plan = validate_plan(job, request)
        if plan['fresh'] and action == 'restore':
            raise ReleaseRejected('A first installation has no prior integration version to select')
        selected = {'profile': Path(request['profile']), 'installed': Path(request['installed']),
                    'current': recovery_bridge(job, Path(request['profile']))}
    administration = selected['current'].memory_administration()
    if plan['native_mount_required'] and administration.required(selected['installed'], selected['profile']):
        if authorization is None:
            raise PermissionError('The native mount requires installation owner authorization')
        administration.mount_environment(selected['installed'], selected['profile'], authorization,
            binding=administration.job_binding(job, request, action))
    if action == 'restore':
        mount_module = selected['current'].memory_module('mount_transaction')
        baseline = selected['current'].memory_module('version_drift').default_baseline_path(selected['installed'].parent)
        check_restore(job, request, plan, mount_module.MountTransaction(selected['installed'], selected['profile'], baseline))
    if authorization is not None:
        request = {**request, 'memory_authorization': str(authorization)}
    publish(job / 'request.json', (json.dumps(request, indent=2) + '\n').encode())
    write_admission(job, request, action)
    write_state(job, 'queued-' + action)


def recovery_bridge(job, profile):
    request = read_private(job / 'request.json')
    plan = validate_plan(job, request) if (job / 'plan.json').is_file() else None
    if plan is not None and plan['fresh']:
        validate_operation_package(job, request)
        return load_bridge(job / 'package/lifeos_hook_bridge')
    active = profile / 'plugins/lifeos-hook-bridge'
    if active.is_dir():
        return load_bridge(active)
    expected = plan['program_entries_sha256'] if plan is not None else None
    snapshot = ProgramTransaction(job / 'program-snapshot', expected_entries_sha256=expected)
    if snapshot.journal.is_file():
        value = snapshot._load()
        for index, entry in enumerate(value['entries']):
            retained = snapshot.snapshot / ('before-' + str(index))
            if entry['target'] == str(active) and entry['before'] is not None and fingerprint(retained) == entry['before']:
                return load_bridge(retained)
        if plan is None or not plan['fresh']:
            raise ReleaseRejected('The retained bridge does not match its recorded identity')
    candidate = job / 'package/lifeos_hook_bridge'
    validate_operation_package(job, request)
    return load_bridge(candidate)


def validate_operation_package(job, request):
    """Validate the operation's extracted package against its certificate; return the package manifest."""
    if request.get('format') == 2:
        from .integration_package import validate_integration
        return validate_integration(job / 'package', request['certificate'])
    from .release_stage import validate_package
    return validate_package(job / 'package', request['certificate'])


def _yaml_configuration(profile, native):
    from ruamel.yaml import YAML
    yaml = YAML()
    data = yaml.load((profile / 'config.yaml').read_bytes())
    if not isinstance(data, dict):
        raise ReleaseRejected('The selected profile configuration is not a mapping')
    # Native Mount.ts edits block headers. Preserve values and comments while preparing those headers.
    pending, seen = [data], set()
    while pending:
        value = pending.pop()
        if not isinstance(value, (dict, list)) or id(value) in seen:
            continue
        seen.add(id(value))
        formatting = getattr(value, 'fa', None)
        if formatting is not None:
            formatting.set_block_style()
        pending.extend(value.values() if isinstance(value, dict) else value)
    plugins = data.setdefault('plugins', {})
    enabled = plugins.setdefault('enabled', [])
    disabled = plugins.setdefault('disabled', [])
    if not isinstance(enabled, list) or not isinstance(disabled, list):
        raise ReleaseRejected('The profile plugin selection requires named enablement lists')
    for name in ('lifeos-hook-bridge', 'lifeos-release-manager'):
        if name not in enabled:
            enabled.append(name)
        while name in disabled:
            disabled.remove(name)
    entries = plugins.setdefault('entries', {})
    bridge = entries.setdefault('lifeos-hook-bridge', {})
    bridge['enabled'] = True
    bridge.setdefault('settings', {})['lifeos_source_dir'] = str(native)
    entries.setdefault('lifeos-release-manager', {})['enabled'] = True
    rendered = io.StringIO()
    yaml.dump(data, rendered)
    return rendered.getvalue().encode()


def _program_plan(job, request, selected):
    profile, installed = selected['profile'], selected['installed']
    package = selected['package']
    native = selected.get('native', package / 'lifeos/LifeOS/install')
    generated = job / 'generated'
    generated.mkdir(mode=0o700, exist_ok=True)
    if (generated.resolve() != generated or generated.stat().st_uid != os.getuid()
            or generated.stat().st_mode & 0o077):
        raise ReleaseRejected('Release preparation outputs require a private owner directory')
    files, dependencies = {}, {}
    directories = {selected['bridge']: package / 'lifeos_hook_bridge',
                   profile / 'plugins/lifeos-release-manager': package / 'optional/lifeos_release_manager'}
    if request.get('format') == 2:
        from .inplace_plan import host_entries
        host_directories, host_files = host_entries(job, request, selected, generated)
        directories.update(host_directories)
        files.update(host_files)
    else:
        launch = generated / 'hermes'
        publish(launch, launcher_script(request['runtime']['hermes']), 0o700)
        for path in selected['launchers']:
            files[path] = launch
        commands = _json((job / 'manifest.json').read_bytes())['runtime']['commands']
        for name in ('hermes', 'hermes-agent', 'hermes-acp'):
            if commands.get(name) != 'bin/' + name:
                raise ReleaseRejected('The prepared runtime changes a native command path')
            command = generated / name
            publish(command, launcher_script(str(job / commands[name])), 0o700)
            files[Path(request['account_home']) / '.local/bin' / name] = command
    bun = Path(request['account_home']) / '.local/bin/bun'
    files[bun] = Path(request['runtime']['bun'])
    publish(generated / 'config.yaml', _yaml_configuration(profile, native))
    configuration_check = ('import sys\nfrom argparse import Namespace\n'
        'from hermes_constants import set_hermes_home_override\n'
        'set_hermes_home_override(sys.argv[1])\n'
        'from hermes_cli.post_update import step_migrate_config\n'
        'step_migrate_config()\n'
        'from hermes_cli.config import config_command\n'
        'config_command(Namespace(config_command="check"))\n')
    python = request['runtime']['python']
    if request.get('format') == 2:
        from .inplace_preparation import host_python
        python = host_python(request['host']['source'])
    run_stage([python, '-B', '-c', configuration_check, str(generated)],
        job, 'program-configuration', environment=_environment(generated, home=job,
            source=Path(request['runtime']['source'])))
    files[profile / 'config.yaml'] = generated / 'config.yaml'
    current = selected['current']
    created = selected.get('created_roles', ('gateway', 'dashboard', 'pulse') if selected['fresh'] else ())
    if created:
        from .release_services import service_files
        files.update(service_files(request, generated, roles=created))
    if not selected['fresh']:
        drift = current.memory_module('version_drift')
        previous = selected['reviewed_baseline']
        planner = current.memory_module('update_plan')
        native_plan = planner.plan_system_files(installed, previous, native, Path(request['runtime']['reference']))
        for name in (*native_plan['add'], *native_plan['replace']):
            files[installed / name] = native / name
        for name in native_plan['remove']:
            files[installed / name] = None
        if selected['native_changes']:
            hooks = current.memory_module('update_hooks')
            old_hooks = json.loads((selected['prior_source'] / 'hooks/hooks.json').read_bytes())['hooks']
            new_hooks = json.loads((native / 'hooks/hooks.json').read_bytes())['hooks']
            settings, _ = hooks.replace_owned_hooks(json.loads((installed / 'settings.json').read_bytes()), old_hooks, new_hooks)
            publish(generated / 'settings.json', (json.dumps(settings, indent=2) + '\n').encode())
            files[installed / 'settings.json'] = generated / 'settings.json'
            dependency_module = current.memory_module('update_dependencies')
            prior_roots = dependency_module._package_roots(selected['prior_source'])
            next_roots = dependency_module._package_roots(native)
            reference = Path(request['runtime']['reference'])
            for relative in prior_roots | next_roots:
                for name in ('package.json', 'bun.lock'):
                    target = installed / relative / name
                    source = reference / relative / name if relative in next_roots else None
                    files[target] = source if source is not None and source.is_file() else None
                source = reference / relative / 'node_modules' if relative in next_roots else None
                if source is not None and not source.is_dir():
                    source = None
                dependencies[installed / relative / 'node_modules'] = source
        if selected['native_changes']:
            files[selected['baseline']] = selected['baseline']
        else:
            baseline = drift.create_baseline(native, installed)
            baseline['created_at'] = previous['created_at']
            publish(generated / 'baseline.json', (json.dumps(baseline, indent=2) + '\n').encode())
            files[selected['baseline']] = generated / 'baseline.json'
    certificate = request['certificate']
    if request.get('format') == 2:
        manifest = json.loads((package / 'INTEGRATION.json').read_bytes())
        receipt = {'format': 1, 'version': request['version'], 'commit': request['commit'],
            'package_sha256': request['package_sha256'], 'plugin_files': manifest['plugin_files'],
            'upstream': {'hermes': request['host']['commit'], 'lifeos': certificate['lifeos']['commit']},
            'patches': {'hermes': len(selected['entry']['patches']), 'lifeos': len(selected['candidate'].LIFEOS_PATCHES)},
            'operators': {}}
    else:
        manifest = json.loads((package / 'DAILY-CANDIDATE.json').read_bytes())
        receipt = {'format': 1, 'version': request['version'], 'commit': request['commit'],
            'package_sha256': request['package_sha256'],
            'plugin_files': {name.removeprefix('lifeos_hook_bridge/'): value for name, value in manifest['plugin_files'].items()},
            'upstream': {'hermes': certificate['hermes_base'], 'lifeos': certificate['lifeos_base']},
            'patches': {'hermes': certificate['hermes_patch_count'], 'lifeos': certificate['lifeos_patch_count']},
            'operators': manifest.get('operators', {})}
    publish(generated / 'integration-release.json', (json.dumps(receipt, indent=2) + '\n').encode())
    files[profile / 'integration-release.json'] = generated / 'integration-release.json'
    return directories, files, dependencies


def _fresh_native(job, request, selected, *, checkpoint=lambda point: None):
    from .release_initialization import NativeInitialization
    helpers = selected['candidate'].memory_module('fresh_store')
    return NativeInitialization(job, request, selected['installed']).execute(helpers, checkpoint=checkpoint)


def _return_fresh_dashboard(job, request, selected, programs, services, lease):
    initialization = job / 'native-initialization.json'
    if initialization.is_file() and read_private(initialization)['state'] == 'complete':
        # Finish only the admitted program phase. Native mounting remains an explicit recovery action.
        programs.resume()
        verify_runtime(request)
        from .release_services import verify_installed_services
        verify_installed_services(selected['candidate'], selected['profile'], selected['installed'], installation_lease=lease)
    else:
        programs.check_prepared()
    services.resume()


def execute(job, action, *, checkpoint=lambda point: None):
    with operation_lock(job):
        request = read_private(job / 'request.json')
        validate_admission(job, request, action)
        try:
            return _execute(job, action, checkpoint=checkpoint)
        except (ValueError, OSError, RuntimeError, PermissionError, ImportError, KeyError) as error:
            record_failure(job, error)
            state = read_private(job / 'status.json')['state']
            if state not in {'rolled_back', 'applied', 'recovery_required'}:
                failed_state = ('recovery_required' if state in {'applying', 'recovering', 'restoring', 'queued-recover'}
                                else 'applied' if state == 'queued-restore' else 'rejected')
                write_state(job, failed_state,
                    error='The release worker refuses the current artifacts or authority. Review the private operation before recovery.')
            raise
        finally:
            revoke_recorded_authorization(job)


def revoke_recorded_authorization(job):
    request = read_private(job / 'request.json')
    authorization = request.get('memory_authorization')
    if authorization is None:
        return
    profile = job.parent.parent
    if request.get('profile') != str(profile):
        raise ReleaseRejected('The grant cleanup changes its operation profile')
    directory = profile / '.lifeos-memory-admin'
    path = Path(authorization)
    if path.parent != directory or re.fullmatch(r'[0-9a-f]{32}\.json', path.name) is None:
        raise ReleaseRejected('The grant cleanup changes its private authorization path')
    info = directory.lstat()
    if (directory.resolve() != directory or not stat.S_ISDIR(info.st_mode)
            or info.st_uid != os.getuid() or info.st_mode & 0o077):
        raise ReleaseRejected('The grant cleanup requires private owner storage')
    path.unlink(missing_ok=True)


def _execute(job, action, *, checkpoint=lambda point: None):
    request = read_private(job / 'request.json')
    profile = Path(request['profile'])
    job, request = operation(profile, job.name)
    sys.path.insert(0, request['runtime']['source'])
    current = recovery_bridge(job, profile)
    lock = current.memory_module('installation_lock').installation_lock
    program_lock = current.memory_module('program_lock')
    with lock(profile, wait=True) as lease, program_lock.exclusive(profile, timeout=600):
        marker=profile/'.lifeos-removal.json'
        if marker.exists() or marker.is_symlink():
            raise ReleaseRejected('Recover the selected software removal before another release worker')
        request = read_private(job / 'request.json')
        validate_admission(job, request, action)
        if request.get('format') == 2:
            from .inplace_worker import run
            return run(job, request, action, current, lease, checkpoint=checkpoint)
        plan = validate_plan(job, request)
        fresh_recovery = action == 'recover' and plan['fresh']
        if action == 'apply':
            selected = inspect_operation(job, request, installation_lease=lease)
        elif fresh_recovery:
            selected = inspect_operation(job, request, installation_lease=lease, fresh_recovery=True)
        else:
            if str(current.memory_module('lifeos_installation').selection(profile).installed) != request['installed']:
                raise ReleaseRejected('The recovery changes its selected native installation')
            selected = {'profile': profile, 'installed': Path(request['installed']), 'current': current,
                'baseline': current.memory_module('version_drift').default_baseline_path(Path(request['installed']).parent)}
        services = None
        if plan['services']:
            if plan['fresh']:
                from .release_services import fresh_services
                services = fresh_services(current, profile, selected['installed'], installation_lease=lease)
            else:
                services = current.memory_module('profile_services').ProfileServices(profile, selected['installed'], installation_lease=lease)
        administration = current.memory_administration()
        if fresh_recovery and administration.required(selected['installed'], profile):
            raise PermissionError('Fresh recovery preserves newly enabled memory ownership and requires governed installation repair')
        environment = service_environment(request)
        if plan['native_mount_required']:
            environment = administration.mount_environment(selected['installed'], profile,
                request.get('memory_authorization'), binding=administration.job_binding(job, request, action))
            environment.update(PATH=service_environment(request)['PATH'], PYTHONPATH=request['runtime']['source'])
        programs = ProgramTransaction(job / 'program-snapshot', expected_entries_sha256=plan['program_entries_sha256'])
        mount = current.memory_module('mount_transaction').MountTransaction(selected['installed'], profile, selected['baseline'])
        if action != 'apply' and not fresh_recovery:
            manifest = check_mount_recovery(job, request, mount)
            if action == 'restore':
                check_restore(job, request, plan, mount)
            else:
                overrides = {} if manifest is None or manifest['state'] == 'rolled_back' else {
                    entry['target']: fingerprint(entry['target'])
                    for entry in manifest['entries']}
                programs.check_recovery(overrides=overrides)
            write_state(job, 'recovering' if action == 'recover' else 'restoring')
            if services is not None:
                services.quiesce()
            _restore_mount(job, request, mount)
            programs.restore()
            if services is not None:
                services.resume()
            verify_runtime(request, restored=True)
            write_state(job, 'rolled_back')
            _revoke(administration, profile, request)
            return {'state': 'rolled_back'}
        if not fresh_recovery and sha(profile / 'config.yaml') != request['configuration_sha256']:
            raise ReleaseRejected('The profile configuration changes before program selection')
        if not fresh_recovery:
            directories, files, dependencies = _program_plan(job, request, selected)
            programs.check_plan(directories=directories, files=files, dependencies=dependencies)
            programs.check_prepared()
        write_state(job, 'recovering' if fresh_recovery else 'applying')
        try:
            if services is not None:
                if fresh_recovery:
                    if services.status()['state'] == 'none':
                        services.drain(signature=plan['services']['signature'])
                    else:
                        services.quiesce()
                else:
                    services.drain(signature=plan['services']['signature'])
                services.verify_stopped()
                if selected['fresh']:
                    from .release_services import check_dashboard_writers
                    check_dashboard_writers(profile)
            if fresh_recovery:
                _restore_mount(job, request, mount)
            for entry in programs._load()['entries']:
                Path(entry['target']).parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            if selected['fresh']:
                _fresh_native(job, request, selected, checkpoint=checkpoint)
            if fresh_recovery:
                programs.resume(checkpoint=checkpoint)
            else:
                programs.apply(checkpoint=checkpoint)
            checkpoint('programs-published')
            if plan['native_mount_required']:
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
            if selected['fresh']:
                from .release_services import verify_installed_services
                verify_installed_services(selected['candidate'], profile, selected['installed'], installation_lease=lease)
            if services is not None:
                services.resume()
            write_state(job, 'applied')
            return {'state': 'applied'}
        except BaseException as error:
            record_failure(job, error)
            if services is not None:
                services.quiesce()
            _restore_mount(job, request, mount)
            if selected['fresh']:
                write_state(job, 'recovery_required', error='The prepared first installation requires recovery. User data is preserved.')
                if services is not None:
                    _return_fresh_dashboard(job, request, selected, programs, services, lease)
                raise
            programs.restore()
            if services is not None:
                services.resume()
            write_state(job, 'rolled_back')
            raise
        finally:
            _revoke(administration, profile, request)


def _revoke(administration, profile, request):
    authorization = request.get('memory_authorization')
    if authorization is not None:
        administration.revoke(administration.MemoryConfiguration(profile / 'lifeos-memory.json'), authorization)


def record_failure(job, error):
    frames = [{'file': frame.filename, 'line': frame.lineno, 'function': frame.name}
              for frame in traceback.extract_tb(error.__traceback__)]
    value = {'exception': type(error).__name__, 'frames': frames}
    if isinstance(error, ReleaseRejected):
        # Release refusals are written for the owner and carry no credentials or command text.
        value['message'] = str(error)
    publish(job / 'worker-failure.json', (json.dumps(value) + '\n').encode())


def _restore_mount_manifest(job, request, journal, *, required=False):
    intent = job / 'mount-intent.json'
    if not intent.is_file() or not journal.is_file():
        if required:
            raise ReleaseRejected('The release no longer has its retained native mount')
        return None
    if sha(journal) == read_private(intent)['prior_journal_sha256']:
        if required:
            raise ReleaseRejected('The release no longer has its retained native mount')
        return None
    action = read_private(intent).get('action', 'apply')
    if action not in {'apply', 'recover'}:
        raise ReleaseRejected('The native mount intent changes its admitted action')
    expected = {'job': str(job.absolute()), 'request_digest': request_digest(request), 'action': action}
    manifest = read_private(journal)
    if not isinstance(manifest, dict) or manifest.get('binding') != expected:
        raise ReleaseRejected('The native mount journal belongs to another release operation')
    return manifest


def _retained_mount(manifest, profile):
    if manifest['state'] != 'committed' or manifest.get('retain_for_rollback') is not True:
        raise ReleaseRejected('The release no longer has its retained native mount')
    _check_mount_copies(manifest, profile)


def _check_mount_copies(manifest, profile):
    snapshot = Path(manifest['snapshot'])
    if (snapshot.parent != profile / '.lifeos-mount' or snapshot.resolve() != snapshot
            or re.fullmatch(r'[0-9a-f]{32}', snapshot.name) is None):
        raise ReleaseRejected('The retained native mount changes its snapshot directory')
    info = snapshot.stat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise ReleaseRejected('The retained native mount requires its private snapshot')
    for index, entry in enumerate(manifest['entries']):
        if type(entry['copy']) is not int or entry['copy'] != index:
            raise ReleaseRejected('The mount recovery copy changes its recorded path')
        if entry['before'] is None:
            continue
        copy = snapshot / 'previous' / str(index)
        try:
            info = copy.lstat()
        except FileNotFoundError as error:
            raise ReleaseRejected('The mount recovery copy is missing') from error
        if (not stat.S_ISREG(info.st_mode) or info.st_size > 4 * 1024 * 1024
                or info.st_uid != os.getuid() or info.st_mode & 0o077
                or fingerprint(copy)['sha256'] != entry['before']['digest']):
            raise ReleaseRejected('The mount recovery copy changed')


def check_mount_recovery(job, request, mount):
    manifest = _restore_mount_manifest(job, request, mount.journal)
    if manifest is not None and manifest['state'] != 'rolled_back':
        _check_mount_copies(manifest, Path(request['profile']))
    if manifest is not None:
        with mount._lock():
            selected = mount._manifest()
            if selected is None:
                raise ReleaseRejected('The native recovery changes its selected installation')
            acceptable = ('after',) if selected['state'] == 'committed' else (
                ('before',) if selected['state'] == 'rolled_back' else ('before', 'after'))
            mount._checks(selected['entries'], acceptable, restoring=selected['state'] == 'restoring')
    return manifest


def restore_available(job, request, plan):
    if plan['fresh']:
        return False
    try:
        profile = Path(request['profile'])
        receipt = read_private(profile / 'integration-release.json')
        if not isinstance(receipt, dict) or any(receipt.get(key) != request[key]
                for key in ('version', 'commit', 'package_sha256')):
            return False
        if plan['native_mount_required']:
            manifest = _restore_mount_manifest(job, request, profile / '.lifeos-mount/operation.json', required=True)
            _retained_mount(manifest, profile)
        return True
    except (ValueError, OSError, RuntimeError, KeyError, TypeError):
        return False


def check_restore(job, request, plan, mount):
    manifest = _restore_mount_manifest(job, request, mount.journal, required=plan['native_mount_required'])
    overrides = {}
    if manifest is not None:
        _retained_mount(manifest, Path(request['profile']))
        mount.check_completed()
        overrides = {entry['target']: {'type': 'file', 'mode': entry['after']['mode'],
                                      'sha256': entry['after']['digest']} for entry in manifest['entries']}
    programs = ProgramTransaction(job / 'program-snapshot', expected_entries_sha256=plan['program_entries_sha256'])
    programs.check_applied(overrides=overrides)


def _restore_mount(job, request, mount):
    if _restore_mount_manifest(job, request, mount.journal) is None:
        return
    candidate = load_bridge(job / 'package/lifeos_hook_bridge')
    transaction = candidate.memory_module('mount_transaction').MountTransaction(
        Path(request['installed']), Path(request['profile']), mount.baseline)
    status = transaction.status()
    if status['recovery_required']:
        transaction.recover()
    elif status['state'] == 'committed':
        transaction.restore_completed()


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser()
    parser.add_argument('job', type=Path)
    parser.add_argument('--action', choices=('prepare', 'apply', 'recover', 'restore'), default='apply')
    args = parser.parse_args()
    sys.dont_write_bytecode = True
    preparing_job = None
    try:
        if args.action == 'prepare':
            request = read_private(args.job.absolute() / 'request.json')
            preparing_job, request = operation(Path(request['profile']), args.job.name)
            with operation_lock(preparing_job):
                _, result = _review_operation(preparing_job, request, preparing=True)
                write_state(preparing_job, 'ready')
        else:
            result = execute(args.job.absolute(), args.action)
    except OperationBusy:
        return 1
    except (ValueError, OSError, RuntimeError, PermissionError, ImportError, KeyError) as error:
        if args.action == 'prepare':
            if preparing_job is not None:
                with operation_lock(preparing_job):
                    record_failure(preparing_job, error)
            return 1
        return 1
    print(json.dumps(result))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
