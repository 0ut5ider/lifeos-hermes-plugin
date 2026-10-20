# ABOUTME: Binds complete software removal to the applied in-place operation that the LifeOS host record names.
# ABOUTME: Plans the restoration of the original Hermes files and runs removal commands with the restored host.
from __future__ import annotations

import json
from pathlib import Path
import re
import shutil

from .cli import profile_directory, read_private
from .host_compatibility import inspect_host, load_manifest
from .host_configuration import RECORD as CONFIGURATION_RECORD
from .host_record import HostRecordRejected, check_originals, load_record, originals_path, record_path
from .inplace_plan import HOLD
from .integration_package import COMPATIBILITY, validate_integration
from .release_catalog import ReleaseRejected, parse_json
from .release_programs import fingerprint, publish
from .release_stage import validate_files, sha


IDENTIFIER = re.compile('[0-9a-f]{32}')


def _refusal(result):
    """Return the first compatibility refusal with the paths that it names."""
    reasons = result['reasons']
    if not reasons:
        return 'The Hermes installation is not in its recorded LifeOS state.'
    reason = reasons[0]
    paths = reason.get('paths') or []
    return reason['message'] + (' ' + ', '.join(paths) if paths else '')


def installed_host(profile, record, manifest):
    """Verify that the recorded host still carries exactly the LifeOS patches; return the retained originals."""
    result = inspect_host(record['source'], manifest, hermes_home=profile, record=record)
    # A bridge that Hermes evicted is a reason to remove LifeOS, not a reason to refuse removal.
    reasons = [reason for reason in result['reasons'] if reason['code'] != 'bridge_disabled']
    if reasons or not (result['installed'] or result['state'] == 'host_drift'):
        raise ReleaseRejected('Removal refuses the current Hermes installation: ' + _refusal({**result, 'reasons': reasons}))
    try:
        return check_originals(record)
    except HostRecordRejected as error:
        raise ReleaseRejected(str(error)) from error


def selected(profile, installed, *, bridge):
    """Return the removal generation for the applied in-place operation that the host record names."""
    from .removal_generation import account
    profile = profile_directory(profile)
    home = account(profile, installed)
    try:
        record = load_record(profile)
    except HostRecordRejected as error:
        raise ReleaseRejected(str(error)) from error
    if record is None:
        raise ReleaseRejected('In-place removal requires the LifeOS host record')
    identity = read_private(profile / 'integration-release.json')
    active = bridge.memory_module('release_version').status(profile, profile / 'plugins/lifeos-hook-bridge')['active']
    if active['verification'] != 'verified':
        raise ReleaseRejected('The active bridge differs from its complete release')
    roots = profile / '.lifeos-releases'
    job = roots / record['operation']
    if (IDENTIFIER.fullmatch(record['operation']) is None or roots.resolve() != roots
            or job.resolve() != job or not job.is_dir()):
        raise ReleaseRejected('The in-place operation that the host record names is unavailable')
    request = read_private(job / 'request.json')
    status = read_private(job / 'status.json')
    host = request.get('host') if isinstance(request.get('host'), dict) else {}
    if (status.get('state') != 'applied' or request.get('format') != 2 or request.get('identifier') != job.name
            or request.get('profile') != str(profile) or request.get('installed') != str(Path(installed).absolute())
            or any(request.get(key) != identity.get(key) for key in ('version', 'commit', 'package_sha256'))
            or record['version'] != request.get('version')
            or host.get('source') != record['source'] or host.get('commit') != record['commit']):
        raise ReleaseRejected('Removal requires the applied in-place operation that the host record names')
    package = job / 'package'
    manifest = validate_integration(package, request['certificate'])
    validate_files(profile / 'plugins/lifeos-hook-bridge', manifest['plugin_files'])
    validate_files(profile / 'plugins/lifeos-release-manager', manifest['manager_files'])
    originals = installed_host(profile, record, load_manifest(package / COMPATIBILITY))
    bun = home / '.local/bin/bun'
    bun_identity = fingerprint(Path(request['runtime']['bun']))
    if bun_identity is None or fingerprint(bun) != bun_identity:
        raise ReleaseRejected('The account Bun command differs from its integration-owned program')
    return {'home': home, 'job': job, 'request': request, 'package': package, 'manifest': manifest,
            'bridge_files': manifest['plugin_files'], 'manager_files': manifest['manager_files'], 'launchers': {},
            'bun': bun, 'bun_identity': bun_identity, 'record': record, 'originals': originals,
            'native_source': job / 'lifeos/LifeOS/install', 'reference': Path(request['runtime']['reference'])}


