# ABOUTME: Applies complete integration programs from a detached, profile-bound release operation.
# ABOUTME: Preserves user-data roots and uses governed mount recovery for native configuration changes.
from __future__ import annotations

import argparse
import io
import importlib
import json
import os
from pathlib import Path
import shutil
import sys
import types

if not __package__:
    namespace = types.ModuleType('lifeos_release_worker')
    namespace.__path__ = [str(Path(__file__).resolve().parent)]
    sys.modules[namespace.__name__] = namespace
    __package__ = namespace.__name__

from .cli import operation, read_private, write_state
from .release_catalog import ReleaseRejected
from .release_plan import inspect_operation, service_environment, verify_runtime
from .release_programs import ProgramTransaction, fingerprint, publish
from .release_stage import load_bridge, sha


def review_operation(job, request):
    selected = inspect_operation(job, request)
    plan = {'fresh': selected['fresh'], 'native_mount_required': selected['native_changes'],
            'launchers': [str(path) for path in selected['launchers']], 'services': selected['services']}
    publish(job / 'plan.json', (json.dumps(plan, indent=2) + '\n').encode())
    return selected, plan


def admit_operation(job, request, action, *, authorization=None):
    if action not in {'apply', 'recover', 'restore'}:
        raise ReleaseRejected('Choose an apply, recovery, or rollback action')
    if action == 'apply':
        if read_private(job / 'status.json')['state'] != 'ready':
            raise ReleaseRejected('The release operation is not ready')
        selected, plan = review_operation(job, request)
        if sha(Path(request['profile']) / 'config.yaml') != request['configuration_sha256']:
            raise ReleaseRejected('The profile configuration changes after preparation')
    else:
        plan = read_private(job / 'plan.json')
        if plan['fresh']:
            raise ReleaseRejected('A first installation has no prior integration version to select')
        selected = {'profile': Path(request['profile']), 'installed': Path(request['installed']),
                    'current': load_bridge(Path(request['profile']) / 'plugins/lifeos-hook-bridge')}
    administration = selected['current'].memory_administration()
    if plan['native_mount_required'] and administration.required(selected['installed'], selected['profile']):
        if authorization is None:
            raise PermissionError('The native mount requires installation owner authorization')
        administration.mount_environment(selected['installed'], selected['profile'], authorization,
            binding=administration.job_binding(job, request, action))
    if authorization is not None:
        request = {**request, 'memory_authorization': str(authorization)}
    publish(job / 'request.json', (json.dumps(request, indent=2) + '\n').encode())
    write_state(job, 'queued-' + action)


def _yaml_configuration(profile, native):
    from ruamel.yaml import YAML
    yaml = YAML()
    data = yaml.load((profile / 'config.yaml').read_bytes())
    if not isinstance(data, dict):
        raise ReleaseRejected('The selected profile configuration is not a mapping')
    plugins = data.setdefault('plugins', {})
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
    native = package / 'lifeos/LifeOS/install'
    generated = job / 'generated'
    generated.mkdir(mode=0o700)
    files, dependencies = {}, {}
    directories = {selected['bridge']: package / 'lifeos_hook_bridge',
                   profile / 'plugins/lifeos-release-manager': package / 'optional/lifeos_release_manager'}
    for path in selected['launchers']:
        files[path] = Path(request['runtime']['hermes'])
    bun = Path(request['account_home']) / '.local/bin/bun'
    files[bun] = Path(request['runtime']['bun'])
    publish(generated / 'config.yaml', _yaml_configuration(profile, native))
    files[profile / 'config.yaml'] = generated / 'config.yaml'
    current = selected['current']
    if not selected['fresh']:
        drift = current.memory_module('version_drift')
        previous = drift.load_baseline(selected['baseline'], installed)
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
            publish(generated / 'baseline.json', (json.dumps(drift.create_baseline(native, installed), indent=2) + '\n').encode())
            files[selected['baseline']] = generated / 'baseline.json'
    manifest = json.loads((package / 'DAILY-CANDIDATE.json').read_bytes())
    certificate = request['certificate']
    receipt = {'format': 1, 'version': request['version'], 'commit': request['commit'],
        'package_sha256': request['package_sha256'],
        'plugin_files': {name.removeprefix('lifeos_hook_bridge/'): value for name, value in manifest['plugin_files'].items()},
        'upstream': {'hermes': certificate['hermes_base'], 'lifeos': certificate['lifeos_base']},
        'patches': {'hermes': certificate['hermes_patch_count'], 'lifeos': certificate['lifeos_patch_count']},
        'operators': manifest.get('operators', {})}
    publish(generated / 'integration-release.json', (json.dumps(receipt, indent=2) + '\n').encode())
    files[profile / 'integration-release.json'] = generated / 'integration-release.json'
    return directories, files, dependencies


