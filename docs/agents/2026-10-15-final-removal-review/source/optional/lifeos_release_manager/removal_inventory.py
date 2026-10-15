# ABOUTME: Admits only exact qualified native software and plugin files for complete removal.
# ABOUTME: Preserves user stores and foreign hook registrations while refusing edited program ownership.
import json
import os
from pathlib import Path

from .release_catalog import ReleaseRejected
from .release_programs import fingerprint
from .release_stage import sha, validate_files


def plugin(directory, files):
    validate_files(directory,files)
    return fingerprint(directory)


def native(installed, source, reference, *, bridge):
    installed,source,reference=map(lambda value:Path(value).absolute(),(installed,source,reference))
    for path in (installed,source,reference):
        if path.resolve()!=path or not path.is_dir():
            raise ReleaseRejected('Removal requires physical qualified native program directories')
    planner=bridge.memory_module('update_plan')
    expected=planner.deployed_system_files(source,reference)
    files={};before={}
    for name,digest in expected.items():
        target=installed/name
        if (target.resolve()!=target or not target.is_file() or sha(target)!=digest):
            raise ReleaseRejected('A native program differs from the qualified removal source: '+name)
        identity=fingerprint(target)
        if identity['sha256']!=digest:raise ReleaseRejected('A native program changes during removal admission')
        before[target]=identity;files[target]=None
    dependencies={}
    roots=bridge.memory_module('update_dependencies')._package_roots(reference)
    for root in sorted(roots):
        for name in ('package.json','bun.lock'):
            target=installed/root/name;original=reference/root/name
            if original.is_file():
                if fingerprint(target)!=fingerprint(original):
                    raise ReleaseRejected('A native package differs from its qualified removal source')
                before[target]=fingerprint(original);files[target]=None
            elif target.exists() or target.is_symlink():
                raise ReleaseRejected('An unreviewed native package collides with complete removal')
        target=installed/root/'node_modules';original=reference/root/'node_modules'
        if fingerprint(target,allow_links=True)!=fingerprint(original,allow_links=True):
            raise ReleaseRejected('A native dependency differs from its qualified removal source')
        if original.exists():before[target]=fingerprint(original,allow_links=True);dependencies[target]=None
    for name in ('CLAUDE.md',):
        target=installed/name;original=reference/name
        if original.is_file():
            if fingerprint(target)!=fingerprint(original):
                raise ReleaseRejected('The native instructions change before removal')
            before[target]=fingerprint(original);files[target]=None
    retained={installed/name for name in ('LIFEOS/USER','LIFEOS/MEMORY','LIFEOS/PULSE/state')}
    generated={installed/name for name in bridge.memory_module('version_drift').GENERATED_FILES}
    for name in ('hooks','skills','agents','commands','test','LIFEOS'):
        root=installed/name
        if not root.exists() and not root.is_symlink():continue
        if root.is_symlink() or not root.is_dir():raise ReleaseRejected('A native program directory changes its physical path')
        for directory,names,children in os.walk(root,followlinks=False):
            parent=Path(directory)
            names[:]=[name for name in names if name!='__pycache__' and parent/name not in dependencies
                and parent/name not in retained]
            for name in (*names,*children):
                path=parent/name
                if path.is_symlink():raise ReleaseRejected('An unreviewed native program link blocks removal')
                if path.is_file() and path.suffix!='.pyc' and path not in files and path not in generated:
                    raise ReleaseRejected('An unreviewed native program blocks complete removal')
    data,identity=bridge.memory_module('mount_transaction')._read(installed/'settings.json')
    current=json.loads(data)
    before[installed/'settings.json']={'type':'file','mode':identity['mode'],'sha256':identity['digest']}
    owned=json.loads((source/'hooks/hooks.json').read_bytes())['hooks']
    settings,receipt=bridge.memory_module('update_hooks').replace_owned_hooks(current,owned,{})
    return {'files':files,'dependencies':dependencies,'settings':(json.dumps(settings,indent=2)+'\n').encode(),
        'hook_receipt':receipt,'before':before}
