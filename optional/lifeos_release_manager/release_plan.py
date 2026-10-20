# ABOUTME: Binds a complete release operation to the current profile and its selected native installation.
# ABOUTME: Checks source drift, service launchers, and native changes before code publication.
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess

from .release_catalog import ReleaseRejected
from .release_accounts import account_home
from .release_baseline import reviewed_baseline
from .release_programs import fingerprint
from .release_stage import load_bridge, sha, validate_package, runtime_source_fingerprint, user_runtime_directory


def inspect_operation(job, request, *, installation_lease=None, fresh_recovery=False):
    if request.get('format') == 2:
        from .inplace_plan import inspect_inplace
        return inspect_inplace(job, request, installation_lease=installation_lease, fresh_recovery=fresh_recovery)
    profile = Path(request['profile'])
    package = job / 'package'
    validate_package(package, request['certificate'])
    archive = job / 'download' / (request['version'] + '-' + request['commit'][:8] + '.tgz')
    if (sha(archive) != request['package_sha256']
            or sha(job / 'manifest.json') != request['runtime_metadata_sha256']
            or sha(package / 'python-runtime/uv.lock') != request['python_lock_sha256']
            or runtime_source_fingerprint(Path(request['runtime']['source'])) != request['runtime_fingerprint']):
        raise ReleaseRejected('A prepared release artifact changes before selection')
    candidate = load_bridge(package / 'lifeos_hook_bridge')
    selected = candidate.memory_module('lifeos_installation').selection(profile)
    installed = selected.installed
    home = account_home(profile)
    if (str(installed) != request['installed'] or Path(request['account_home']) != home
            or request['identifier'] != job.name or job.parent != profile / '.lifeos-releases'):
        raise ReleaseRejected('The operation changes its profile or installation binding')
    for key, expected in {'python': job / 'python-environment/bin/python',
                          'bun': job / 'tools/bun', 'hermes': job / 'bin/hermes',
                          'source': job / 'hermes', 'reference': job / 'reference-home/.claude'}.items():
        if request['runtime'].get(key) != str(expected):
            raise ReleaseRejected('The prepared runtime changes its fixed job paths')
    bridge = profile / 'plugins/lifeos-hook-bridge'
    fresh = fresh_recovery or not installed.exists()
    current = candidate if fresh else load_bridge(bridge) if bridge.is_dir() else candidate
    baseline = current.memory_module('version_drift').default_baseline_path(installed.parent)
    result = {'profile': profile, 'installed': installed, 'candidate': candidate, 'current': current,
              'bridge': bridge, 'baseline': baseline, 'package': package, 'fresh': fresh,
              'native': package / 'lifeos/LifeOS/install'}
    if result['fresh']:
        if not fresh_recovery and (installed.is_symlink() or selected.user_data.exists() or selected.user_data.is_symlink()
                or (profile / 'lifeos-memory.json').exists()):
            raise ReleaseRejected('Fresh installation requires an empty native destination without existing personal data')
        if fresh_recovery and (installed.exists() or selected.user_data.exists()) and not (job / 'native-initialization.json').is_file():
            raise ReleaseRejected('Fresh recovery requires its recorded native initialization')
        from gateway.status import live_gateway_pid_for_home
        if live_gateway_pid_for_home(profile):
            raise ReleaseRejected('Stop this profile gateway before its first native installation')
        if fresh_recovery:
            from .cli import read_private
            preview = read_private(job / 'plan.json')['services']
        else:
            from .release_services import fresh_preview
            preview = fresh_preview(candidate, profile, installed, installation_lease=installation_lease)
        result.update(native_changes=True, services=preview, launchers=[home / '.local/bin/hermes'])
        return result
    result.update(existing_native(result, request, package / 'lifeos/LifeOS/install'))
    services = current.memory_module('profile_services').ProfileServices(profile, installed,
        installation_lease=installation_lease)
    preview = services.preview()
    launchers = set()
    for role in ('gateway', 'dashboard'):
        values, _ = services._inspect(role)
        match = re.search(r'\bpath=([^ ;}]+)', values['ExecStart'])
        if match is None:
            raise ReleaseRejected('A bound service has no fixed launcher path')
        executable = Path(match.group(1))
        if (not executable.is_absolute() or not executable.is_relative_to(home)
                or fingerprint(executable) is None or not executable.is_file()):
            raise ReleaseRejected('The bound service launcher is not a regular account program')
        launchers.add(executable)
    result.update(services=preview, launchers=sorted(launchers))
    return result


