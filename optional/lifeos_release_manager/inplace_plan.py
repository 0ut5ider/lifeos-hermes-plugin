# ABOUTME: Binds an in-place operation to the running Hermes host and plans its host file publication.
# ABOUTME: Rechecks the host, the staged patches, LifeOS, the services, and the consumers before any change.
from __future__ import annotations

import json
from pathlib import Path

from .host_compatibility import inspect_host, load_manifest
from .host_record import build_record, check_originals, load_record, originals_path, record_path
from .inplace_preparation import GATEWAY_UNIT, TRANSITION_GATEWAY, desired_host_files, host_launcher
from .inplace_services import UNITS, ancestors, inventory
from .integration_package import COMPATIBILITY, validate_integration
from .release_accounts import account_home
from .release_catalog import ReleaseRejected
from .release_programs import publish
from .release_stage import load_bridge, runtime_source_fingerprint, sha


HOLD = 'hermes-update-holds/lifeos.json'
HOLD_MESSAGE = ('LifeOS patches this Hermes installation. Updating Hermes now would move those patches onto an '
                'untested version. Remove LifeOS first, or wait for a LifeOS release that supports the new Hermes version.')


def archive_name(request):
    return 'lifeos-integration-' + request['version'] + '-' + request['commit'][:8] + '.tgz'


def staged_files(job, entry):
    """Return the verified staged host files of ``entry`` from ``job/host``."""
    host = job / 'host'
    staged = {}
    for relative, hashes in entry['files'].items():
        patched = host / 'patched' / relative
        stock = host / 'stock' / relative
        if patched.is_symlink() or not patched.is_file() or sha(patched) != hashes['patched']:
            raise ReleaseRejected('A staged patched Hermes file changed after preparation: ' + relative)
        if hashes['stock'] is not None and (stock.is_symlink() or not stock.is_file() or sha(stock) != hashes['stock']):
            raise ReleaseRejected('A staged original Hermes file changed after preparation: ' + relative)
        staged[relative] = {'patched': patched, 'stock': None if hashes['stock'] is None else stock}
    return staged


def inspect_inplace(job, request, *, installation_lease=None, fresh_recovery=False):
    """Return the selection for an in-place operation, refusing any change since preparation."""
    profile, source = Path(request['profile']), Path(request['host']['source'])
    package = job / 'package'
    validate_integration(package, request['certificate'])
    if sha(job / 'download' / archive_name(request)) != request['package_sha256']:
        raise ReleaseRejected('The integration archive changes before selection')
    # The host interpreter moves to a new environment generation at every dependency synchronization,
    # so it is resolved from the host whenever it is used and is not a fixed path.
    expected = {'bun': str(job / 'tools/bun'), 'hermes': str(host_launcher(source)),
                'source': str(job / 'hermes-preview'), 'reference': str(job / 'reference-home/.claude'),
                'lifeos': str(job / 'lifeos'), 'host_files': str(job / 'host')}
    if {key: value for key, value in request['runtime'].items() if key != 'python'} != expected:
        raise ReleaseRejected('The prepared runtime changes its fixed paths')
    if runtime_source_fingerprint(job / 'hermes-preview') != request['runtime_fingerprint']:
        raise ReleaseRejected('The prepared preview changes before selection')
    # The worker imports the preview, so it inspects the recorded host source explicitly.
    host = inspect_host(source, load_manifest(package / COMPATIBILITY), hermes_home=profile, record=load_record(profile))
    record_file = record_path(profile)
    record_digest = sha(record_file) if record_file.exists() else None
    if host['detected']['source'] != str(source) or host['detected']['commit'] != request['host']['commit']:
        raise ReleaseRejected('The Hermes installation changes after preparation; prepare the operation again')
    # Forward recovery finds a partly published host; the program journal checks each file's identity instead.
    if not fresh_recovery:
        if host['state'] != request['host']['state'] or record_digest != request['host']['record_sha256']:
            raise ReleaseRejected('The Hermes installation changes after preparation; prepare the operation again')
        from .dependency_plan import selected_lock
        if sha(selected_lock(source)) != request['dependencies']['seed_sha256']:
            raise ReleaseRejected('The Hermes Python environment changes after preparation; prepare the operation again')
    entry = next((item for item in load_manifest(package / COMPATIBILITY)['hermes']
                  if item['commit'] == request['host']['commit']), None)
    if entry is None:
        raise ReleaseRejected('The integration release no longer supports the installed Hermes version')
    staged = staged_files(job, entry)
    candidate = load_bridge(package / 'lifeos_hook_bridge')
    lifeos = candidate.validate_candidate(job / 'lifeos', request['certificate']['lifeos']['commit'],
                                          package / 'lifeos_hook_bridge/patches', candidate.LIFEOS_PATCHES)
    if lifeos['tree_sha256'] != request['certificate']['lifeos']['tree_sha256']:
        raise ReleaseRejected('The prepared LifeOS tree differs from its qualified identity')
    selected = candidate.memory_module('lifeos_installation').selection(profile)
    installed = selected.installed
    home = account_home(profile)
    if (str(installed) != request['installed'] or Path(request['account_home']) != home
            or request['identifier'] != job.name or job.parent != profile / '.lifeos-releases'):
        raise ReleaseRejected('The operation changes its profile or installation binding')
    bridge = profile / 'plugins/lifeos-hook-bridge'
    fresh = fresh_recovery or not installed.exists()
    current = candidate if fresh else load_bridge(bridge) if bridge.is_dir() else candidate
    baseline = current.memory_module('version_drift').default_baseline_path(installed.parent)
    result = {'profile': profile, 'installed': installed, 'candidate': candidate, 'current': current,
              'bridge': bridge, 'baseline': baseline, 'package': package, 'fresh': fresh,
              'native': job / 'lifeos/LifeOS/install', 'entry': entry, 'staged': staged, 'source': source}
    if fresh and not fresh_recovery and (installed.is_symlink() or selected.user_data.exists()
            or selected.user_data.is_symlink() or (profile / 'lifeos-memory.json').exists()):
        raise ReleaseRejected('Fresh installation requires an empty native destination without existing personal data')
    # The command or preparation process that runs this review is the operator, not a consumer to stop.
    consumers = inventory(source, Path(request['host']['state_directory']), operators=ancestors())
    # Forward recovery repeats the consumer stop in the worker; the services may already be stopped.
    if consumers['blocking'] and not fresh_recovery:
        from .consumer_scan import process_names
        raise ReleaseRejected('Close these Hermes processes before the operation: ' + process_names(consumers['blocking']))
    roles = [role for role in ('gateway', 'dashboard', 'pulse') if role in consumers['bound']]
    created = list(consumers['offers'])
    if fresh:
        created.append('pulse')
    # The operation's own bridge controls services: an installed managed bridge predates role selection.
    services = candidate.memory_module('profile_services').ProfileServices(
        profile, installed, units={role: UNITS[role] for role in roles}, roles=roles,
        installation_lease=installation_lease, first_installation=fresh) if roles else None
    # A transition verifies through the account launcher that the existing services start.
    launcher = home / '.local/bin/hermes' if request['host'].get('transition') else host_launcher(source)
    result.update(services={'roles': roles, 'created': created, 'consumers': consumers['consumers'],
                            'active': {role: consumers['active'][role] for role in roles},
                            'enabled': {role: consumers['enabled'][role] for role in roles},
                            'signature': None if services is None or fresh_recovery else services.preview()['signature']},
                  created_roles=tuple(created), launchers=[str(launcher)],
                  dashboard_options=consumers['dashboard_options'] if 'dashboard' in created else {})
    if fresh:
        result['native_changes'] = True
    else:
        from .release_plan import existing_native
        result.update(existing_native(result, request, result['native']))
    return result


