# ABOUTME: Decides, without changing anything, whether LifeOS can patch the running Hermes installation.
# ABOUTME: Checks layout, exact upstream commit, every patch target's file hash, profiles, and dependencies.
from __future__ import annotations

import copy
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys


MANIFEST = Path(__file__).with_name('host-compatibility.json')
COMMIT = re.compile('[0-9a-f]{40}')
SHA256 = re.compile('[0-9a-f]{64}')
PACKAGE = re.compile('[A-Za-z0-9][A-Za-z0-9._-]*')
EXACT_VERSION = re.compile('[0-9][0-9A-Za-z.+!_-]*')
PYTHON_VERSION = re.compile('[0-9]+\\.[0-9]+')
HOOK = re.compile('[a-z][a-z0-9_]*')
PATH_LIMIT = 50

# Each refusal code maps to the state reported to the owner. Their order is the reporting priority.
STATES = {
    'not_hermes_source': 'unsupported_layout',
    'not_git_checkout': 'unsupported_layout',
    'packaged_install': 'unsupported_layout',
    'foreign_owner': 'unsupported_layout',
    'shared_write_access': 'unsupported_layout',
    'read_only_source': 'unsupported_layout',
    'git_unavailable': 'unsupported_layout',
    'unsupported_version': 'unsupported_version',
    'unsupported_interpreter': 'unsupported_version',
    'shared_installation': 'shared_installation',
    'modified_files': 'modified_source',
    'untracked_files': 'modified_source',
    'hidden_changes': 'modified_source',
    'partially_patched': 'partially_patched',
    'patched_without_record': 'patched_without_record',
    'dependency_conflict': 'dependency_conflict',
    'host_drift': 'host_drift',
    'invalid_host_record': 'host_drift',
    'bridge_disabled': 'host_drift',
}

# Environment variables that would make Git inspect a repository other than the selected source.
GIT_REDIRECTS = ('GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE', 'GIT_OBJECT_DIRECTORY', 'GIT_COMMON_DIR',
                 'GIT_ALTERNATE_OBJECT_DIRECTORIES', 'GIT_CEILING_DIRECTORIES', 'GIT_NAMESPACE')


class ManifestRejected(ValueError):
    """The compatibility manifest is malformed, so no installation can be admitted."""


def _reject(message):
    raise ManifestRejected(message)


def _relative_path(value):
    if not isinstance(value, str) or not value or '\\' in value or '\0' in value:
        _reject('Compatibility paths require relative POSIX text')
    path = PurePosixPath(value)
    if path.is_absolute() or path.as_posix() != value or any(part in ('', '.', '..') for part in path.parts):
        _reject('Compatibility paths must stay inside the Hermes source')
    if path.parts[0] == '.git':
        _reject('Compatibility paths cannot name Git metadata')
    return value


def _entry(value):
    if not isinstance(value, dict) or set(value) != {'label', 'commit', 'patches', 'files'}:
        _reject('Each Hermes entry requires a label, commit, patches, and files')
    label = value['label']
    if not isinstance(label, str) or not label.strip() or len(label) > 64 or any(ord(c) < 32 for c in label):
        _reject('Each Hermes entry requires a bounded label')
    if not isinstance(value['commit'], str) or COMMIT.fullmatch(value['commit']) is None:
        _reject('Each Hermes entry requires a full upstream commit')
    patches = value['patches']
    if not isinstance(patches, list) or not patches:
        _reject('Each Hermes entry requires its ordered patch identities')
    for patch in patches:
        if (not isinstance(patch, dict) or set(patch) != {'name', 'sha256'} or not isinstance(patch['name'], str)
                or re.fullmatch(r'[A-Za-z0-9._-]+\.patch', patch['name']) is None
                or not isinstance(patch['sha256'], str) or SHA256.fullmatch(patch['sha256']) is None):
            _reject('Each patch identity requires a patch name and SHA-256')
    files = value['files']
    if not isinstance(files, dict) or not files:
        _reject('Each Hermes entry requires its patch target hashes')
    for path, hashes in files.items():
        _relative_path(path)
        if not isinstance(hashes, dict) or set(hashes) != {'stock', 'patched'}:
            _reject('Each patch target requires stock and patched hashes')
        stock, patched = hashes['stock'], hashes['patched']
        if not isinstance(patched, str) or SHA256.fullmatch(patched) is None:
            _reject('Each patch target requires a patched SHA-256')
        if stock is not None and (not isinstance(stock, str) or SHA256.fullmatch(stock) is None):
            _reject('Each patch target requires a stock SHA-256 or null for an added file')
        if stock == patched:
            _reject('A patch target must change its file')
    return value


