# ABOUTME: Selects current stock Hermes settings after an owner verifies provider return.
# ABOUTME: Removes integration selections and explicitly disables Discord while retaining credentials.
import copy
import io
from pathlib import Path

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from .release_catalog import ReleaseRejected


PLUGINS=frozenset({'lifeos','lifeos-hook-bridge','lifeos-release-manager'})


def _copy(value):
    result=copy.deepcopy(value)
    if hasattr(result,'yaml_set_anchor'):result.yaml_set_anchor(None)
    return result


def _mapping(config, name):
    value=config.get(name,{})
    if (not isinstance(value,dict) or getattr(value,'merge',None)
            or getattr(getattr(value,'anchor',None),'value',None)):
        raise ReleaseRejected('Removal requires independent explicit configuration mappings')
    value=_copy(value);config[name]=value
    return value


def configuration(data, installed, recorded=None):
    yaml=YAML();yaml.preserve_quotes=True
    try:value=yaml.load(data.decode())
    except (YAMLError,UnicodeError,RecursionError) as error:
        raise ReleaseRejected('The current Hermes configuration cannot be removed safely') from error
    if not isinstance(value,dict) or getattr(value,'merge',None):
        raise ReleaseRejected('Removal requires an explicit current configuration mapping')
    if recorded is not None:
        # Values LifeOS changed return to their pre-installation values unless the owner changed them since.
        from .host_configuration import restore
        value,_=restore(value,recorded)
    memory=_mapping(value,'memory')
    if (memory.get('provider','builtin') not in (None,'builtin') or memory.get('memory_enabled',True) is not True
            or memory.get('user_profile_enabled',True) is not True):
        raise ReleaseRejected('Verify the reviewed built-in memory return before complete removal')
    memory.pop('provider',None)
    memory.update(memory_enabled=True,user_profile_enabled=True)
    plugins=_mapping(value,'plugins')
    for name in ('enabled','disabled'):
        items=plugins.get(name,[])
        if not isinstance(items,list) or any(not isinstance(item,str) for item in items):
            raise ReleaseRejected('Removal requires explicit plugin selections')
        plugins[name]=[item for item in items if item not in PLUGINS]
    entries=plugins.get('entries',{})
    if not isinstance(entries,dict):raise ReleaseRejected('Removal requires explicit plugin settings')
    plugins['entries']={name:entry for name,entry in entries.items() if name not in PLUGINS}
    skills=_mapping(value,'skills')
    if 'external_dirs' in skills:
        directories=skills['external_dirs']
        if not isinstance(directories,list) or any(not isinstance(path,str) for path in directories):
            raise ReleaseRejected('Removal requires explicit external skill directories')
        skills['external_dirs']=[path for path in directories if path!=str(Path(installed)/'skills')]
    platforms=_mapping(value,'platforms')
    discord=platforms.get('discord',{})
    if not isinstance(discord,dict) or getattr(discord,'merge',None):
        raise ReleaseRejected('Removal requires explicit Discord settings')
    discord=_copy(discord);discord['enabled']=False;platforms['discord']=discord
    output=io.StringIO();yaml.dump(value,output)
    return output.getvalue().encode()


def environment_block(profile, workspace):
    return ('\n\n# Writes are hard-blocked outside these roots. The LifeOS tree is\n'
        '# READ-only to the sidecar; persistence goes through the memory API.\n'
        'HERMES_WRITE_SAFE_ROOT='+str(workspace)+':'+str(profile)+'\n').encode()


def environment(data, profile, workspace):
    block=environment_block(profile,workspace)
    if data.count(block)>1:raise ReleaseRejected('The owned environment block is ambiguous')
    from hermes_cli.config import _sanitize_env_lines
    # The block starts with its own line break; a later owner line must not join an unterminated line before it.
    before,found,after=data.partition(block)
    separator=b'\n' if found and after and before and not before.endswith((b'\n',b'\r')) else b''
    try:lines=io.StringIO((before+separator+after).decode('utf-8-sig'),newline=None).readlines()
    except UnicodeError as error:raise ReleaseRejected('The current environment requires valid UTF-8 before removal') from error
    return ''.join(_sanitize_env_lines(lines)).encode()