def existing_native(selected, request, native):
    """Review the update of an installed native LifeOS tree from ``native``; return the selection fields."""
    profile, installed, bridge = selected['profile'], selected['installed'], selected['bridge']
    current, baseline = selected['current'], selected['baseline']
    if not bridge.is_dir() or bridge.is_symlink():
        raise ReleaseRejected('The existing native installation requires its installed bridge')
    active = current.memory_module('release_version').status(profile, bridge)['active']
    if active['verification'] != 'verified':
        raise ReleaseRejected('The existing bridge differs from its recorded release')
    drift = current.memory_module('version_drift')
    prior = drift.load_baseline(baseline, installed)
    source = Path(prior['source_root'])
    current.memory_module('update_worker').check_prior_source(prior, source, installed)
    current.memory_module('update_worker').check_template_compatibility(source, native)
    planner = current.memory_module('update_plan')
    reference = Path(request['runtime']['reference'])
    prior = reviewed_baseline(profile, prior, installed,
        planner.deployed_system_files(native, reference), active, planner)
    changes = planner.plan_system_files(installed, prior, native, reference)
    dependency_module = current.memory_module('update_dependencies')
    dependency_roots = dependency_module._package_roots(source) | dependency_module._package_roots(native)
    dependency_changes = any(
        (sha(source / root / name) if (source / root / name).is_file() else None)
        != (sha(native / root / name) if (native / root / name).is_file() else None)
        for root in dependency_roots for name in ('package.json', 'bun.lock'))
    return {'prior_source': source, 'reviewed_baseline': prior,
            'native_changes': dependency_changes or any(changes[key] for key in ('add', 'replace', 'remove'))}


def service_environment(request):
    environment = dict(os.environ, HOME=request['account_home'], HERMES_HOME=request['profile'],
        XDG_RUNTIME_DIR=user_runtime_directory(),
        DBUS_SESSION_BUS_ADDRESS='unix:path=' + user_runtime_directory() + '/bus',
        PYTHONDONTWRITEBYTECODE='1')
    environment['PATH'] = str(Path(request['runtime']['bun']).parent) + os.pathsep + environment.get('PATH', os.defpath)
    if request.get('format') == 2:
        # The host launcher activates its own source and environment; a preview path would hide the real host.
        environment.pop('PYTHONPATH', None)
    else:
        environment['PYTHONPATH'] = request['runtime']['source']
    return environment


def verify_runtime(request, *, restored=False):
    profile = Path(request['profile'])
    if restored:
        commands = json.loads((Path(request['profile']) / '.lifeos-releases' / request['identifier'] / 'plan.json').read_bytes())['launchers']
        command = commands[0]
    else:
        command = request['runtime']['hermes']
    result = subprocess.run([command, 'config', 'check'], env=service_environment(request),
                            text=True, capture_output=True, timeout=90)
    if result.returncode:
        raise ReleaseRejected('The selected Hermes runtime refuses the preserved profile configuration')
    if restored:
        return
    from .cli import read_private
    job = profile / '.lifeos-releases' / request['identifier']
    for launcher in read_private(job / 'plan.json')['launchers']:
        result = subprocess.run([launcher, 'lifeos-version'], env=service_environment(request),
                                text=True, capture_output=True, timeout=90)
        if result.returncode:
            raise ReleaseRejected('The selected installed launcher cannot load the integration commands')
        try:
            report = json.loads(result.stdout)
            active = report['active']
        except (ValueError, KeyError, TypeError) as error:
            raise ReleaseRejected('The installed launcher does not return a release identity') from error
        if (active.get('verification') != 'verified' or any(active.get(name) != request[name]
                for name in ('version', 'commit', 'package_sha256'))):
            raise ReleaseRejected('The installed command does not match the selected complete release')
        # The bridge compares the patched Hermes files with the host record that this operation published.
        host = report.get('host') or {}
        if host.get('state') == 'host_drift':
            raise ReleaseRejected('The bridge reports changed Hermes files after publication: '
                                  + ', '.join(host.get('changed') or [host.get('reason', 'lifeos-host.json')]))
