# ABOUTME: Records which Hermes checkout LifeOS patched and where the original files are retained.
# ABOUTME: Validates the record and the retained originals so updates and removal never trust stale state.
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import stat

from .host_compatibility import ManifestRejected, _entry, _relative_path


RECORD_NAME = 'lifeos-host.json'
ORIGINALS = '.lifeos-host/originals'


class HostRecordRejected(ValueError):
    """The host record or its retained originals are missing, malformed, or changed."""


def record_path(profile):
    return Path(profile).absolute() / RECORD_NAME


def originals_path(profile):
    return Path(profile).absolute() / ORIGINALS


def build_record(profile, source, entry, *, operation, version):
    """Return the record for a host that receives ``entry`` from operation ``operation``."""
    value = {'format': 1, 'source': str(Path(source).absolute()), 'commit': entry['commit'], 'label': entry['label'],
             'patches': copy.deepcopy(entry['patches']), 'files': copy.deepcopy(entry['files']),
             'originals': str(originals_path(profile)), 'operation': operation, 'version': version}
    return validate_record(value, profile)


def validate_record(value, profile):
    if not isinstance(value, dict) or set(value) != {'format', 'source', 'commit', 'label', 'patches', 'files',
                                                     'originals', 'operation', 'version'}:
        raise HostRecordRejected('The LifeOS host record has an invalid structure')
    if type(value['format']) is not int or value['format'] != 1:
        raise HostRecordRejected('The LifeOS host record format is unsupported')
    try:
        _entry({key: value[key] for key in ('label', 'commit', 'patches', 'files')})
    except ManifestRejected as error:
        raise HostRecordRejected('The LifeOS host record has invalid file identities') from error
    source = value['source']
    if not isinstance(source, str) or not Path(source).is_absolute() or '..' in Path(source).parts:
        raise HostRecordRejected('The LifeOS host record requires an absolute Hermes source path')
    if value['originals'] != str(originals_path(profile)):
        raise HostRecordRejected('The LifeOS host record names another originals directory')
    for key in ('operation', 'version'):
        if not isinstance(value[key], str) or not value[key] or len(value[key]) > 64:
            raise HostRecordRejected('The LifeOS host record requires its operation and release version')
    return value


def load_record(profile):
    """Return the validated host record, or None when this profile has no in-place installation."""
    path = record_path(profile)
    if not path.exists() and not path.is_symlink():
        return None
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(descriptor, 'rb') as stream:
            info = os.fstat(stream.fileno())
            if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o022
                    or info.st_size > 2 * 1024 * 1024):
                raise HostRecordRejected('The LifeOS host record requires a bounded owner file')
            value = json.loads(stream.read())
    except HostRecordRejected:
        raise
    except (OSError, ValueError) as error:
        raise HostRecordRejected('The LifeOS host record is unreadable') from error
    return validate_record(value, profile)


def check_originals(record):
    """Verify each retained original against the qualified stock identity; return the target-to-original map."""
    root = Path(record['originals'])
    originals = {}
    for relative, hashes in record['files'].items():
        _relative_path(relative)
        if hashes['stock'] is None:
            continue
        path = root / relative
        try:
            descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        except OSError as error:
            raise HostRecordRejected('A retained original Hermes file is missing: ' + relative) from error
        with os.fdopen(descriptor, 'rb') as stream:
            info = os.fstat(stream.fileno())
            if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o022
                    or hashlib.file_digest(stream, 'sha256').hexdigest() != hashes['stock']):
                raise HostRecordRejected('A retained original Hermes file changed: ' + relative)
        originals[relative] = path
    return originals