def host_entries(job, request, selected, generated):
    """Return the in-place directory and file publication entries for the host, its record, and its hold."""
    profile, source, entry = selected['profile'], selected['source'], selected['entry']
    record = load_record(profile)
    originals = check_originals(record) if record is not None else None
    staged = selected['staged']
    desired = desired_host_files(entry, staged, record, originals)
    files = {source / relative: path for relative, path in desired.items()}
    retained = originals_path(profile)
    for relative, value in staged.items():
        if value['stock'] is not None:
            files[retained / relative] = value['stock']
    if record is not None:
        for relative, path in originals.items():
            files.setdefault(retained / relative, path)
    value = build_record(profile, source, entry, operation=job.name, version=request['version'])
    publish(generated / 'lifeos-host.json', (json.dumps(value, indent=2, sort_keys=True) + '\n').encode())
    files[record_path(profile)] = generated / 'lifeos-host.json'
    publish(generated / 'update-hold.json', (json.dumps({'holder': 'LifeOS', 'message': HOLD_MESSAGE}) + '\n').encode())
    files[source / '.git' / HOLD] = generated / 'update-hold.json'
    if request['host'].get('transition'):
        files.update(transition_launchers(Path(request['account_home']), source, generated))
        files.update(transition_unit_files(Path(request['account_home']), job, request['host'].get('transition_units', {})))
    return {}, files


REVIEW = 'inplace-review.json'


def update_difference(record, entry):
    """Return the host targets an update adds, changes, and returns to their originals; None for a first installation."""
    if record is None:
        return None
    before, after = record['files'], entry['files']
    return {'added': sorted(set(after) - set(before)),
            'changed': sorted(path for path in set(after) & set(before) if after[path]['patched'] != before[path]['patched']),
            'restored': sorted(set(before) - set(after))}


def review_changes(job, entry, record, current, generated):
    """Record for the owner review every configuration key that changes and the update's host difference."""
    from .host_configuration import parse_configuration, changed_paths
    keys = changed_paths(parse_configuration(Path(current).read_bytes()), parse_configuration(Path(generated).read_bytes()))
    value = {'configuration': ['.'.join(map(str, path)) for path, _, _ in keys],
             'update': update_difference(record, entry)}
    publish(job / REVIEW, (json.dumps(value, indent=2, sort_keys=True) + '\n').encode())
    return value


def transition_unit_files(home, job, units):
    """Map the reviewed stock gateway unit of a transition to its publication source."""
    if 'gateway' not in units:
        return {}
    generated = job / TRANSITION_GATEWAY
    if sha(generated) != units['gateway']['after']:
        raise ReleaseRejected('The transition gateway unit differs from the reviewed definition')
    return {home / GATEWAY_UNIT: generated}


def transition_launchers(home, source, generated):
    """Point the account commands at the stock checkout with the forwarders Hermes itself publishes."""
    import shlex
    commands = {'hermes': [source / '.hermes/bin/hermes'],
                'hermes-agent': [source / '.hermes/bin/hermes', '--run-module', 'run_agent'],
                'hermes-acp': [source / '.hermes/bin/hermes-acp']}
    files = {}
    for name, command in commands.items():
        script = generated / ('launcher-' + name)
        publish(script, ('#!/bin/sh\nexec ' + ' '.join(shlex.quote(str(part)) for part in command) + ' "$@"\n').encode(), 0o755)
        files[home / '.local/bin' / name] = script
    return files
