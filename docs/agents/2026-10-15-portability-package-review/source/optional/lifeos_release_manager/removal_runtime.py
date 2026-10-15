# ABOUTME: Binds the executable stock Hermes closure to the owner removal review.
# ABOUTME: Checks command, interpreter, dependency, and bootstrap artifacts before selection and recovery.
import os
from pathlib import Path

from .release_catalog import ReleaseRejected
from .release_programs import fingerprint


DIRECTORIES=('bin','hermes','python-environment','dependency-profile/tools','pm-runtime','bytecode')
EXCLUDED={'python-environment':frozenset({'.lock'}),'hermes':frozenset({'.hermes','.bytecode-fingerprint'})}


def _covered(target, root):
    for name in DIRECTORIES:
        directory=root/name
        if target.is_relative_to(directory):
            relative=target.relative_to(directory)
            return not relative.parts or relative.parts[0] not in EXCLUDED.get(name,())
    return False


def identity(root):
    root=Path(root).absolute()
    if root.resolve()!=root or not root.is_dir():
        raise ReleaseRejected('The stock executable runtime requires its physical prepared directory')
    result={}
    for name in (*DIRECTORIES,'enabled-features.json','manifest.json','runtime.json'):
        path=root/name;links={}
        if path.is_dir():
            for parent,directories,files in os.walk(path,followlinks=False):
                for item in (*directories,*files):
                    child=Path(parent)/item
                    if not child.is_symlink():continue
                    if not _covered(child.resolve(strict=True),root):
                        raise ReleaseRejected('The stock executable runtime contains an unbound dependency link')
                    links[str(child.relative_to(path))]=os.readlink(child)
        excluded=EXCLUDED.get(name,())
        selected=fingerprint(path,allow_links=True,external_links=links,excluded_root_entries=excluded,include_bytecode=True)
        if selected is None and name!='bytecode':
            raise ReleaseRejected('The stock executable runtime loses a required artifact')
        result[name]=selected
    return result


def command(command, runtime):
    root=Path(runtime['source']).parent
    return [command[0],'-B','-X','pycache_prefix='+str(root/'bytecode'),*command[1:]]


def launchers(root):
    from .release_programs import publish
    before='export PYTHONPYCACHEPREFIX="${PYTHONPYCACHEPREFIX:-${XDG_CACHE_HOME:-$HOME/.cache}/hermes-pycache}"'
    after='export PYTHONPYCACHEPREFIX="$root/bytecode"\nexport PYTHONDONTWRITEBYTECODE=1'
    for name in ('hermes','hermes-agent','hermes-acp'):
        path=Path(root)/'bin'/name;data=path.read_text()
        if data.count(before)!=1:
            raise ReleaseRejected('The prepared stock launcher has an unsupported bytecode selection')
        publish(path,data.replace(before,after).encode(),path.stat().st_mode & 0o777)
