# ABOUTME: Binds the executable stock Hermes closure to the owner removal review.
# ABOUTME: Checks command, interpreter, dependency, and bootstrap artifacts before selection and recovery.
import os
from pathlib import Path

from .release_catalog import ReleaseRejected
from .release_programs import fingerprint


def identity(root):
    root=Path(root).absolute()
    if root.resolve()!=root or not root.is_dir():
        raise ReleaseRejected('The stock executable runtime requires its physical prepared directory')
    result={}
    for name in ('bin','python-environment','dependency-profile/tools','pm-runtime',
            'enabled-features.json','manifest.json','runtime.json'):
        path=root/name;links={}
        if path.is_dir():
            for parent,directories,files in os.walk(path,followlinks=False):
                for item in (*directories,*files):
                    child=Path(parent)/item
                    if not child.is_symlink():continue
                    if not child.resolve(strict=True).is_relative_to(root):
                        raise ReleaseRejected('The stock executable runtime contains an external dependency link')
                    links[str(child.relative_to(path))]=os.readlink(child)
        excluded=frozenset({'.lock'}) if name=='python-environment' else ()
        selected=fingerprint(path,allow_links=True,external_links=links,excluded_root_entries=excluded)
        if selected is None:
            raise ReleaseRejected('The stock executable runtime loses a required artifact')
        result[name]=selected
    return result