def _capabilities(value):
    if not isinstance(value, dict) or set(value) != {'hooks', 'middleware_api'}:
        _reject('Each Hermes entry requires its hook and middleware capabilities')
    hooks = value['hooks']
    if (not isinstance(hooks, list) or not hooks or len(set(map(str, hooks))) != len(hooks)
            or any(not isinstance(hook, str) or HOOK.fullmatch(hook) is None for hook in hooks)):
        _reject('Each Hermes entry requires distinct hook names')
    if type(value['middleware_api']) is not int or value['middleware_api'] < 1:
        _reject('Each Hermes entry requires a middleware API version')


def _known_conflicts(value):
    if (not isinstance(value, list) or len(value) > 20 or len(set(map(str, value))) != len(value)
            or any(not isinstance(item, str) or not item.strip() or len(item) > 300
                   or any(ord(c) < 32 for c in item) for item in value)):
        _reject('Known conflicts require distinct bounded sentences')


def _qualified_entry(value):
    """Validate a manifest entry: the host identity, the interpreter, the capabilities, and any known conflicts."""
    required = {'label', 'commit', 'patches', 'files', 'python', 'capabilities'}
    if not isinstance(value, dict) or not required <= set(value) <= required | {'known_conflicts'}:
        _reject('Each Hermes entry requires a label, commit, patches, files, python, and capabilities')
    _entry({key: value[key] for key in ('label', 'commit', 'patches', 'files')})
    if not isinstance(value['python'], str) or PYTHON_VERSION.fullmatch(value['python']) is None:
        _reject('Each Hermes entry requires its Python major and minor version')
    _capabilities(value['capabilities'])
    if 'known_conflicts' in value:
        _known_conflicts(value['known_conflicts'])
    return value


def _dependency(value):
    if (not isinstance(value, dict) or set(value) != {'name', 'version'}
            or not isinstance(value['name'], str) or PACKAGE.fullmatch(value['name']) is None
            or not isinstance(value['version'], str) or EXACT_VERSION.fullmatch(value['version']) is None):
        _reject('Each dependency requires a package name and exact version')
    return value


def load_manifest(source=MANIFEST):
    """Return a validated copy of the compatibility manifest from a mapping or a JSON file."""
    if isinstance(source, dict):
        value = copy.deepcopy(source)
    else:
        try:
            value = json.loads(Path(source).read_text())
        except (OSError, ValueError) as error:
            raise ManifestRejected('The compatibility manifest is unavailable or invalid') from error
    if not isinstance(value, dict) or set(value) != {'format', 'hermes', 'dependencies'}:
        _reject('The compatibility manifest requires format, hermes, and dependencies')
    if type(value['format']) is not int or value['format'] != 1:
        _reject('The compatibility manifest format is unsupported')
    if not isinstance(value['hermes'], list) or not value['hermes']:
        _reject('The compatibility manifest requires at least one qualified Hermes entry')
    for entry in value['hermes']:
        _qualified_entry(entry)
    if len({entry['commit'] for entry in value['hermes']}) != len(value['hermes']):
        _reject('Each qualified Hermes commit appears once')
    if not isinstance(value['dependencies'], list):
        _reject('The compatibility manifest requires a dependency list')
    for dependency in value['dependencies']:
        _dependency(dependency)
    return value


def running_source():
    """Return the Hermes source directory that the current interpreter imports."""
    import hermes_cli
    return Path(hermes_cli.__file__).resolve().parent.parent


