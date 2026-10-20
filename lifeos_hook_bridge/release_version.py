# ABOUTME: Reports matching integration versions and exact installed release identities.
# ABOUTME: Separates staged candidates from selected code and detects changed plugin and patched Hermes files.
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError


NUMBER = r'(?:0|[1-9][0-9]*)'
VERSION = re.compile(NUMBER+r'\.'+NUMBER+r'\.'+NUMBER+r'(?:-(?:dev|rc)\.'+NUMBER+r')?')


def _version(value):
    if not isinstance(value,str) or VERSION.fullmatch(value) is None:
        raise ValueError('Integration versions require three numbers and an optional dev or rc counter')
    return value


def _declared(plugin):
    try:
        manifest=YAML(typ='safe').load((plugin/'plugin.yaml').read_text())
        dashboard=json.loads((plugin/'dashboard/manifest.json').read_text())
        version=_version(manifest['version'])
        if _version(dashboard['version'])!=version:
            raise ValueError('The plugin and dashboard versions differ')
        return version
    except (YAMLError, KeyError, TypeError) as error:
        raise ValueError('The integration version declarations are invalid') from error


def versions(package):
    package=Path(package)
    version=_version((package/'VERSION').read_text().strip())
    if _declared(package/'lifeos_hook_bridge')!=version:
        raise ValueError('The three integration version declarations differ')
    return version


def _receipt(path):
    if not path.exists() and not path.is_symlink():
        return None
    info=path.lstat()
    if (not stat.S_ISREG(info.st_mode) or info.st_nlink!=1 or info.st_uid!=os.getuid()
            or info.st_mode & 0o077 or info.st_size>512*1024):
        raise ValueError('Release receipts require bounded private owner files')
    value=json.loads(path.read_text())
    if (not isinstance(value,dict) or type(value.get('format')) is not int or value['format']!=1
            or not isinstance(value.get('commit'),str) or re.fullmatch('[0-9a-f]{40}',value['commit']) is None
            or not isinstance(value.get('package_sha256'),str)
            or re.fullmatch('[0-9a-f]{64}',value['package_sha256']) is None):
        raise ValueError('Release receipts require exact commit and package identities')
    _version(value.get('version'))
    return value


def _identity(value):
    return {name:value[name] for name in ('version','commit','package_sha256')}


HOST_RECORD='lifeos-host.json'


def _host_record(path):
    info=path.lstat()
    if (not stat.S_ISREG(info.st_mode) or info.st_uid!=os.getuid() or info.st_mode & 0o022
            or info.st_size>2*1024*1024):
        raise ValueError('The LifeOS host record requires a bounded owner file')
    try:
        value=json.loads(path.read_text())
    except ValueError as error:
        raise ValueError('The LifeOS host record is unreadable') from error
    if (not isinstance(value,dict) or not isinstance(value.get('source'),str)
            or not Path(value['source']).is_absolute() or not isinstance(value.get('files'),dict)):
        raise ValueError('The LifeOS host record has an invalid structure')
    for name,hashes in value['files'].items():
        relative=PurePosixPath(name) if isinstance(name,str) else None
        if (relative is None or not name or relative.is_absolute() or str(relative)!=name
                or any(part in {'.','..'} for part in relative.parts) or relative.parts[0]=='.git'
                or not isinstance(hashes,dict) or not isinstance(hashes.get('patched'),str)
                or re.fullmatch('[0-9a-f]{64}',hashes['patched']) is None):
            raise ValueError('The LifeOS host record has invalid file identities')
    return value


def _digest(path):
    try:
        descriptor=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    except OSError:
        return None
    with os.fdopen(descriptor,'rb') as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            return None
        return hashlib.file_digest(stream,'sha256').hexdigest()


def host_recorded(profile):
    """Return whether the profile has an in-place host record, which marks an in-place installation."""
    path=Path(profile)/HOST_RECORD
    return path.exists() or path.is_symlink()


def host_status(profile):
    """Compare each Hermes file that LifeOS patched with its recorded hash; None without an in-place record."""
    if not host_recorded(profile):
        return None
    path=Path(profile)/HOST_RECORD
    try:
        record=_host_record(path)
    except OSError:
        return {'state':'host_drift','reason':'The LifeOS host record is unreadable: '+str(path)+'.'}
    except ValueError as error:
        return {'state':'host_drift','reason':str(error)+': '+str(path)+'.'}
    source=Path(record['source'])
    changed=sorted(name for name,hashes in record['files'].items()
        if (source/name).parent.resolve()!=source.resolve()/PurePosixPath(name).parent
            or _digest(source/name)!=hashes['patched'])
    return {'state':'host_drift' if changed else 'installed','source':str(source),'changed':changed}


def status(profile, plugin):
    profile,plugin=Path(profile),Path(plugin)
    version=_declared(plugin)
    active={'version':version,'verification':'unrecorded','verification_scope':'plugin_sources'}
    record=_receipt(profile/'integration-release.json')
    if record is not None:
        files=record.get('plugin_files')
        if not isinstance(files,dict) or not 1<=len(files)<=1024:
            raise ValueError('The release receipt requires bounded plugin file hashes')
        changed=[]
        for name,digest in files.items():
            if (not isinstance(name,str) or not name or '\\' in name
                    or PurePosixPath(name).is_absolute() or any(part in {'.','..'} or part.startswith('.')
                        for part in PurePosixPath(name).parts) or str(PurePosixPath(name))!=name
                    or not isinstance(digest,str) or re.fullmatch('[0-9a-f]{64}',digest) is None):
                raise ValueError('Release file hashes require fixed relative program paths')
            path=plugin/name
            if (not path.is_file() or path.is_symlink() or path.resolve()!=plugin.resolve()/name
                    or hashlib.sha256(path.read_bytes()).hexdigest()!=digest):
                changed.append(name)
        actual={str(path.relative_to(plugin)) for path in plugin.rglob('*')
            if '__pycache__' not in path.relative_to(plugin).parts and path.suffix!='.pyc'
            and (path.is_file() or path.is_symlink())}
        changed.extend(actual-set(files))
        active.update(_identity(record),version=version,recorded_version=record['version'],
            verification='verified' if not changed and record['version']==version else 'modified',
            modified_files=sorted(set(changed)))
    staged=_receipt(profile/'integration-candidate.json')
    return {'active':active,'staged':None if staged is None else _identity(staged),'host':host_status(profile)}
