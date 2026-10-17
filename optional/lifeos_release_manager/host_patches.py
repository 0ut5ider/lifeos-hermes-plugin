# ABOUTME: Stages the qualified patched Hermes files from the owner's checkout in private operation storage.
# ABOUTME: Keeps exact copies of the original files and verifies every result against the compatibility manifest.
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import shutil
import stat
import subprocess
import tempfile

from .release_stage import sha


ADDED_MODE = 0o644


class HostPatchRejected(ValueError):
    """The owner's Hermes files or the patch set differ from the qualified compatibility entry."""


def _read_original(path):
    """Return the bytes and permission bits of a regular file, refusing links and other types."""
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, 'rb') as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode):
            raise HostPatchRejected('A Hermes patch target is not a regular file: ' + str(path))
        return stream.read(), stat.S_IMODE(info.st_mode)


def _write(path, data, mode):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with path.open('xb') as output:
        output.write(data)
    path.chmod(mode)


def stage_host_files(source, entry, patches, destination):
    """Copy the stock patch targets, apply the ordered patches to the copies, and verify each result.

    Returns a map from each relative target path to its retained original (None for an added file)
    and its staged patched file. The owner's checkout is only read.
    """
    source, patches, destination = Path(source).absolute(), Path(patches).absolute(), Path(destination).absolute()
    if destination.exists() or destination.is_symlink() or destination.parent.resolve() != destination.parent:
        raise HostPatchRejected('Host patch staging requires a new private directory')
    for patch in entry['patches']:
        path = patches / patch['name']
        if path.is_symlink() or not path.is_file() or sha(path) != patch['sha256']:
            raise HostPatchRejected('The Hermes patch differs from its qualified identity: ' + patch['name'])
    staging = Path(tempfile.mkdtemp(prefix='.host-', dir=destination.parent))
    try:
        stock, patched = staging / 'stock', staging / 'patched'
        stock.mkdir(mode=0o700)
        patched.mkdir(mode=0o700)
        for relative, hashes in entry['files'].items():
            target = source / relative
            if hashes['stock'] is None:
                if target.exists() or target.is_symlink():
                    raise HostPatchRejected('A file that LifeOS adds already exists: ' + relative)
                continue
            try:
                data, mode = _read_original(target)
            except FileNotFoundError as error:
                raise HostPatchRejected('A Hermes patch target is missing: ' + relative) from error
            if hashlib.sha256(data).hexdigest() != hashes['stock']:
                raise HostPatchRejected('A Hermes patch target differs from the qualified version: ' + relative)
            _write(stock / relative, data, mode)
            _write(patched / relative, data, mode)
        environment = {**os.environ, 'GIT_CEILING_DIRECTORIES': str(staging)}
        for patch in entry['patches']:
            result = subprocess.run(['git', 'apply', str(patches / patch['name'])], cwd=patched, env=environment,
                                    capture_output=True, text=True, timeout=120)
            if result.returncode:
                raise HostPatchRejected('The Hermes patch does not apply to the staged files: ' + patch['name'])
        produced = {path.relative_to(patched).as_posix() for path in patched.rglob('*') if not path.is_dir()}
        if produced != set(entry['files']):
            raise HostPatchRejected('The patches change files outside the qualified patch targets')
        for relative, hashes in entry['files'].items():
            path = patched / relative
            if path.is_symlink() or sha(path) != hashes['patched']:
                raise HostPatchRejected('A patched Hermes file differs from its qualified result: ' + relative)
            if hashes['stock'] is None:
                path.chmod(ADDED_MODE)
        os.replace(staging, destination)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return {relative: {'stock': None if hashes['stock'] is None else destination / 'stock' / relative,
                       'patched': destination / 'patched' / relative}
            for relative, hashes in entry['files'].items()}
