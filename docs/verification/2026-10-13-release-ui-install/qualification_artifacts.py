# ABOUTME: Binds qualification inputs and numerical test releases to exact archive contents.
# ABOUTME: Distinguishes generated test bytecode from archived programs and checks permitted version changes.
import hashlib
import importlib.util
import json
from pathlib import Path, PurePosixPath
import stat
import tarfile

DECLARATIONS = ('VERSION', 'lifeos_hook_bridge/plugin.yaml', 'lifeos_hook_bridge/dashboard/manifest.json',
    'optional/lifeos_release_manager/plugin.yaml', 'optional/lifeos_release_manager/dashboard/manifest.json')
CHANGELOG_ADDITION = b'# Changelog\n\n## 0.4.2-rc.2 (unpublished version-only test candidate)\n\n- Change the complete integration version to verify a numerical update through Hermes and both dashboard update controls.\n- Keep the program behavior from the corrected 0.4.2-rc.1 candidate.\n'


def archive_contents(path):
    files, names, total = {}, set(), 0
    with tarfile.open(path) as archive:
        for number, member in enumerate(archive, 1):
            name = member.name.rstrip('/')
            relative = PurePosixPath(name)
            total += member.size
            if (number > 100000 or total > 5 * 1024 ** 3 or not name or '\\' in name
                    or relative.is_absolute() or str(relative) != name
                    or any(part in {'.', '..'} for part in relative.parts) or name in names
                    or not (member.isdir() or member.isfile())):
                raise ValueError('The qualification archive has an unsupported member')
            names.add(name)
            if member.isfile():
                data = archive.extractfile(member).read()
                files[name] = {'data': data, 'sha256': hashlib.sha256(data).hexdigest(),
                               'mode': 0o700 if member.mode & 0o111 else 0o600}
    return files


def archive_files(path):
    return {name: {key: value[key] for key in ('sha256', 'mode')}
            for name, value in archive_contents(path).items()}


def file_map_digest(files):
    return hashlib.sha256(json.dumps(files, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def package_matches(root, expected, *, allow_generated=False):
    root = Path(root)
    for name, value in expected.items():
        path = root / name
        info = path.lstat()
        if (not stat.S_ISREG(info.st_mode) or path.resolve() != path
                or stat.S_IMODE(info.st_mode) != value['mode']
                or hashlib.sha256(path.read_bytes()).hexdigest() != value['sha256']):
            raise ValueError('A qualification archived file changes: ' + name)
    caches = 0
    metadata = []
    for path in root.rglob('*'):
        if path.is_dir() and not path.is_symlink():
            continue
        name = path.relative_to(root).as_posix()
        if name in expected:
            continue
        if allow_generated and path.is_file() and not path.is_symlink():
            if name == 'hermes/.bytecode-fingerprint':
                metadata.append(name)
                continue
            if '__pycache__' in path.parts and path.suffix == '.pyc':
                try:
                    source = Path(importlib.util.source_from_cache(str(path))).relative_to(root).as_posix()
                except (ValueError, NotImplementedError):
                    source = None
                if source in expected:
                    caches += 1
                    continue
        raise ValueError('A qualification package has an unexpected file: ' + name)
    return {'generated_bytecode_files': caches, 'generated_metadata_files': metadata}


def version_derivative(first_archive, second_archive, first_commit, second_commit):
    first, second = archive_contents(first_archive), archive_contents(second_archive)
    if set(first) != set(second):
        raise ValueError('The numerical candidate changes its archive members')
    for name in DECLARATIONS:
        before, after = first[name]['data'], second[name]['data']
        if before.count(b'0.4.2-rc.1') != 1 or after != before.replace(b'0.4.2-rc.1', b'0.4.2-rc.2'):
            raise ValueError('The numerical candidate changes a version declaration: ' + name)
    if second['CHANGELOG.md']['data'] != first['CHANGELOG.md']['data'].replace(b'# Changelog\n', CHANGELOG_ADDITION, 1):
        raise ValueError('The numerical candidate changes its release notes')
    before = json.loads(first['DAILY-CANDIDATE.json']['data'])
    after = json.loads(second['DAILY-CANDIDATE.json']['data'])
    expected = dict(before, version='0.4.2-rc.2', head=second_commit,
        plugin_files={name: value['sha256'] for name, value in second.items() if name.startswith('lifeos_hook_bridge/')},
        manager_files={name.removeprefix('optional/lifeos_release_manager/'): value['sha256']
                       for name, value in second.items() if name.startswith('optional/lifeos_release_manager/')})
    if before['version'] != '0.4.2-rc.1' or before['head'] != first_commit or after != expected:
        raise ValueError('The numerical candidate changes its candidate manifest')
    for name, value in first.items():
        if name in (*DECLARATIONS, 'CHANGELOG.md', 'DAILY-CANDIDATE.json'):
            continue
        git_metadata = any(name == prefix + 'index' or name.startswith(prefix + 'logs/')
                           for prefix in ('hermes/.git/', 'lifeos/.git/'))
        if not git_metadata and (value['sha256'], value['mode']) != (second[name]['sha256'], second[name]['mode']):
            raise ValueError('The numerical candidate changes another archived file: ' + name)
    return {'exact_version_transformations': True, 'native_and_dependency_programs_identical': True}
