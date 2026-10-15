# ABOUTME: Validates private recovery sources before the standalone command executes manager code.
# ABOUTME: Uses only the stock Python standard library so the checks can be frozen into the launcher.
import hashlib
import json
import os
from pathlib import Path
import re
import stat


def _private(path):
    path=Path(path)
    if path.parent.resolve()!=path.parent:raise ValueError('The recovery metadata changes its physical directory')
    descriptor=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    with os.fdopen(descriptor,'rb') as stream:
        info=os.fstat(stream.fileno())
        if (not stat.S_ISREG(info.st_mode) or info.st_uid!=os.getuid() or info.st_mode & 0o077
                or info.st_nlink!=1 or info.st_size>2*1024*1024):
            raise ValueError('Recovery requires bounded private owner metadata')
        return json.loads(stream.read(2*1024*1024+1))


def _files(root, expected):
    info=root.lstat()
    if root.resolve()!=root or not stat.S_ISDIR(info.st_mode) or info.st_uid!=os.getuid() or info.st_mode & 0o022:
        raise ValueError('Recovery requires protected physical code directories')
    if not isinstance(expected,dict) or not 1<=len(expected)<=2048:raise ValueError('Recovery requires an exact bounded code map')
    found={}
    for path in root.rglob('*'):
        info=path.lstat()
        if (path.is_symlink() or info.st_uid!=os.getuid() or info.st_mode & 0o022
                or path.name=='__pycache__' or path.suffix=='.pyc'):
            raise ValueError('The retained recovery code has an unreviewed artifact')
        if stat.S_ISDIR(info.st_mode):continue
        if not stat.S_ISREG(info.st_mode):raise ValueError('The retained recovery code requires regular files')
        found[path.relative_to(root).as_posix()]=hashlib.sha256(path.read_bytes()).hexdigest()
        if len(found)>2048:raise ValueError('The retained recovery code exceeds its file bound')
    if found!=expected:raise ValueError('The retained recovery code changes after owner review')


def validate(profile, identifier):
    profile=Path(profile).absolute()
    if not isinstance(identifier,str) or re.fullmatch('[0-9a-f]{32}',identifier) is None:
        raise ValueError('Recovery requires the exact workflow identifier')
    marker=_private(profile/'.lifeos-removal.json')
    if (not isinstance(marker,dict) or set(marker)!={'format','workflow','signature'} or marker['format']!=1
            or marker['workflow']!=identifier or not isinstance(marker['signature'],str)
            or re.fullmatch('[0-9a-f]{64}',marker['signature']) is None):
        raise ValueError('Recovery requires the exact current removal selection')
    job=profile/'.lifeos-portability'/identifier;stage=job/'removal'
    for path in (job,stage):
        info=path.lstat()
        if path.resolve()!=path or not stat.S_ISDIR(info.st_mode) or info.st_uid!=os.getuid() or info.st_mode & 0o077:
            raise ValueError('Recovery requires private workflow directories')
    plan=_private(stage/'plan.json')
    digest=hashlib.sha256(json.dumps(plan,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    if (not isinstance(plan,dict) or digest!=marker['signature'] or plan.get('format')!=1
            or plan.get('identifier')!=identifier or plan.get('profile')!=str(profile)):
        raise ValueError('The recovery plan differs from its owner selection')
    for name,key in (('recovery-manager','manager_files'),('recovery-bridge','bridge_files')):
        _files(stage/name,plan.get(key))
    return {'worker':str(stage/'recovery-manager/removal_recovery.py'),'signature':marker['signature']}
