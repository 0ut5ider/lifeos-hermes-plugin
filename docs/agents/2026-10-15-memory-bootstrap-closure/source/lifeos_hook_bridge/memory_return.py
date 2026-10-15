# ABOUTME: Returns one profile to reviewed Hermes memory through a current-state file journal.
# ABOUTME: Preserves later edits and native data while requiring a verified external writer barrier.
import hashlib
import copy
import io
import json
import os
from pathlib import Path
import re
from uuid import uuid4

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from .memory_access import MemoryConflict, MemoryUnavailable
from .memory_backup import _directory, _read
from .memory_export import MemoryExport
from .memory_import import _encoded
from .memory_transaction import publish
from .mount_transaction import _read as read_target, _sync_directory


NAMES=('memories/MEMORY.md','memories/USER.md','SOUL.md','lifeos-memory.json','config.yaml')
STATES={'ready','applying','configured','restoring','rolled_back','cancelled'}


def _digest(data):
    return hashlib.sha256(data).hexdigest()


def _independent(value):
    result=copy.deepcopy(value)
    if isinstance(value,dict):
        for key,item in value.items():result[key]=item
    if hasattr(result,'yaml_set_anchor'):result.yaml_set_anchor(None)
    return result


class MemoryReturn:
    def __init__(self, configuration, *, installation_lease=None, verify_writers=None, operation_id=None):
        self.configuration=configuration
        self.exporter=MemoryExport(configuration,installation_lease=installation_lease)
        self.importer=self.exporter.importer
        self.profile=self.importer.profile
        self.verify_writers=verify_writers
        if operation_id is not None and (not isinstance(operation_id,str) or re.fullmatch('[0-9a-f]{32}',operation_id) is None):
            raise ValueError('Provider return requires a server-issued operation identifier')
        self.operation_id=operation_id

    def _configuration(self, data):
        yaml=YAML();yaml.preserve_quotes=True
        try:config=yaml.load(data.decode())
        except (YAMLError,UnicodeError,RecursionError) as error:
            raise MemoryUnavailable('The current Hermes configuration cannot be returned safely') from error
        if not isinstance(config,dict):raise MemoryUnavailable('Hermes return requires a configuration mapping')
        memory=config.setdefault('memory',{})
        plugins=config.setdefault('plugins',{})
        skills=config.setdefault('skills',{})
        if any(not isinstance(value,dict) or getattr(value,'merge',None)
                or getattr(getattr(value,'anchor',None),'value',None) for value in (config,memory,plugins,skills)):
            raise MemoryUnavailable('Hermes return requires unambiguous independent settings')
        memory.update(provider='builtin',memory_enabled=True,user_profile_enabled=True)
        enabled=_independent(plugins.get('enabled',[]));disabled=_independent(plugins.get('disabled',[]))
        entries=_independent(plugins.get('entries',{}))
        if not isinstance(enabled,list) or not isinstance(disabled,list) or not isinstance(entries,dict):
            raise MemoryUnavailable('Hermes return requires supported plugin selections')
        plugins.update(enabled=enabled,disabled=disabled,entries=entries)
        for name in ('lifeos','lifeos-hook-bridge'):
            enabled[:]=[entry for entry in enabled if entry!=name]
            if name not in disabled:disabled.append(name)
            if name in entries:
                if not isinstance(entries[name],dict):raise MemoryUnavailable('A LifeOS plugin entry is ambiguous')
                entries[name]=_independent(entries[name])
                entries[name]['enabled']=False
        if 'external_dirs' in skills:
            directories=skills['external_dirs']
            if not isinstance(directories,list) or any(not isinstance(path,str) for path in directories):
                raise MemoryUnavailable('Hermes return requires explicit external skill directories')
            skills['external_dirs']=[path for path in directories if path!=str(self.importer.installed/'skills')]
        output=io.StringIO();yaml.dump(config,output)
        return output.getvalue().encode()

    def prepare(self, destination, export_signature, export_plan_signature, *, prompt, account=None):
        destination=Path(destination).absolute()
        if not isinstance(prompt,str) or not prompt.strip() or len(prompt.encode())>256*1024 or '\x00' in prompt:
            raise ValueError('Choose a bounded reviewed Hermes prompt for provider return')
        with self.importer._locks(account) as selected:
            document,captured=self.exporter.inspect(destination,export_signature,account=account)
            export_plan=self.exporter._plan(destination,export_signature,export_plan_signature,account)
            if not export_plan['ready_for_return']:
                raise MemoryUnavailable('Resolve or explicitly retain required export items before returning to Hermes')
            self.exporter._current(captured,account)
            for name,content in export_plan['files'].items():
                actual,_=_read(destination/'hermes'/name,private=True)
                if actual!=content.encode():raise MemoryUnavailable('The reviewed Hermes export changes before return')
            config,_=read_target(self.profile/'config.yaml')
            native={**selected,'ownership_enabled':False,'sharing_enabled':False}
            self.configuration.validate(native)
            outputs={'config.yaml':self._configuration(config),'lifeos-memory.json':_encoded(native),'SOUL.md':prompt.encode(),
                **{'memories/'+name:content.encode() for name,content in export_plan['files'].items()}}
            final=destination/'return'
            if final.exists() or final.is_symlink():raise MemoryUnavailable('Use the existing return review or prepare a new export')
            state=destination/('.return-preparing-'+uuid4().hex)
            state.mkdir(mode=0o700)
            publish(state/'preparation.json',_encoded({'profile':str(self.profile),'writer':account,
                'operation_id':self.operation_id,'export_signature':export_signature,
                'export_plan_signature':export_plan_signature}))
            targets=[]
            for index,name in enumerate(NAMES):
                before,metadata=read_target(self.profile/name)
                if before is not None:publish(state/'before'/str(index),before)
                after=outputs[name]
                publish(state/'after'/str(index),after)
                targets.append({'name':name,'copy':index,'before':metadata,'after':{'digest':_digest(after),'mode':0o600}})
            plan={'version':1,'profile':str(self.profile),'root':str(self.importer.installed),'principal':self.importer.principal,
                'operation_id':self.operation_id,
                'writer':account,'export_signature':export_signature,'export_plan_signature':export_plan_signature,
                'snapshot_signature':document['snapshot_signature'],'target_signature':captured['target_signature'],'targets':targets}
            data=_encoded(plan);signature=_digest(data)
            publish(state/'plan.json',data)
            self._state(state,signature,'ready')
            os.rename(state,final);_sync_directory(destination)
            return {'state':'ready','signature':signature,'files':list(NAMES),'prompt':prompt,
                'restart_required':True,'application_verified':False,'native_data_retained':True,
                'lifeos_plugins_disabled':['lifeos','lifeos-hook-bridge'],'lifeos_background_jobs':'stop before application'}

    @staticmethod
    def _state(directory, signature, state):
        publish(directory/'operation.json',_encoded({'signature':signature,'state':state}))

    def owns_operation(self, destination, *, account=None):
        path=Path(destination).absolute()/'return/plan.json'
        if not path.exists():return False
        data,_=_read(path,private=True);plan=json.loads(data)
        if not isinstance(plan,dict) or plan.get('writer')!=account:
            raise MemoryUnavailable('The return preparation belongs to another installation owner')
        return plan.get('operation_id')==self.operation_id

    def _load(self, destination, signature, account):
        directory=destination/'return'
        _directory(directory,private=True)
        data,_=_read(directory/'plan.json',private=True)
        if not isinstance(signature,str) or _digest(data)!=signature:raise MemoryUnavailable('The return plan changes after review')
        try:plan=json.loads(data)
        except (ValueError,UnicodeError,RecursionError) as error:
            raise MemoryUnavailable('The return plan has invalid metadata') from error
        fields={'version','profile','root','principal','writer','export_signature','export_plan_signature','snapshot_signature','target_signature','targets','operation_id'}
        if (not isinstance(plan,dict) or set(plan)!=fields or type(plan['version']) is not int or plan['version']!=1
                or plan['profile']!=str(self.profile) or plan['root']!=str(self.importer.installed)
                or plan['principal']!=self.importer.principal or plan['writer']!=account or plan['operation_id']!=self.operation_id
                or not isinstance(plan['targets'],list) or len(plan['targets'])!=len(NAMES)):
            raise MemoryUnavailable('The return plan belongs to another owner or installation')
        copies={}
        for index,(name,entry) in enumerate(zip(NAMES,plan['targets'],strict=True)):
            if (not isinstance(entry,dict) or set(entry)!={'name','copy','before','after'} or entry['name']!=name
                    or type(entry['copy']) is not int or entry['copy']!=index):
                raise MemoryUnavailable('The return plan has invalid file targets')
            for side in ('before','after'):
                metadata=entry[side]
                if metadata is None and side=='before':continue
                if (not isinstance(metadata,dict) or set(metadata)!={'digest','mode'}
                        or not isinstance(metadata['digest'],str) or re.fullmatch('[0-9a-f]{64}',metadata['digest']) is None
                        or type(metadata['mode']) is not int or not 0<=metadata['mode']<=0o777):
                    raise MemoryUnavailable('The return plan has invalid target identities')
                data,_=_read(directory/side/str(index),private=True)
                if _digest(data)!=metadata['digest']:raise MemoryUnavailable('A retained return copy changes after review')
                copies[(name,side)]=data
        data,_=_read(directory/'operation.json',private=True)
        operation=json.loads(data)
        if (not isinstance(operation,dict) or set(operation)!={'signature','state'}
                or operation['signature']!=signature or operation['state'] not in STATES):
            raise MemoryUnavailable('The return operation has invalid state')
        return plan,operation,copies

    def cancel_preparation(self, destination, signature, *, account=None):
        destination=Path(destination).absolute()
        with self.importer._locks(account):
            plan,operation,_=self._load(destination,signature,account)
            if operation['state'] not in {'ready','cancelled'}:
                raise MemoryUnavailable('Only an unapplied return preparation can be cancelled')
            history=destination/'return-history';history.mkdir(mode=0o700,exist_ok=True)
            _directory(history,private=True)
            self._state(destination/'return',signature,'cancelled')
            retained=history/uuid4().hex
            os.rename(destination/'return',retained);_sync_directory(destination);_sync_directory(history)
            return {'state':'cancelled','signature':signature,'native_data_retained':True,'application_verified':False}

    def _barrier(self):
        if not callable(self.verify_writers):raise MemoryUnavailable('Provider return requires a verified profile writer barrier')
        self.verify_writers()

    def _check(self, plan, *, sides):
        for entry in plan['targets']:
            _,metadata=read_target(self.profile/entry['name'])
            if metadata not in [entry[side] for side in sides]:
                raise MemoryConflict('Provider return preserves a later profile file edit')

    def _native_current(self, plan, connection=None):
        if connection is None:
            with self.importer.memory._transaction() as selected:
                return self._native_current(plan,selected)
        if self.importer._target_signature(connection)!=plan['target_signature']:
            raise MemoryConflict('LifeOS facts change after reverse export review')

    def _publish_target(self, entry, side, copies):
        path=self.profile/entry['name']
        metadata=entry[side]
        if metadata is None:
            path.unlink(missing_ok=True);_sync_directory(path.parent)
        else:
            publish(path,copies[(entry['name'],side)],mode=metadata['mode'])

    def apply(self, destination, signature, *, account=None):
        destination=Path(destination).absolute()
        with self.importer._locks(account), self.importer.memory._transaction() as connection:
            plan,operation,copies=self._load(destination,signature,account)
            if operation['state'] not in {'ready','applying','configured'}:
                raise MemoryUnavailable('The return operation requires recovery before application')
            self._barrier();self._native_current(plan,connection)
            self._check(plan,sides=('after',) if operation['state']=='configured' else ('before','after'))
            self._state(destination/'return',signature,'applying')
            for entry in plan['targets']:
                self._barrier();self._check(plan,sides=('before','after'))
                self.importer._owner(account)
                self._publish_target(entry,'after',copies)
            self._barrier();self._native_current(plan,connection);self._check(plan,sides=('after',))
            self._state(destination/'return',signature,'configured')
            return {'state':'configured','signature':signature,'restart_required':True,'application_verified':False,'native_data_retained':True}

    def rollback(self, destination, signature, *, account=None):
        destination=Path(destination).absolute()
        with self.importer._locks(account):
            plan,_,copies=self._load(destination,signature,account)
            self._barrier();self._check(plan,sides=('before','after'))
            self._state(destination/'return',signature,'restoring')
            for entry in reversed(plan['targets']):
                self._barrier();self._check(plan,sides=('before','after'))
                self.importer._owner(account)
                self._publish_target(entry,'before',copies)
            self._check(plan,sides=('before',))
            self._state(destination/'return',signature,'rolled_back')
            return {'state':'rolled_back','signature':signature,'restart_required':True,'application_verified':False,'native_data_retained':True}
