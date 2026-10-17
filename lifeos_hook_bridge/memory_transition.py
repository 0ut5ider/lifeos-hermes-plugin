# ABOUTME: Coordinates reviewed provider return with actual profile service barriers and recovery.
# ABOUTME: Leaves Pulse stopped and disabled, preserves native data, and requires a fresh-session proof.
from contextlib import contextmanager
import json
import os
from pathlib import Path
import re
import subprocess
from uuid import uuid4

from .installation_lock import installation_lock
from . import program_lock
from .memory_access import MemoryUnavailable
from .memory_backup import _directory, _read
from .memory_import import _encoded
from .memory_return import MemoryReturn, _digest
from .memory_transaction import publish
from .mount_transaction import _sync_directory
from .profile_services import ProfileServices


STATES={'ready','draining','publishing','configured','restarting','verification_required',
        'verified','restoring','rolled_back'}
ENABLEMENT={'enabled','enabled-runtime','disabled','static','linked','linked-runtime','indirect'}


class MemoryTransition:
    def __init__(self, configuration, *, units=None, installation_lease=None, operation_id=None):
        self.configuration=configuration
        self.profile=configuration.path.parent.absolute()
        selected=configuration.load()
        self.installed=Path(selected['root']).absolute()
        self.lease=installation_lease
        if operation_id is not None and (not isinstance(operation_id,str) or re.fullmatch('[0-9a-f]{32}',operation_id) is None):
            raise ValueError('Provider transition requires a server-issued operation identifier')
        self.operation_id=operation_id
        # An in-place host passes only the units it has; their roles become the bound service set.
        self.units=ProfileServices(self.profile,self.installed,units=units).units
        self.directory=self.profile/'.lifeos-memory-transition'

    @contextmanager
    def _lock(self, account):
        with installation_lock(self.profile,lease=self.lease) as lease:
            selected=self.configuration.load()
            self.configuration.check_owner(selected,account)
            if not isinstance(account,str) or not account.startswith('dashboard:'):
                raise PermissionError('An authenticated installation owner must authorize provider return')
            if selected['root']!=str(self.installed):
                raise MemoryUnavailable('The selected native store changes during provider return')
            self.directory.mkdir(mode=0o700,exist_ok=True);_directory(self.directory,private=True)
            services=ProfileServices(self.profile,self.installed,units=self.units,
                installation_lease=lease)
            operation=MemoryReturn(self.configuration,installation_lease=lease,verify_writers=services.verify_stopped,
                operation_id=self.operation_id)
            yield services,operation

    def _load(self, signature, account):
        data,_=_read(self.directory/'plan.json',private=True)
        if not isinstance(signature,str) or _digest(data)!=signature:
            raise MemoryUnavailable('Provider return requires the exact reviewed transition signature')
        plan=json.loads(data)
        if (not isinstance(plan,dict) or set(plan)!={'version','profile','root','owner','units','snapshot',
                'return_signature','services_signature','original_roles','pulse_enablement','operation_id'}
                or plan['version']!=1 or plan['profile']!=str(self.profile) or plan['root']!=str(self.installed)
                or plan['owner']!=account or plan['units']!=self.units or plan['operation_id']!=self.operation_id
                or not isinstance(plan['original_roles'],list)
                or any(role not in self.units for role in plan['original_roles'])
                or plan['pulse_enablement'] not in ENABLEMENT
                or not isinstance(plan['snapshot'],str) or not Path(plan['snapshot']).is_absolute()
                or any(not isinstance(plan[key],str) or re.fullmatch('[0-9a-f]{64}',plan[key]) is None
                    for key in ('return_signature','services_signature'))):
            raise MemoryUnavailable('The provider transition belongs to another owner or installation')
        data,_=_read(self.directory/'operation.json',private=True);state=json.loads(data)
        if (not isinstance(state,dict) or set(state)!={'signature','state'}
                or state['signature']!=signature or state['state'] not in STATES):
            raise MemoryUnavailable('The provider transition has invalid private state')
        return plan,state['state']

    def _state(self, signature, state):
        publish(self.directory/'operation.json',_encoded({'signature':signature,'state':state}))

    def owns_operation(self, *, account=None):
        if not (self.directory/'plan.json').exists():return False
        data,_=_read(self.directory/'plan.json',private=True)
        value=json.loads(data)
        if not isinstance(value,dict) or value.get('owner')!=account:
            raise MemoryUnavailable('The provider transition belongs to another installation owner')
        return value.get('operation_id')==self.operation_id

    def _archive(self):
        history=self.profile/'.lifeos-memory-transition-history'
        history.mkdir(mode=0o700,exist_ok=True);_directory(history,private=True)
        os.rename(self.directory,history/uuid4().hex)
        _sync_directory(history);_sync_directory(self.profile)

    def cancel_preparation(self, signature, *, account=None):
        with self._lock(account):
            _,state=self._load(signature,account)
            if state not in {'ready','rolled_back'}:
                raise MemoryUnavailable('Only an unapplied provider transition can be cancelled')
            self._state(signature,'rolled_back')
            self._archive()
            return {'signature':signature,'state':'cancelled','application_verified':False,'native_data_retained':True}

    def _enablement(self):
        result=subprocess.run(['systemctl','--user','show',self.units['pulse'],
            '--property=UnitFileState','--value'],text=True,capture_output=True,timeout=30)
        value=result.stdout.strip()
        if result.returncode or result.stderr or value not in ENABLEMENT:
            raise MemoryUnavailable('Pulse requires a supported current service enablement state')
        return value

    def _pulse_layout(self, services, enablement):
        if enablement not in {'enabled','enabled-runtime'}:return
        values,_=services._inspect('pulse')
        fragment=Path(values['FragmentPath'])
        directories={Path.home()/'.config/systemd/user',Path('/run/user')/str(os.getuid())/'systemd/user'}
        if fragment.parent not in directories or fragment.is_symlink() or fragment.name!=self.units['pulse']:
            raise MemoryUnavailable('Enabled Pulse requires a regular installed user service definition')

    def _enabled(self, desired, original):
        current=self._enablement()
        disabled='disabled' if original in {'enabled','enabled-runtime'} else original
        if current not in {original,disabled}:
            raise MemoryUnavailable('Pulse enablement changes outside the reviewed provider return')
        if current==desired:return
        command=['systemctl','--user',('enable' if desired in {'enabled','enabled-runtime'} else 'disable')]
        if original=='enabled-runtime':command.append('--runtime')
        result=subprocess.run([*command,self.units['pulse']],text=True,capture_output=True,timeout=30)
        if result.returncode or self._enablement()!=desired:
            raise MemoryUnavailable('Pulse does not reach its reviewed enablement state')

    @staticmethod
    def _receipt(signature, state):
        return {'signature':signature,'state':state,'native_data_retained':True,
            'application_verified':state=='verified','fresh_session_required':state!='verified',
            'pulse_stopped':state in {'verification_required','verified'}}

    def prepare_return(self, destination, return_signature, *, account=None):
        destination=Path(destination).absolute()
        with self._lock(account) as (services,operation):
            if (self.directory/'plan.json').exists() or (self.directory/'plan.json').is_symlink():
                data,_=_read(self.directory/'plan.json',private=True)
                previous=json.loads(data)
                prior=MemoryTransition(self.configuration,units=self.units,operation_id=previous.get('operation_id'))
                _,old_state=prior._load(_digest(data),account)
                if old_state!='rolled_back':
                    raise MemoryUnavailable('Complete or recover the existing provider transition first')
                self._archive();self.directory.mkdir(mode=0o700)
            plan,state,_=operation._load(destination,return_signature,account)
            if state['state']!='ready':raise MemoryUnavailable('Prepare an unapplied reviewed provider return')
            operation._check(plan,sides=('before',));operation._native_current(plan)
            admitted=services._admission()
            self._pulse_layout(services,self._enablement())
            service_signature=services.preview()['signature']
            if services._signature(admitted)!=service_signature:
                raise MemoryUnavailable('The profile service state changes during transition review')
            document={'version':1,'profile':str(self.profile),'root':str(self.installed),'owner':account,
                'operation_id':self.operation_id,
                'units':self.units,'snapshot':str(destination),'return_signature':return_signature,
                'services_signature':service_signature,'pulse_enablement':self._enablement(),
                'original_roles':[role for role,item in admitted['services'].items() if item['active']]}
            data=_encoded(document);signature=_digest(data)
            stage=self.profile/('.lifeos-memory-transition-preparing-'+uuid4().hex)
            stage.mkdir(mode=0o700)
            publish(stage/'plan.json',data)
            publish(stage/'operation.json',_encoded({'signature':signature,'state':'ready'}))
            os.rename(stage,self.directory);_sync_directory(self.profile)
            return self._receipt(signature,'ready')

    def status(self, signature, *, account=None):
        with self._lock(account):
            _,state=self._load(signature,account)
            return self._receipt(signature,state)

    def apply(self, signature, *, account=None, checkpoint=lambda point:None):
        with self._lock(account) as (services,operation):
            plan,state=self._load(signature,account)
            if state in {'verification_required','verified'}:return self._receipt(signature,state)
            if state in {'restoring','rolled_back'}:raise MemoryUnavailable('Recover the provider transition before application')
            snapshot=Path(plan['snapshot'])
            target,_,_=operation._load(snapshot,plan['return_signature'],account)
            operation._check(target,sides=('before',) if state=='ready' else ('before','after'))
            operation._native_current(target)
            if state=='ready':
                if services.preview()['signature']!=plan['services_signature'] or self._enablement()!=plan['pulse_enablement']:
                    raise MemoryUnavailable('The reviewed service state changes before provider return')
            with program_lock.exclusive(self.profile,600):
                if state=='ready' or state=='draining' and services.status()['state'] in {'none','active'}:
                    self._state(signature,'draining');services.drain(signature=plan['services_signature'])
                else:services.quiesce()
                services.verify_stopped();checkpoint('drained')
                self._state(signature,'publishing')
                operation.apply(snapshot,plan['return_signature'],account=account)
                self._state(signature,'configured');checkpoint('configured')
                desired='disabled' if plan['pulse_enablement'] in {'enabled','enabled-runtime'} else plan['pulse_enablement']
                self._enabled(desired,plan['pulse_enablement']);services.verify_stopped()
                self._state(signature,'restarting')
                services.resume(roles=[role for role in ('dashboard','gateway') if role in self.units])
                checkpoint('restarted')
                self._state(signature,'verification_required')
            return self._receipt(signature,'verification_required')

    def rollback(self, signature, *, account=None):
        with self._lock(account) as (services,operation):
            plan,state=self._load(signature,account)
            if state=='rolled_back':return self._receipt(signature,state)
            target,_,_=operation._load(Path(plan['snapshot']),plan['return_signature'],account)
            operation._check(target,sides=('before','after'))
            if state=='ready' or state=='draining' and services.status()['state'] in {'none','active'}:
                if services.preview()['signature']!=plan['services_signature']:
                    raise MemoryUnavailable('The profile services change before return cancellation')
                self._state(signature,'rolled_back');return self._receipt(signature,'rolled_back')
            with program_lock.exclusive(self.profile,600):
                self._state(signature,'restoring');services.quiesce();services.verify_stopped()
                operation.rollback(Path(plan['snapshot']),plan['return_signature'],account=account)
                self._enabled(plan['pulse_enablement'],plan['pulse_enablement'])
                services.resume(roles=plan['original_roles'],activate=True)
                self._state(signature,'rolled_back')
            return self._receipt(signature,'rolled_back')

    def verify(self, signature, probe, *, account=None):
        if not callable(probe):raise ValueError('Provider return requires an actual fresh-agent verifier')
        with self._lock(account) as (services,operation):
            plan,state=self._load(signature,account)
            if state not in {'verification_required','verified'}:
                raise MemoryUnavailable('Finish the provider return and service restart before verification')
            target,_,copies=operation._load(Path(plan['snapshot']),plan['return_signature'],account)
            operation._check(target,sides=('after',))
            expected={name:copies[('memories/'+name,'after')].decode() for name in ('MEMORY.md','USER.md')}
            services.verify_active()
            proof=probe(expected)
            expected_files={entry['name']:entry['after'] for entry in target['targets']}
            if (not isinstance(proof,dict) or proof.get('format')!=1 or proof.get('provider')!='builtin'
                    or proof.get('fresh_agent_verified') is not True or proof.get('model_turn_executed') is not False
                    or proof.get('profile')!=str(self.profile) or proof.get('files')!=expected_files):
                raise MemoryUnavailable('The fresh-agent proof does not match the reviewed current profile')
            operation._check(target,sides=('after',));services.verify_active()
            publish(self.directory/'fresh-agent-verification.json',_encoded(proof))
            self._state(signature,'verified')
            return {**self._receipt(signature,'verified'),'verification':proof}
