# ABOUTME: Reports matching integration versions and exact installed release identities.
# ABOUTME: Separates staged candidates from selected code and detects changed plugin files.
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


def status(profile, plugin):
    profile,plugin=Path(profile),Path(plugin)
    version=_declared(plugin)
    active={'version':version,'verification':'unrecorded'}
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
    return {'active':active,'staged':None if staged is None else _identity(staged)}