def host_plan(profile, record, originals, stage):
    """Return the directories, files, and reviewed identities that restore the recorded Hermes files.

    Each patched target returns to a verified copy of its retained original, with the original mode, or is
    deleted when LifeOS added it. The retained originals, the host record, and the update hold (when present) are removed.
    """
    profile, stage = Path(profile).absolute(), Path(stage)
    source = Path(record['source'])
    copies = stage / 'host-originals'
    copies.mkdir(mode=0o700)
    directories, files, expected = {}, {}, {}
    for relative, hashes in sorted(record['files'].items()):
        target = source / relative
        identity = fingerprint(target)
        if (target.parent.resolve() != target.parent or identity is None or identity['type'] != 'file'
                or identity['sha256'] != hashes['patched']):
            raise ReleaseRejected('A Hermes file changed after LifeOS patched it; restore it before removal: ' + relative)
        expected[target] = identity
        if hashes['stock'] is None:
            files[target] = None
            continue
        copy = copies / relative
        copy.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        shutil.copy2(originals[relative], copy)
        if sha(copy) != hashes['stock']:
            raise ReleaseRejected('A retained original Hermes file changed: ' + relative)
        files[target] = copy
    retained = originals_path(profile).parent
    owned = {originals_path(profile) / relative for relative, hashes in record['files'].items()
             if hashes['stock'] is not None}
    configuration_record = profile / CONFIGURATION_RECORD
    if configuration_record.is_file() and not configuration_record.is_symlink():
        owned.add(configuration_record)
    found = set()
    for path in retained.rglob('*'):
        if path.is_symlink() or not (path.is_dir() or path.is_file()):
            raise ReleaseRejected('The retained Hermes originals contain an unsupported entry')
        if path.is_file():
            found.add(path)
    if retained.resolve() != retained or found != owned:
        raise ReleaseRejected('The retained Hermes originals contain files that the host record does not name')
    directories[retained] = None
    expected[retained] = fingerprint(retained)
    record = record_path(profile)
    identity = fingerprint(record)
    if identity is None or identity['type'] != 'file':
        raise ReleaseRejected('Removal requires the LifeOS host record')
    files[record] = None
    expected[record] = identity
    hold = source / '.git' / HOLD
    identity = fingerprint(hold)
    # A missing hold only means Hermes updates are already admitted; it does not affect source restoration.
    if identity is None:
        return directories, files, expected
    if identity['type'] != 'file':
        raise ReleaseRejected('The Hermes update hold is not a regular file')
    files[hold] = None
    expected[hold] = identity
    try:
        holder = json.loads(hold.read_bytes()).get('holder')
    except (ValueError, AttributeError) as error:
        raise ReleaseRejected('The Hermes update hold is unreadable') from error
    if holder != 'LifeOS':
        raise ReleaseRejected('The Hermes update hold belongs to another integration')
    return directories, files, expected


def check_host_files(entries, source):
    """Refuse when a Hermes file differs from both its reviewed patched state and its restored original."""
    source = Path(source)
    for entry in entries:
        target = Path(entry['target'])
        if not target.is_relative_to(source) or target.is_relative_to(source / '.git'):
            continue
        if fingerprint(target, allow_links=entry['allow_links']) not in (entry['before'], entry['after']):
            raise ReleaseRejected('A Hermes file changed after the removal review: ' + str(target.relative_to(source)))


def runtime(plan):
    """Return the restored host that runs removal commands; Hermes selects its environment at each start."""
    from .inplace_preparation import host_launcher
    source = Path(plan['host']['source'])
    unavailable = 'The Hermes installation is unavailable for removal commands'
    if not source.is_absolute() or source.resolve() != source or not source.is_dir():
        raise ReleaseRejected(unavailable)
    try:
        launcher = host_launcher(source)
    except ReleaseRejected as error:
        raise ReleaseRejected(unavailable) from error
    return {'kind': 'host', 'source': str(source), 'hermes': str(launcher)}


def command(selected, arguments, *, code):
    """Return a command that runs ``code`` with the host source and the environment Hermes selects at start."""
    # hermes_cli._launchers is a private module of the pinned Hermes v0.21.7.
    from hermes_cli import _launchers
    result = _launchers.runtime_command(Path(selected['source']), [str(item) for item in arguments], code=code)
    result.insert(1, '-B')
    return result


def synchronize(stage, plan, label):
    """Commit the dependency generation for the published configuration; return the package changes."""
    from .dependency_plan import locked_packages, selected_lock
    from .inplace_preparation import host_python
    from .release_accounts import account_home
    from .release_stage import stage_environment, run_stage, user_runtime_directory
    source, profile = Path(plan['host']['source']), Path(plan['profile'])
    before = locked_packages(selected_lock(source))
    output = stage / (label + '.json')
    output.unlink(missing_ok=True)
    environment = {**stage_environment(profile, home=account_home(profile), source=source),
                   'XDG_RUNTIME_DIR': user_runtime_directory(),
                   'DBUS_SESSION_BUS_ADDRESS': 'unix:path=' + user_runtime_directory() + '/bus'}
    run_stage([host_python(source), '-B', stage / 'recovery-manager/dependency_plan.py', 'synchronize', source, output],
              stage, label, environment=environment)
    after = locked_packages(selected_lock(source))
    value = {**parse_json(output.read_bytes()), 'removed': sorted(set(before) - set(after)),
             'added': sorted(set(after) - set(before))}
    publish(stage / (label + '-packages.json'), (json.dumps(value, indent=2, sort_keys=True) + '\n').encode())
    return value


def recorded_configuration(profile):
    """Return the record of configuration values LifeOS changed, or None for an installation without one."""
    path = Path(profile) / CONFIGURATION_RECORD
    if not path.is_file() or path.is_symlink():
        return None
    try:
        value = json.loads(path.read_bytes())
    except ValueError as error:
        raise ReleaseRejected('The LifeOS configuration record is unreadable') from error
    if not isinstance(value, dict) or value.get('format') != 1 or not isinstance(value.get('values'), list):
        raise ReleaseRejected('The LifeOS configuration record has an invalid structure')
    return value