def _git(source, *arguments):
    environment = {name: value for name, value in os.environ.items() if name not in GIT_REDIRECTS}
    environment.update({'GIT_OPTIONAL_LOCKS': '0', 'GIT_TERMINAL_PROMPT': '0', 'LC_ALL': 'C'})
    command = ['git', '--no-optional-locks', '-c', 'core.fsmonitor=false', '-c', 'core.untrackedCache=false',
               '-C', str(source), *arguments]
    try:
        result = subprocess.run(command, capture_output=True, env=environment, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.stdout if result.returncode == 0 else None


def _reason(code, message, paths=None):
    value = {'code': code, 'message': message}
    if paths is not None:
        value['paths'] = sorted(paths)[:PATH_LIMIT]
        value['count'] = len(paths)
    return value


def _packaged(stamp):
    """Report whether the install stamp names a packager or an updater other than Hermes itself.

    The stock Git bootstrap also writes a stamp, with no distribution and the "self" update mechanism.
    """
    if not stamp.exists() and not stamp.is_symlink():
        return False
    try:
        value = json.loads(stamp.read_text())
    except (OSError, ValueError):
        return True
    return (not isinstance(value, dict) or value.get('distribution') is not None
            or value.get('updateMechanism') != 'self')


def _layout(source):
    reasons = []
    if not all((source / name).exists() for name in ('hermes_cli', 'run_agent.py', 'pyproject.toml')):
        return [_reason('not_hermes_source', 'The selected directory is not a Hermes source checkout.')]
    if _packaged(source / 'install-stamp.json'):
        reasons.append(_reason('packaged_install',
            'This Hermes is a packaged build (Docker, Nix, or the desktop app). Its packager owns the files.'))
    metadata = source / '.git'
    if metadata.is_symlink() or not metadata.is_dir():
        reasons.append(_reason('not_git_checkout',
            'Hermes is not a standalone Git checkout. LifeOS supports the default Git installation only.'))
    info = source.stat()
    if info.st_uid != os.getuid():
        reasons.append(_reason('foreign_owner', 'Another account owns the Hermes source.'))
    if info.st_mode & 0o022:
        reasons.append(_reason('shared_write_access', 'Other accounts can write to the Hermes source.'))
    if not os.access(source, os.W_OK):
        reasons.append(_reason('read_only_source', 'This account cannot write to the Hermes source.'))
    return reasons


def _shared(hermes_home):
    hermes_home = Path(hermes_home).absolute()
    if hermes_home.parent.name == 'profiles':
        return _reason('shared_installation',
            'Hermes runs a named profile. LifeOS supports a single-profile installation only.',
            [hermes_home.name])
    profiles = hermes_home / 'profiles'
    names = [path.name for path in profiles.iterdir() if path.is_dir()] if profiles.is_dir() else []
    if names:
        return _reason('shared_installation',
            'Other Hermes profiles share this source. LifeOS supports a single-profile installation only.',
            names)
    return None


def _file_digest(path):
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except FileNotFoundError:
        return None
    except OSError:
        return 'unreadable'
    with os.fdopen(descriptor, 'rb') as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            return 'unreadable'
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def _targets(source, files):
    stock, patched, other = [], [], []
    for path, hashes in files.items():
        target = source / path
        actual = 'unreadable' if target.is_symlink() else _file_digest(target)
        if actual == hashes['stock']:
            stock.append(path)
        elif actual == hashes['patched']:
            patched.append(path)
        else:
            other.append(path)
    return stock, patched, other


def _exposed_targets(source, files):
    """Return patch targets, or the directories that receive added files, outside this account's sole control."""
    exposed = []
    for path in files:
        target = source / path
        if target.is_symlink():
            continue
        try:
            info = (target if target.exists() else target.parent).lstat()
        except FileNotFoundError:
            continue
        if info.st_uid != os.getuid() or info.st_mode & 0o022:
            exposed.append(path)
    return exposed


def _working_tree(source, targets):
    """Return tracked edits, untracked files, and Git-hidden paths outside the patch targets."""
    status = _git(source, 'status', '--porcelain=v1', '-z', '--untracked-files=all', '--ignore-submodules=none')
    flags = _git(source, 'ls-files', '-v', '-z')
    if status is None or flags is None:
        return None
    modified, untracked = [], []
    records = status.split(b'\0')
    index = 0
    while index < len(records):
        record = records[index].decode(errors='replace')
        index += 1
        if not record:
            continue
        code, path = record[:2], record[3:]
        if 'R' in code or 'C' in code:
            index += 1
        if path in targets:
            continue
        (untracked if code == '??' else modified).append(path)
    hidden = []
    for record in flags.split(b'\0'):
        record = record.decode(errors='replace')
        if record and (record[0] == 'S' or record[0].islower()):
            hidden.append(record[2:])
    return modified, untracked, hidden


def _dependencies(required, search_path):
    installed = {}
    for distribution in importlib.metadata.distributions(path=search_path):
        name = distribution.metadata['Name']
        if name:
            installed.setdefault(re.sub(r'[-_.]+', '-', name).lower(), distribution.version)
    add, conflicts = [], []
    for dependency in required:
        version = installed.get(re.sub(r'[-_.]+', '-', dependency['name']).lower())
        if version is None:
            add.append(dependency['name'] + '==' + dependency['version'])
        elif version != dependency['version']:
            conflicts.append({'name': dependency['name'], 'installed': version, 'required': dependency['version']})
    return {'add': add, 'conflicts': conflicts}


def _result(detected, manifest, reasons, *, qualified=None, dependencies=None, installed=False):
    state = STATES[reasons[0]['code']] if reasons else 'installed' if installed else 'compatible'
    return {
        'format': 1,
        'compatible': not reasons and not installed,
        'installed': not reasons and installed,
        'state': state,
        'reasons': reasons,
        'detected': detected,
        'qualified': qualified,
        'supported': [{'label': entry['label'], 'commit': entry['commit']} for entry in manifest['hermes']],
        'dependencies': dependencies or {'add': [], 'conflicts': []},
    }


def _interpreter(entry, running):
    """Refuse an interpreter other than the one the release qualifies for this Hermes version."""
    if entry is None or entry['python'] == running:
        return None
    return _reason('unsupported_interpreter', 'LifeOS qualifies Hermes ' + entry['label'] + ' with Python '
                   + entry['python'] + '. This Hermes runs Python ' + running + '.')


def _bridge_enabled(hermes_home):
    """Report whether the profile still enables the bridge; Hermes can evict a plugin during a dependency sync."""
    from ruamel.yaml import YAML
    try:
        value = YAML(typ='safe').load((Path(hermes_home) / 'config.yaml').read_text())
    except (OSError, ValueError):
        return False
    plugins = value.get('plugins') if isinstance(value, dict) else None
    if not isinstance(plugins, dict):
        return False
    enabled, disabled = plugins.get('enabled') or [], plugins.get('disabled') or []
    return 'lifeos-hook-bridge' in enabled and 'lifeos-hook-bridge' not in disabled


def _installed_reasons(source, record, head, hermes_home):
    """Compare a host that LifeOS patched with its host record."""
    if record['source'] != str(source) or record['commit'] != head:
        return [_reason('host_drift', 'LifeOS was installed into another Hermes source or version than the one running now.')]
    tree = _working_tree(source, set(record['files']))
    if tree is None:
        return [_reason('git_unavailable', 'Git cannot read the Hermes checkout as this account.')]
    modified, untracked, hidden = tree
    _, patched, other = _targets(source, record['files'])
    reasons = []
    if modified:
        reasons.append(_reason('modified_files', 'Hermes source files differ from the qualified upstream version.', modified))
    if untracked:
        reasons.append(_reason('untracked_files',
            'The Hermes source contains files that are not part of the upstream version.', untracked))
    if hidden:
        reasons.append(_reason('hidden_changes', 'Git is set to ignore changes to some tracked Hermes files.', hidden))
    drifted = sorted(set(record['files']) - set(patched))
    if drifted:
        reasons.insert(0, _reason('host_drift',
            'Some Hermes files that LifeOS patched have changed since installation.', drifted))
    if not _bridge_enabled(hermes_home):
        reasons.append(_reason('bridge_disabled',
            'Hermes no longer enables the LifeOS bridge plugin. A Hermes dependency update can disable a plugin.'))
    return reasons


def inspect_host(source, manifest, *, hermes_home, search_path=None, record=None, python=None):
    """Classify one Hermes installation against the manifest, or against its LifeOS host record, without writing to it.

    ``python`` is the major.minor version of the interpreter that runs Hermes; it defaults to this interpreter.
    """
    source = Path(source).absolute()
    manifest = load_manifest(manifest)
    dependencies = _dependencies(manifest['dependencies'], sys.path if search_path is None else search_path)
    detected = {'source': str(source), 'commit': None, 'version': None, 'profile': str(Path(hermes_home).absolute()),
                'interpreter': sys.executable, 'python': '.'.join(map(str, sys.version_info[:3]))}
    reasons = _layout(source)
    if reasons:
        return _result(detected, manifest, reasons, dependencies=dependencies)
    head = _git(source, 'rev-parse', '--verify', 'HEAD^{commit}')
    version = _git(source, 'describe', '--tags', '--always')
    if head is None or version is None:
        return _result(detected, manifest, [_reason('git_unavailable',
            'Git cannot read the Hermes checkout as this account.')], dependencies=dependencies)
    detected['commit'] = head.decode().strip()
    detected['version'] = version.decode().strip()
    entry = next((item for item in manifest['hermes'] if item['commit'] == detected['commit']), None)
    shared = _shared(hermes_home)
    interpreter = _interpreter(entry, python or '.'.join(map(str, sys.version_info[:2])))
    if record is not None:
        reasons.extend(_installed_reasons(source, record, detected['commit'], hermes_home))
        reasons.extend([interpreter] if interpreter else [])
        reasons.extend([shared] if shared else [])
        if dependencies['conflicts']:
            reasons.append(_reason('dependency_conflict',
                'An installed Python package has a different version than LifeOS requires.',
                [item['name'] for item in dependencies['conflicts']]))
        return _result(detected, manifest, reasons, qualified=record['label'], dependencies=dependencies,
                       installed=True)
    if entry is None:
        reasons.append(_reason('unsupported_version',
            'LifeOS has no qualified patch set for this Hermes version.'))
        reasons.extend([shared] if shared else [])
    else:
        reasons.extend([interpreter] if interpreter else [])
        exposed = _exposed_targets(source, entry['files'])
        if exposed:
            reasons.append(_reason('shared_write_access',
                'Another account owns or can write to some Hermes files that LifeOS changes.', exposed))
        reasons.extend([shared] if shared else [])
        tree = _working_tree(source, set(entry['files']))
        if tree is None:
            return _result(detected, manifest, [_reason('git_unavailable',
                'Git cannot read the Hermes checkout as this account.')], dependencies=dependencies)
        modified, untracked, hidden = tree
        stock, patched, other = _targets(source, entry['files'])
        if modified or other:
            reasons.append(_reason('modified_files',
                'Hermes source files differ from the qualified upstream version.', modified + other))
        if untracked:
            reasons.append(_reason('untracked_files',
                'The Hermes source contains files that are not part of the upstream version.', untracked))
        if hidden:
            reasons.append(_reason('hidden_changes',
                'Git is set to ignore changes to some tracked Hermes files.', hidden))
        if not other and stock and patched:
            reasons.append(_reason('partially_patched',
                'Some LifeOS changes are already present. The installation is incomplete.', patched))
        if not other and patched and not stock:
            reasons.append(_reason('patched_without_record',
                'LifeOS changes are present, but this installation has no LifeOS installation record.'))
    if dependencies['conflicts']:
        reasons.append(_reason('dependency_conflict',
            'An installed Python package has a different version than LifeOS requires.',
            [item['name'] for item in dependencies['conflicts']]))
    return _result(detected, manifest, reasons, qualified=entry and entry['label'], dependencies=dependencies)


def transition_source(hermes_home, source=None):
    """Return the stock checkout that replaces a managed LifeOS runtime, or None when Hermes is not managed.

    A managed release runs Hermes from ``<profile>/.lifeos-releases/<operation>/hermes``. Its transition
    target is the stock Git installation at ``<profile>/hermes-agent``, which the official installer creates.
    """
    profile = Path(hermes_home).absolute()
    source = running_source() if source is None else Path(source).absolute()
    releases = profile / '.lifeos-releases'
    if (source.name != 'hermes' or source.parent.parent != releases
            or re.fullmatch('[0-9a-f]{32}', source.parent.name) is None):
        return None
    return profile / 'hermes-agent'


def check(hermes_home, *, manifest=MANIFEST, search_path=None):
    """Inspect the Hermes installation that runs this process, or the stock checkout that replaces a managed runtime."""
    from .host_record import HostRecordRejected, load_record, record_path
    target = transition_source(hermes_home)
    source, manifest = target or running_source(), load_manifest(manifest)
    try:
        record = load_record(hermes_home)
    except HostRecordRejected as error:
        # A damaged record is drift: nothing can compare the host with what LifeOS installed.
        result = inspect_host(source, manifest, hermes_home=hermes_home, search_path=search_path)
        reason = _reason('invalid_host_record', str(error) + ': ' + str(record_path(hermes_home)) + '.')
        result.update(state='host_drift', compatible=False, installed=False, reasons=[reason, *result['reasons']])
    else:
        result = inspect_host(source, manifest, hermes_home=hermes_home, search_path=search_path, record=record)
    result['transition'] = target is not None
    return result
