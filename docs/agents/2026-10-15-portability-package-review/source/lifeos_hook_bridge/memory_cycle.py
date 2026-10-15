# ABOUTME: Archives terminal ownership journals before a newly reviewed activation cycle.
# ABOUTME: Resumes journal moves after interruption without restoring configuration or memory data.
import hashlib
import json
import os
from pathlib import Path
import re
from uuid import uuid4

from .memory_access import MemoryUnavailable
from .memory_backup import _directory,_read
from .memory_transaction import publish
from .mount_transaction import _sync_directory


NAMES={'.lifeos-memory-activation','.lifeos-ownership-setup','.lifeos-ownership','.lifeos-memory-transition'}


def _encoded(value):
    return json.dumps(value,sort_keys=True,separators=(',',':')).encode()


def _identity(directory):
    _directory(directory,private=True);result={'.':{'mode':directory.stat().st_mode & 0o777}}
    for path in sorted(directory.rglob('*')):
        if path.is_symlink():raise MemoryUnavailable('A terminal ownership journal changes its physical path')
        if path.is_dir():
            _directory(path,private=True);value={'mode':path.stat().st_mode & 0o777}
        else:
            data,metadata=_read(path,private=True)
            value={'mode':metadata['mode'],'sha256':hashlib.sha256(data).hexdigest()}
        result[path.relative_to(directory).as_posix()]=value
        if len(result)>2048:raise MemoryUnavailable('The terminal ownership journal exceeds its archive limit')
    return result


def _resume(configuration, account):
    profile=configuration.path.parent.absolute();marker=profile/'.lifeos-memory-cycle.json'
    data,_=_read(marker,private=True);plan=json.loads(data);selected=configuration.load()
    configuration.check_owner(selected,account)
    if (not isinstance(plan,dict) or set(plan)!={'version','profile','root','owner','identifier','entries'}
            or plan['version']!=1 or plan['profile']!=str(profile) or plan['root']!=selected['root'] or plan['owner']!=account
            or not isinstance(plan['identifier'],str) or re.fullmatch('[0-9a-f]{32}',plan['identifier']) is None
            or selected.get('ownership_enabled') is not False or not isinstance(plan['entries'],dict)
            or not set(plan['entries'])<=NAMES or '.lifeos-memory-transition' not in plan['entries']):
        raise MemoryUnavailable('The ownership cycle archive belongs to another owner or live selection')
    history=profile/'.lifeos-memory-cycle-history';_directory(history,private=True)
    archive=history/plan['identifier'];_directory(archive,private=True)
    original,_=_read(archive/'plan.json',private=True)
    if original!=data:raise MemoryUnavailable('The terminal ownership archive changes its admitted plan')
    for name,identity in plan['entries'].items():
        source=profile/name;target=archive/name
        if source.exists() or source.is_symlink():
            if target.exists() or target.is_symlink() or _identity(source)!=identity:
                raise MemoryUnavailable('The terminal ownership journal changes before archival')
        elif not target.exists() or _identity(target)!=identity:
            raise MemoryUnavailable('The terminal ownership archive loses its retained journal')
    for name,identity in plan['entries'].items():
        source=profile/name;target=archive/name
        if not source.exists():continue
        if _identity(source)!=identity:
            raise MemoryUnavailable('The terminal ownership journal changes during archival')
        os.rename(source,target);_sync_directory(archive);_sync_directory(profile)
        if _identity(target)!=identity:raise MemoryUnavailable('The retained terminal ownership journal changes')
    publish(archive/'receipt.json',_encoded({'state':'archived','configuration_restored':False,'memory_restored':False}))
    marker.unlink();_sync_directory(profile)


def retire_verified_return(configuration, *, account, units=None, installation_lease=None):
    from .memory_transition import MemoryTransition
    from .memory_return import MemoryReturn,_digest
    from .ownership_setup import OwnershipSetup
    from .memory_ownership import OwnershipTransaction
    profile=configuration.path.parent.absolute();marker=profile/'.lifeos-memory-cycle.json'
    selected=configuration.load();configuration.check_owner(selected,account)
    if marker.exists() or marker.is_symlink():
        _resume(configuration,account);return
    directory=profile/'.lifeos-memory-transition'
    if not directory.exists():return
    if selected.get('ownership_enabled') is not False:
        raise MemoryUnavailable('A new ownership cycle requires the reviewed returned provider')
    data,_=_read(directory/'plan.json',private=True);previous=json.loads(data)
    transition=MemoryTransition(configuration,units=units,installation_lease=installation_lease,
        operation_id=previous.get('operation_id'))
    plan,state=transition._load(_digest(data),account)
    if state!='verified':raise MemoryUnavailable('Verify or recover the existing provider return before another activation')
    returned=MemoryReturn(configuration,installation_lease=installation_lease,operation_id=plan['operation_id'])
    inner,current,_=returned._load(Path(plan['snapshot']),plan['return_signature'],account)
    proof_data,_=_read(directory/'fresh-agent-verification.json',private=True);proof=json.loads(proof_data)
    if (current['state']!='configured' or proof.get('format')!=1 or proof.get('provider')!='builtin'
            or proof.get('fresh_agent_verified') is not True or proof.get('model_turn_executed') is not False
            or proof.get('profile')!=str(profile) or proof.get('files')!={item['name']:item['after'] for item in inner['targets']}):
        raise MemoryUnavailable('The previous provider return loses its exact fresh-session proof')
    setup=OwnershipSetup(configuration,units=units,installation_lease=installation_lease)
    existing=setup._load();ownership=OwnershipTransaction(configuration,installation_lease=installation_lease)._load(selected)
    if existing is not None or ownership is not None:
        if (existing is None or ownership is None or existing['state']!='configured' or ownership['state']!='committed'
                or ownership['signature']!=existing['plan']['ownership_signature']):
            raise MemoryUnavailable('The previous ownership journals are not a matched terminal setup')
    names={name for name in NAMES if (profile/name).exists() or (profile/name).is_symlink()}
    identities={name:_identity(profile/name) for name in sorted(names)}
    history=profile/'.lifeos-memory-cycle-history';history.mkdir(mode=0o700,exist_ok=True);_directory(history,private=True)
    identifier=uuid4().hex;archive=history/identifier;archive.mkdir(mode=0o700)
    document={'version':1,'profile':str(profile),'root':selected['root'],'owner':account,'identifier':identifier,'entries':identities}
    encoded=_encoded(document);publish(archive/'plan.json',encoded);publish(marker,encoded)
    _resume(configuration,account)
