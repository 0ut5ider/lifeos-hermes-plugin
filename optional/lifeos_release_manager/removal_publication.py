# ABOUTME: Publishes a reviewed software removal under the owner, native writer, and service barriers.
# ABOUTME: Resumes interrupted program changes, synchronizes an in-place host environment, and keeps later memory.
import json
from pathlib import Path

from .cli import read_private
from .release_catalog import ReleaseRejected
from .release_programs import ProgramTransaction,publish
from .removal_services import RemovalServices
from .removal_data import barrier
from .removal_state import retained


STATES={'ready','draining','publishing','restarting','verification_required','verified','restoring','rolled_back'}


class RemovalPublication:
    def __init__(self, profile, signature, *, services=None, installation_lease=None):
        self.profile=Path(profile).absolute()
        self.source,self.configuration,self.job,self.plan=retained(self.profile)
        if self.plan['signature']!=signature:
            raise ReleaseRejected('Software removal requires the exact reviewed owner signature')
        for field in ('program_entries_sha256','service_signature','native_signature'):
            if not isinstance(self.plan.get(field),str) or len(self.plan[field])!=64:
                raise ReleaseRejected('Software removal has an incomplete publication review')
        self.signature=signature;self.lease=installation_lease;self.stage=self.job/'removal'
        self.programs=ProgramTransaction(self.stage/'programs',expected_entries_sha256=self.plan['program_entries_sha256'])
        units=self.plan.get('service_units')
        controller=self.source.memory_module('profile_services').ProfileServices(self.profile,Path(self.plan['root']),
            units=units,installation_lease=installation_lease) if services is None else None
        self.services=RemovalServices(controller,self.stage/'services.json') if services is None else services
        bindings=self.services._load(self.plan['service_signature'])
        if bindings['profile']!=str(self.profile) or bindings['installed']!=self.plan['root']:
            raise ReleaseRejected('The removal service barrier belongs to another installation')
        self.importer=self.source.memory_module('memory_import').MemoryImport(self.configuration)
        root=Path(self.plan['root'])
        protected=(root.parent/'.config/LIFEOS/USER',self.profile/'memories',self.profile/'SOUL.md',
            self.stage,root/'LIFEOS/USER',root/'LIFEOS/MEMORY',self.profile/'workspace',root.parent/'workspace')
        for entry in self.programs.entries():
            target=Path(entry['target'])
            if any(target.is_relative_to(path) or path.is_relative_to(target) for path in protected):
                raise ReleaseRejected('Software removal cannot target personal data or its recovery sources')

    def _owner(self, account):
        if not isinstance(account,str) or account!=self.plan['owner']:
            raise PermissionError('The authenticated installation owner must authorize software removal')
        value=self.configuration.load();self.configuration.check_owner(value,account)
        if value.get('ownership_enabled') is not False or value['root']!=self.plan['root']:
            raise ReleaseRejected('Verify provider return before software removal')

    def _load(self):
        value=read_private(self.stage/'operation.json')
        if (not isinstance(value,dict) or set(value)!={'signature','state'} or value['signature']!=self.signature
                or value['state'] not in STATES):
            raise ReleaseRejected('The removal publication journal has invalid owner state')
        return value['state']

    def _state(self, state):
        publish(self.stage/'operation.json',json.dumps({'signature':self.signature,'state':state},sort_keys=True).encode())

    def _receipt(self, state):
        return {'state':state,'signature':self.signature,'native_data_retained':True,'builtin_memory_retained':True,
            'application_verified':state=='verified'}

    def _host_files(self):
        if 'host' in self.plan:
            from .inplace_removal import check_host_files
            check_host_files(self.programs.entries(),self.plan['host']['source'])

    def _synchronize(self, label, *, required):
        if 'host' not in self.plan:return
        from .inplace_removal import synchronize
        try:synchronize(self.stage,self.plan,label)
        except (ReleaseRejected,OSError,ValueError) as error:
            if required:raise
            # A rollback continues to restore the services; recovery can repeat the synchronization.
            publish(self.stage/(label+'-failure.json'),json.dumps({'error':type(error).__name__}).encode())

    def apply(self, *, account, checkpoint=lambda point:None):
        lock=self.source.memory_module('installation_lock').installation_lock
        program_lock=self.source.memory_module('program_lock')
        with lock(self.profile,lease=self.lease),program_lock.exclusive(self.profile,600):
            self._owner(account);state=self._load()
            if state in {'restoring','rolled_back'}:raise ReleaseRejected('Recover the reviewed software rollback before removal')
            if state in {'verification_required','verified'}:
                self.programs.check_applied();self.services.verify(self.plan['service_signature'])
                return self._receipt(state)
            self._host_files()
            if state=='ready':self.programs.check_prepared()
            else:self.programs.check_recovery()
            self._state('draining');self.services.stop(self.plan['service_signature']);checkpoint('drained')
            with self.configuration._lock(),barrier(self.importer.memory) as connection:
                self._owner(account)
                if self.importer._target_signature(connection)!=self.plan['native_signature']:
                    raise ReleaseRejected('Native facts change after the reviewed reverse export')
                self.services.verify_stopped(self.plan['service_signature'])
                self._state('publishing');self.programs.resume(checkpoint=checkpoint)
                self.programs.check_applied();checkpoint('programs-published')
                self._synchronize('dependency-removal',required=True);checkpoint('dependencies-synchronized')
                self._owner(account)
                if self.importer._target_signature(connection)!=self.plan['native_signature']:
                    raise ReleaseRejected('Native data changes during software removal')
                self._state('restarting');self.services.resume(self.plan['service_signature']);checkpoint('restarted')
                self._state('verification_required')
            return self._receipt('verification_required')

    def rollback(self, *, account, checkpoint=lambda point:None):
        lock=self.source.memory_module('installation_lock').installation_lock
        program_lock=self.source.memory_module('program_lock')
        with lock(self.profile,lease=self.lease),program_lock.exclusive(self.profile,600):
            self._owner(account);state=self._load()
            if state=='rolled_back':return self._receipt(state)
            self._host_files()
            self.programs.check_recovery()
            self._state('restoring');self.services.stop(self.plan['service_signature']);checkpoint('drained')
            with self.configuration._lock(),barrier(self.importer.memory):
                self._owner(account);self.services.verify_stopped(self.plan['service_signature'])
                self.programs.restore();checkpoint('programs-restored')
                self._synchronize('dependency-restore',required=False)
                self._owner(account);self.services.resume(self.plan['service_signature'],restored=True)
                self._state('rolled_back')
            return self._receipt('rolled_back')

    def verify(self, probe, *, account):
        if not callable(probe):raise ValueError('Removal requires an actual fresh stock agent verifier')
        lock=self.source.memory_module('installation_lock').installation_lock
        program_lock=self.source.memory_module('program_lock')
        with lock(self.profile,lease=self.lease),program_lock.exclusive(self.profile,600):
            self._owner(account)
            if self._load() not in {'verification_required','verified'}:
                raise ReleaseRejected('Finish software publication and service restart before final verification')
            self.programs.check_applied();self.services.verify(self.plan['service_signature'])
            read=self.source.memory_module('mount_transaction')._read
            names=('config.yaml','SOUL.md','lifeos-memory.json','memories/MEMORY.md','memories/USER.md')
            captured={name:read(self.profile/name) for name in names}
            expected={name:captured['memories/'+name][0].decode() for name in ('MEMORY.md','USER.md')}
            with barrier(self.importer.memory) as connection:
                if self.importer._target_signature(connection)!=self.plan['native_signature']:
                    raise ReleaseRejected('Native facts change before final software removal verification')
                proof=probe(expected)
            if (not isinstance(proof,dict) or proof.get('format')!=1 or proof.get('provider')!='builtin'
                    or proof.get('fresh_agent_verified') is not True or proof.get('model_turn_executed') is not False
                    or proof.get('profile')!=str(self.profile)
                    or proof.get('files')!={name:metadata for name,(_,metadata) in captured.items()}
                    or not isinstance(proof.get('active_plugins'),list)
                    or {'lifeos','lifeos-hook-bridge','lifeos-release-manager'} & set(proof['active_plugins'])
                    or proof.get('native_providers')):
                raise ReleaseRejected('The fresh stock agent does not prove complete removal and retained built-in memory')
            if any(read(self.profile/name)!=captured[name] for name in names):
                raise ReleaseRejected('The retained Hermes files change during final removal verification')
            self._owner(account);self.programs.check_applied();self.services.verify(self.plan['service_signature'])
            publish(self.stage/'fresh-agent-verification.json',json.dumps(proof,sort_keys=True).encode())
            self._state('verified')
            return {**self._receipt('verified'),'verification':proof}
