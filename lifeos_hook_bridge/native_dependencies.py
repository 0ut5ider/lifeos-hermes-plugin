# ABOUTME: Installs native package dependencies from verified release manifests and frozen locks.
# ABOUTME: Refuses changed package inputs before Bun resolves or replaces their dependency tree.
import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile


def _regular(path):
    if not stat.S_ISREG(path.lstat().st_mode) or path.stat().st_size>1024*1024:
        raise ValueError('Native dependency inputs require bounded regular files')
    return path.read_bytes()


def _catalog(directory):
    directory=Path(directory).absolute()
    if directory.resolve()!=directory:
        raise ValueError('The native dependency catalog changes its physical path')
    value=json.loads(_regular(directory/'catalog.json'))
    if (not isinstance(value,dict) or set(value)!={'version','lifeos_commit','bun_version','packages'}
            or type(value['version']) is not int or value['version']!=1
            or not isinstance(value['lifeos_commit'],str) or re.fullmatch(r'[0-9a-f]{40}',value['lifeos_commit']) is None
            or not isinstance(value['bun_version'],str) or re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+',value['bun_version']) is None
            or not isinstance(value['packages'],dict) or not 1<=len(value['packages'])<=100):
        raise ValueError('The native dependency catalog has unsupported metadata')
    for name,item in value['packages'].items():
        path=Path(name)
        if (not isinstance(name,str) or path.is_absolute() or '..' in path.parts or path.as_posix()!=name
                or not isinstance(item,dict) or set(item)!={'package_sha256','lock_file','lock_sha256'}
                or any(not isinstance(item[key],str) for key in item)
                or re.fullmatch(r'[0-9a-f]{24}\.lock',item['lock_file']) is None
                or any(re.fullmatch('[0-9a-f]{64}',item[key]) is None for key in ('package_sha256','lock_sha256'))
                or hashlib.sha256(_regular(directory/item['lock_file'])).hexdigest()!=item['lock_sha256']):
            raise ValueError('The native dependency catalog has invalid package locks')
    return value


def _write_lock(target,data):
    descriptor,name=tempfile.mkstemp(prefix='.native-lock-',dir=target.parent)
    temporary=Path(name)
    try:
        with os.fdopen(descriptor,'wb') as stream:
            stream.write(data);stream.flush();os.fsync(stream.fileno())
        os.replace(temporary,target)
        descriptor=os.open(target.parent,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(descriptor)
        finally:os.close(descriptor)
    finally:temporary.unlink(missing_ok=True)


def seed_release_locks(installed,directory):
    installed=Path(installed).absolute()
    value=_catalog(directory)
    if (installed.resolve()!=installed or not installed.is_dir()
            or any(path.name!='CLAUDE.md' for path in installed.iterdir())):
        raise ValueError('Release dependencies require an empty fresh installation')
    if (installed/'CLAUDE.md').exists() or (installed/'CLAUDE.md').is_symlink():
        _regular(installed/'CLAUDE.md')
    for name,item in value['packages'].items():
        parent=installed/name
        parent.mkdir(parents=True,exist_ok=True,mode=0o700)
        _write_lock(parent/'bun.lock',_regular(Path(directory)/item['lock_file']))


def validate_release_dependencies(source,directory,revision):
    value=_catalog(directory)
    if value['lifeos_commit']!=revision:
        raise ValueError('The native dependency catalog selects another source revision')
    source=Path(source).absolute()
    actual=set()
    for parent,dirs,files in os.walk(source,followlinks=False):
        current=Path(parent)
        dirs[:]=[name for name in dirs if name not in ('node_modules','.git')
            and current/name!=source/'skills/LifeOS/install']
        if 'package.json' in files:actual.add(current.relative_to(source).as_posix())
    if actual!=set(value['packages']):
        raise ValueError('The native dependency catalog does not cover the complete package tree')
    for name,item in value['packages'].items():
        if hashlib.sha256(_regular(source/name/'package.json')).hexdigest()!=item['package_sha256']:
            raise ValueError('The native package manifest changes after release verification')
    return value


def _lock(root,directory):
    root=Path(root).absolute()
    current=Path.cwd()
    if root.resolve()!=root or current.resolve()!=current or not current.is_relative_to(root):
        raise ValueError('Native dependencies require the selected physical installation')
    value=_catalog(directory)
    item=value['packages'].get(current.relative_to(root).as_posix())
    if item is None or hashlib.sha256(_regular(current/'package.json')).hexdigest()!=item['package_sha256']:
        raise ValueError('The native package manifest does not match its release lock')
    expected=_regular(Path(directory)/item['lock_file'])
    target=current/'bun.lock'
    if target.exists() or target.is_symlink():
        if _regular(target)!=expected:
            raise ValueError('The native dependency lock changes after release verification')
        return
    _write_lock(target,expected)


@contextmanager
def dependency_environment(installed,executable,directory):
    installed=Path(installed).absolute();executable=Path(executable).absolute()
    value=_catalog(directory)
    version=subprocess.run([str(executable),'--version'],text=True,capture_output=True,check=True,timeout=10)
    if version.stdout.strip()!=value['bun_version']:
        raise ValueError('Native dependency installation requires the tested Bun version')
    temporary=Path(tempfile.mkdtemp(prefix='.dependency-bin-',dir=installed))
    try:
        wrapper=temporary/'bun'
        command=[sys.executable,'-I',str(Path(__file__).resolve()),'--executable',str(executable),
                 '--root',str(installed),'--catalog',str(Path(directory).absolute()),'--']
        wrapper.write_text('#!/bin/sh\nexec '+' '.join(shlex.quote(value) for value in command)+' "$@"\n')
        wrapper.chmod(0o700)
        yield {'PATH':str(temporary)+os.pathsep+str(executable.parent)+os.pathsep+os.environ.get('PATH','')}
    finally:shutil.rmtree(temporary)


# Bun subcommands that change installed dependencies or lock files outside the frozen install.
CHANGING_COMMANDS=frozenset({'add','a','remove','rm','update','upgrade','link','unlink','pm','patch','patch-commit'})
# Global Bun options that take the next argument as their value.
VALUE_OPTIONS=frozenset({'--cwd','-c','--config','--env-file','-r','--preload','--tsconfig-override'})


def _subcommand(arguments):
    """Return the first Bun argument that is not a global option or an option value."""
    index=0
    while index<len(arguments):
        token=arguments[index]
        if not token.startswith('-'):return token
        index+=2 if token in VALUE_OPTIONS else 1
    return None


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--executable',required=True)
    parser.add_argument('--root',required=True)
    parser.add_argument('--catalog',required=True)
    parser.add_argument('arguments',nargs=argparse.REMAINDER)
    selected=parser.parse_args()
    arguments=selected.arguments
    if arguments[:1]==['--']:arguments=arguments[1:]
    command=_subcommand(arguments)
    if command in CHANGING_COMMANDS:
        parser.error('Native installation cannot change dependencies outside the release locks')
    if command in ('install','i'):
        if arguments not in ([command],[command,'--frozen-lockfile']):
            parser.error('The native installer requires its fixed frozen-lock operation')
        try:_lock(selected.root,selected.catalog)
        except (ValueError,OSError,KeyError,TypeError) as error:
            print(str(error),file=sys.stderr)
            return 2
        arguments=['install','--frozen-lockfile']
    os.execv(selected.executable,[selected.executable,*arguments])


if __name__=='__main__':
    raise SystemExit(main())
