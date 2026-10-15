# ABOUTME: Admits a reviewed published import before the profile selects native LifeOS ownership.
# ABOUTME: Checks source identity and current references before and after actual service draining.
from contextlib import contextmanager
import json
import hashlib
from pathlib import Path
import re
from uuid import uuid4

from .installation_lock import installation_lock
from . import program_lock
from .memory_access import MemoryUnavailable
from .memory_backup import _directory, _read
from .memory_import import MemoryImport, _encoded
from .memory_transaction import publish
from .ownership_setup import OwnershipSetup


class MemoryActivation:
    def __init__(self, configuration, *, units=None, installation_lease=None):
        self.configuration=configuration
        self.profile=configuration.path.parent.absolute()
        self.units=units
        self.lease=installation_lease
        self.directory=self.profile/'.lifeos-memory-activation'

    def _binding(self, account):
        _directory(self.directory,private=True)
        data,_=_read(self.directory/'binding.json',private=True)
        value=json.loads(data)
        if (not isinstance(value,dict) or set(value)!={'owner','snapshot','snapshot_signature','plan_signature','source'}
                or value['owner']!=account or not isinstance(value['snapshot'],str)
                or not Path(value['snapshot']).is_absolute()
                or value['source'] is not None and (not isinstance(value['source'],str) or not Path(value['source']).is_absolute())
                or any(not isinstance(value[key],str) or re.fullmatch('[0-9a-f]{64}',value[key]) is None
                    for key in ('snapshot_signature','plan_signature'))):
            raise MemoryUnavailable('The activation binding belongs to another import or owner')
        return value

    def _verify(self, binding, account, lease):
        importer=MemoryImport(self.configuration,source_directory=binding['source'],installation_lease=lease)
        snapshot=Path(binding['snapshot'])
        status=importer.status(snapshot,binding['snapshot_signature'],account=account)
        publication=status['publication']
        if (status['plan'] is None or status['plan']['signature']!=binding['plan_signature']
                or publication is None or publication['state']!='published'
                or not publication['required_items_verified']):
            raise MemoryUnavailable('Ownership activation requires the published current reviewed import')
        with importer._locks(account):
            importer._source_current(status['review'],account)
        return publication

    @contextmanager
    def _publication_barrier(self, binding, account, lease):
        importer=MemoryImport(self.configuration,source_directory=binding['source'],installation_lease=lease)
        snapshot=Path(binding['snapshot'])
        document=importer.inspect(snapshot,binding['snapshot_signature'],account=account)
        plan=importer._plan(snapshot,binding['plan_signature'],binding['snapshot_signature'],account)
        importer._source_current(document['review'],account)
        with importer.memory._transaction() as connection:
            importer._registry(connection)
            receipts={row['item']:json.loads(row['receipt']) for row in connection.execute(
                'SELECT item,receipt FROM imports WHERE plan=? AND writer=?',(binding['plan_signature'],account))}
            cache={}
            for item in plan['items']:
                if item['action']!='import':
                    if item['required']:raise MemoryUnavailable('A required import item remains unresolved')
                    continue
                receipt=receipts.get(item['id'])
                reference=receipt.get('reference') if receipt else None
                row=connection.execute('SELECT * FROM records WHERE id=?',(reference['id'],)).fetchone() if reference else None
                if (row is None or row['status']!='active' or row['revision']!=reference['revision']
                        or row['category']!=item['category'] or row['project']!=item['project']
                        or importer.memory._content(row,cache)!=item['content']):
                    raise MemoryUnavailable('An imported reference changes before ownership publication')
            importer._source_current(document['review'],account)
            yield

    @contextmanager
    def _lock(self, account, *, verify=True):
        with installation_lock(self.profile,lease=self.lease) as lease:
            importer=MemoryImport(self.configuration,installation_lease=lease)
            importer._owner(account)
            binding=self._binding(account) if (self.directory/'binding.json').exists() else None
            if binding is None and verify:
                raise MemoryUnavailable('Ownership activation has no reviewed import binding')
            check=(lambda:self._verify(binding,account,lease)) if verify else None
            setup=OwnershipSetup(self.configuration,units=self.units,installation_lease=lease,verify_ready=check,
                publication_barrier=lambda:self._publication_barrier(binding,account,lease))
            with program_lock.exclusive(self.profile,600):
                yield setup

    def prepare(self, snapshot, snapshot_signature, plan_signature, backup, *, account=None, source_directory=None):
        binding={'owner':account,'snapshot':str(Path(snapshot).absolute()),'snapshot_signature':snapshot_signature,
            'plan_signature':plan_signature,'source':str(Path(source_directory).absolute()) if source_directory is not None else None}
        with installation_lock(self.profile,lease=self.lease) as lease:
            self._verify(binding,account,lease)
            self.directory.mkdir(mode=0o700,exist_ok=True);_directory(self.directory,private=True)
            if (self.directory/'binding.json').exists() or (self.directory/'binding.json').is_symlink():
                previous=self._binding(account)
                setup=OwnershipSetup(self.configuration,units=self.units,installation_lease=lease)
                status=setup.status(account=account)
                cancelled=None
                if (self.directory/'cancelled.json').exists():
                    data,_=_read(self.directory/'cancelled.json',private=True);cancelled=json.loads(data)
                cancelled_before_setup=(status['state']=='none' and cancelled=={
                    'binding':hashlib.sha256(_encoded(previous)).hexdigest()})
                if status['state'] not in {'returned','cancelled'} and not cancelled_before_setup:
                    raise MemoryUnavailable('Complete or recover the existing import activation first')
                history=self.directory/'history';history.mkdir(mode=0o700,exist_ok=True)
                _directory(history,private=True)
                publish(history/(uuid4().hex+'.json'),_encoded(previous))
            publish(self.directory/'binding.json',_encoded(binding))
            with program_lock.exclusive(self.profile,600):
                setup=OwnershipSetup(self.configuration,units=self.units,installation_lease=lease,
                    verify_ready=lambda:self._verify(binding,account,lease))
                return setup.prepare(Path(backup).absolute(),account=account)

    def apply(self, signature, *, account=None):
        with self._lock(account) as setup:
            return setup.apply(signature,account=account)

    def recover(self, *, account=None):
        with self._lock(account,verify=False) as setup:
            if setup.status(account=account)['state']=='none':
                if (self.directory/'binding.json').exists():
                    binding=self._binding(account)
                    publish(self.directory/'cancelled.json',_encoded({'binding':hashlib.sha256(_encoded(binding)).hexdigest()}))
                return {'state':'cancelled','application_verified':False,'owner_turn_verified':False}
            return setup.recover(account=account)

    def status(self, *, account=None):
        with self._lock(account,verify=False) as setup:
            return setup.status(account=account)