def _fresh_native(job, request, selected):
    reference = Path(request['runtime']['reference'])
    installed = selected['installed']
    user = installed.parent / '.config/LIFEOS/USER'
    if installed.exists() or user.exists() or installed.is_symlink() or user.is_symlink():
        raise ReleaseRejected('A fresh destination gains existing data before installation')
    helpers = selected['candidate'].memory_module('fresh_store')
    source_user = (reference / 'LIFEOS/USER').resolve(strict=True)
    helpers._empty_personal_templates(source_user, job / 'fresh-templates')
    config = source_user / 'CONFIG/config.toml'
    publish(config, helpers._config_names(config.read_bytes(), helpers._name(request['name']), helpers._name(request['assistant'])))
    user.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    shutil.copytree(source_user, user)
    shutil.copytree(reference, installed, symlinks=True)
    link = installed / 'LIFEOS/USER'
    if not link.is_symlink():
        raise ReleaseRejected('The fresh native installation has no expected user-data link')
    link.unlink()
    link.symlink_to(user, target_is_directory=True)
    settings = installed / 'settings.json'
    publish(settings, settings.read_bytes().replace(str(reference.parent).encode(), str(installed.parent).encode()))


def execute(job, action):
    request = read_private(job / 'request.json')
    profile = Path(request['profile'])
    job, request = operation(profile, job.name)
    sys.path.insert(0, request['runtime']['source'])
    active_bridge = profile / 'plugins/lifeos-hook-bridge'
    current = load_bridge(active_bridge if active_bridge.is_dir() else job / 'package/lifeos_hook_bridge')
    lock = current.memory_module('installation_lock').installation_lock
    with lock(profile, wait=True) as lease:
        request = read_private(job / 'request.json')
        if action == 'apply':
            selected = inspect_operation(job, request)
        else:
            selected = {'profile': profile, 'installed': Path(request['installed']), 'current': current,
                'baseline': current.memory_module('version_drift').default_baseline_path(Path(request['installed']).parent)}
        plan = read_private(job / 'plan.json')
        services = None
        if plan['services']:
            services = current.memory_module('profile_services').ProfileServices(profile, selected['installed'], installation_lease=lease)
        administration = current.memory_administration()
        environment = service_environment(request)
        if plan['native_mount_required']:
            environment = administration.mount_environment(selected['installed'], profile,
                request.get('memory_authorization'), binding=administration.job_binding(job, request, action))
            environment.update(PATH=service_environment(request)['PATH'], PYTHONPATH=request['runtime']['source'])
        programs = ProgramTransaction(job / 'program-snapshot')
        mount = current.memory_module('mount_transaction').MountTransaction(selected['installed'], profile, selected['baseline'])
        if action != 'apply':
            write_state(job, 'recovering' if action == 'recover' else 'restoring')
            if services is not None:
                services.quiesce()
            _restore_mount(job, request, mount)
            programs.restore()
            if services is not None:
                services.resume()
            verify_runtime(request, restored=True)
            write_state(job, 'rolled_back')
            return {'state': 'rolled_back'}
        if sha(profile / 'config.yaml') != request['configuration_sha256']:
            raise ReleaseRejected('The profile configuration changes before program selection')
        directories, files, dependencies = _program_plan(job, request, selected)
        programs.prepare(directories=directories, files=files, dependencies=dependencies)
        write_state(job, 'applying')
        try:
            if services is not None:
                services.drain(signature=plan['services']['signature'])
                services.verify_stopped()
            for path in files:
                path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            for path in directories:
                path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            for path in dependencies:
                path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            if selected['fresh']:
                _fresh_native(job, request, selected)
            programs.apply()
            if plan['native_mount_required']:
                mounted_module = importlib.reload(current.memory_module('mount_transaction'))
                mount = mounted_module.MountTransaction(selected['installed'], profile, selected['baseline'])
                drift = current.memory_module('version_drift')
                baseline = drift.create_baseline(selected['package'] / 'lifeos/LifeOS/install', selected['installed'])
                prior = sha(mount.journal) if mount.journal.is_file() else None
                publish(job / 'mount-intent.json', (json.dumps({'prior_journal_sha256': prior}) + '\n').encode())
                mount.execute(environment, request['runtime']['bun'], request['runtime']['hermes'],
                    baseline_data=(json.dumps(baseline) + '\n').encode(),
                    binding=administration.job_binding(job, request, action), retain_for_rollback=True)
            verify_runtime(request)
            if services is not None:
                services.resume()
            write_state(job, 'applied')
            return {'state': 'applied'}
        except BaseException:
            if services is not None:
                services.quiesce()
            _restore_mount(job, request, mount)
            programs.restore()
            if services is not None:
                services.resume()
            write_state(job, 'rolled_back')
            raise
        finally:
            authorization = request.get('memory_authorization')
            if authorization is not None:
                administration.revoke(administration.MemoryConfiguration(profile / 'lifeos-memory.json'), authorization)


def _restore_mount(job, request, mount):
    intent = job / 'mount-intent.json'
    if not intent.is_file() or not mount.journal.is_file():
        return
    if sha(mount.journal) == read_private(intent)['prior_journal_sha256']:
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
    parser = argparse.ArgumentParser()
    parser.add_argument('job', type=Path)
    parser.add_argument('--action', choices=('apply', 'recover', 'restore'), default='apply')
    args = parser.parse_args()
    sys.dont_write_bytecode = True
    try:
        result = execute(args.job.absolute(), args.action)
    except (ValueError, OSError, RuntimeError, PermissionError):
        write_state(args.job, 'recovery_required', error='The release worker refuses the current artifacts or authority. Review the private operation before recovery.')
        return 1
    print(json.dumps(result))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
