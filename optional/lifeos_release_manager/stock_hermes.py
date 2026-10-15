# ABOUTME: Prepares exact unpatched Hermes sources for integration removal without reversing patches.
# ABOUTME: Verifies authenticated archive bytes and records the complete extracted source identity.
import hashlib
import os
from pathlib import Path
import re
import stat
import subprocess
import tempfile

from .release_catalog import extract_package, ReleaseRejected
from .release_programs import fingerprint


LIMIT=512*1024*1024


def _identity(value):
    if (not isinstance(value,dict) or set(value)!={'format','commit','path','sha256','bytes'}
            or type(value['format']) is not int or value['format']!=1 or value['path']!='stock-hermes.tgz'
            or not isinstance(value['commit'],str) or re.fullmatch('[0-9a-f]{40}',value['commit']) is None
            or not isinstance(value['sha256'],str) or re.fullmatch('[0-9a-f]{64}',value['sha256']) is None
            or type(value['bytes']) is not int or not 0<value['bytes']<=LIMIT):
        raise ReleaseRejected('Stock Hermes requires an authenticated exact archive identity')
    return value


def build_archive(source, destination, commit):
    source,destination=Path(source).absolute(),Path(destination).absolute()
    if not isinstance(commit,str) or re.fullmatch('[0-9a-f]{40}',commit) is None:
        raise ReleaseRejected('Stock Hermes requires a full pinned upstream commit')
    if source.resolve()!=source or destination.parent.resolve()!=destination.parent:
        raise ReleaseRejected('Stock Hermes requires physical source and archive directories')
    result=subprocess.run(['git','rev-parse',commit+'^{commit}'],cwd=source,capture_output=True,text=True,timeout=30)
    if result.returncode or result.stdout.strip()!=commit:
        raise ReleaseRejected('The upstream repository lacks the exact stock Hermes commit')
    with destination.open('xb') as output:
        os.fchmod(output.fileno(),0o600)
        result=subprocess.run(['git','archive','--format=tar.gz',commit],cwd=source,stdout=output,
            stderr=subprocess.PIPE,timeout=180)
        output.flush();os.fsync(output.fileno())
    if result.returncode:raise ReleaseRejected('Git cannot archive the exact stock Hermes source')
    size=destination.stat().st_size
    with destination.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
    return _identity({'format':1,'commit':commit,'path':'stock-hermes.tgz','sha256':digest,'bytes':size})


def prepare_source(archive, destination, identity):
    identity=_identity(identity)
    archive,destination=Path(archive).absolute(),Path(destination).absolute()
    if archive.parent.resolve()!=archive.parent:
        raise ReleaseRejected('The stock source archive changes its physical directory')
    try:descriptor=os.open(archive,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC|os.O_NONBLOCK)
    except OSError as error:
        raise ReleaseRejected('The stock source archive requires a regular physical owner file') from error
    with os.fdopen(descriptor,'rb') as source, tempfile.TemporaryDirectory(prefix='.stock-',dir=destination.parent) as directory:
        before=os.fstat(source.fileno())
        if (not stat.S_ISREG(before.st_mode) or before.st_uid!=os.getuid() or before.st_nlink!=1
                or before.st_mode & 0o022 or before.st_size!=identity['bytes']):
            raise ReleaseRejected('The stock source archive differs from its owner identity')
        retained=Path(directory)/'source.tgz'
        digest=hashlib.sha256();size=0
        with retained.open('xb') as output:
            os.fchmod(output.fileno(),0o600)
            for block in iter(lambda:source.read(1024*1024),b''):
                size+=len(block)
                if size>identity['bytes']:raise ReleaseRejected('The stock source archive exceeds its declared size')
                digest.update(block);output.write(block)
        after=os.fstat(source.fileno())
        stamp=lambda value:(value.st_dev,value.st_ino,value.st_size,value.st_mtime_ns,value.st_mode)
        if (size!=identity['bytes'] or digest.hexdigest()!=identity['sha256'] or stamp(before)!=stamp(after)
                or stamp(after)!=stamp(archive.stat()) or archive.is_symlink()):
            raise ReleaseRejected('The stock source archive changes or fails its authenticated digest')
        extract_package(retained,destination,max_bytes=LIMIT)
    if not all((destination/name).is_file() for name in ('run_agent.py','pyproject.toml')):
        raise ReleaseRejected('The stock archive lacks the actual Hermes source')
    return {'format':1,'commit':identity['commit'],'patches':0,'archive':identity,'source':fingerprint(destination)}


def verify_source(source, record):
    if (not isinstance(record,dict) or set(record)!={'format','commit','patches','archive','source'}
            or type(record['format']) is not int or record['format']!=1 or type(record['patches']) is not int
            or record['patches']!=0 or _identity(record['archive'])['commit']!=record['commit']
            or fingerprint(source)!=record['source']):
        raise ReleaseRejected('The prepared stock Hermes source differs from its reviewed identity')
    return record


def validate_archive(archive, identity):
    identity=_identity(identity);archive=Path(archive).absolute()
    if archive.parent.resolve()!=archive.parent or archive.is_symlink():
        raise ReleaseRejected('The stock source archive requires a physical owner file')
    try:descriptor=os.open(archive,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC|os.O_NONBLOCK)
    except OSError as error:raise ReleaseRejected('The stock source archive is unavailable') from error
    with os.fdopen(descriptor,'rb') as stream:
        before=os.fstat(stream.fileno())
        if (not stat.S_ISREG(before.st_mode) or before.st_uid!=os.getuid() or before.st_mode & 0o022
                or before.st_nlink!=1 or before.st_size!=identity['bytes']):
            raise ReleaseRejected('The stock source archive differs from its declared owner identity')
        if hashlib.file_digest(stream,'sha256').hexdigest()!=identity['sha256']:
            raise ReleaseRejected('The stock source archive fails its authenticated digest')
        after=os.fstat(stream.fileno())
        stamp=lambda value:(value.st_dev,value.st_ino,value.st_size,value.st_mtime_ns,value.st_mode)
        if stamp(before)!=stamp(after) or stamp(after)!=stamp(archive.stat()):
            raise ReleaseRejected('The stock source archive changes during validation')
    return identity
