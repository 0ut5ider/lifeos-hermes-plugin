# ABOUTME: Verifies omitted native program baselines against the accepted integration archive.
# ABOUTME: Preserves recorded hashes and refuses later edits without changing installed state.
import hashlib
import os
from pathlib import Path
import re
import stat
import tarfile

from .release_catalog import MAX_ARCHIVE_BYTES, MAX_EXTRACTED_BYTES, MAX_MEMBERS, VERSION


def _digest(stream):
    digest = hashlib.sha256()
    for data in iter(lambda: stream.read(1024 * 1024), b''):
        digest.update(data)
    return digest.hexdigest()


def _archive(profile, baseline, active, conflict):
    version, commit, digest = (active.get(key) for key in ('version', 'commit', 'package_sha256'))
    if (active.get('verification') != 'verified' or not isinstance(version, str)
            or VERSION.fullmatch(version) is None or not isinstance(commit, str)
            or re.fullmatch('[0-9a-f]{40}', commit) is None or not isinstance(digest, str)
            or re.fullmatch('[0-9a-f]{64}', digest) is None):
        raise conflict('The omitted program baseline requires an exact accepted release')
    source = Path(baseline['source_root'])
    if len(source.parents) < 3:
        raise conflict('The accepted native source has no fixed package boundary')
    package = source.parents[2]
    if source != package / 'lifeos/LifeOS/install' or source.resolve() != source:
        raise conflict('The accepted native source changes its package boundary')
    name = version + '-' + commit[:8]
    if package.name == name:
        path = package.parent / (name + '.tgz')
    elif (package.name == 'package' and package.parent.parent == profile / '.lifeos-releases'
            and re.fullmatch('[0-9a-f]{32}', package.parent.name)):
        path = package.parent / 'download' / (name + '.tgz')
    else:
        raise conflict('The accepted archive has no fixed retained location')
    if path.parent.resolve() != path.parent:
        raise conflict('The accepted archive changes its physical directory')
    return path


def _check_archive(info, conflict):
    if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_nlink != 1
            or info.st_mode & 0o022 or not 0 < info.st_size <= MAX_ARCHIVE_BYTES):
        raise conflict('The accepted archive requires a bounded regular owner file')


def _stamp(info):
    return tuple(getattr(info, name) for name in ('st_dev', 'st_ino', 'st_mode', 'st_nlink',
        'st_uid', 'st_gid', 'st_size', 'st_mtime_ns', 'st_ctime_ns'))


def reviewed_baseline(profile, baseline, installed, desired, active, planner):
    collisions = {}
    for name, wanted in desired.items():
        if name in baseline['files'] or name in planner.GENERATED_FILES:
            continue
        path = planner._checked_path(installed, name)
        if path.exists():
            if not path.is_file():
                raise planner.UpdateConflict('The omitted program is not a regular file')
            observed = planner._digest(path)
            if observed != wanted:
                collisions[name] = observed
    if not collisions:
        return baseline
    conflict = planner.UpdateConflict
    archive_path = _archive(profile, baseline, active, conflict)
    expected = {}
    try:
        descriptor = os.open(archive_path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(descriptor, 'rb') as stream:
            before = os.fstat(stream.fileno())
            _check_archive(before, conflict)
            if _digest(stream) != active['package_sha256']:
                raise conflict('The accepted archive changes its recorded release digest')
            stream.seek(0)
            total = 0
            with tarfile.open(fileobj=stream, mode='r:gz') as archive:
                for number, member in enumerate(archive, 1):
                    total += member.size
                    if number > MAX_MEMBERS or total > MAX_EXTRACTED_BYTES:
                        raise conflict('The accepted archive exceeds its member or content limit')
                    prefix = 'lifeos/LifeOS/install/'
                    name = member.name.removeprefix(prefix)
                    if not member.name.startswith(prefix) or name not in collisions:
                        continue
                    if name in expected or not member.isfile():
                        raise conflict('The accepted program archive entry is not unique and regular')
                    with archive.extractfile(member) as content:
                        expected[name] = _digest(content)
            stream.seek(0)
            after = os.fstat(stream.fileno())
            _check_archive(after, conflict)
            if (_stamp(before) != _stamp(after) or _stamp(archive_path.lstat()) != _stamp(after)
                    or _digest(stream) != active['package_sha256']):
                raise conflict('The accepted archive changes during program review')
    except (OSError, tarfile.TarError) as error:
        raise conflict('The accepted program archive is unavailable') from error
    if expected != collisions:
        raise conflict('An omitted program differs from its accepted archive or has no archive proof')
    return {**baseline, 'files': {**baseline['files'], **expected}}
