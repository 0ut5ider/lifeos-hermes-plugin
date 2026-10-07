# ABOUTME: Coordinates reviewed profile backup, service draining, and ownership configuration changes.
# ABOUTME: Recovers interrupted configuration operations without restoring later native data.
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import re

from .installation_lock import installation_lock
from .memory_access import MemoryUnavailable
from .memory_administration import _connector
from .memory_backup import _directory, _read
from .memory_ownership import OwnershipTransaction
from .memory_transaction import publish
from .profile_backup import create, inspect
from .profile_services import ProfileServices


STATES = {'preparing', 'ready', 'applying', 'configured', 'returning', 'returned', 'cancelled'}


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def _signature(value):
    return isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value) is not None


class OwnershipSetup:
    def __init__(self, configuration, *, units=None):
        self.configuration = configuration
        self.profile = configuration.path.parent.absolute()
        if configuration.path.absolute() != self.profile / 'lifeos-memory.json':
            raise MemoryUnavailable('Ownership setup requires the fixed profile configuration')
        selected = configuration.load()
        self.installed = Path(selected['root']).absolute()
        self.physical_root = self.installed.resolve(strict=True)
        self.principal = selected['principal']
        self.units = ProfileServices(self.profile, self.installed, units=units).units
        self.state = self.profile / '.lifeos-ownership-setup'
        self.journal = self.state / 'operation.json'

    def _owner(self, account):
        if not isinstance(account, str) or not account.startswith('dashboard:'):
            raise PermissionError('An authenticated installation owner must review ownership setup')
        selected = self.configuration.load()
        self.configuration.check_owner(selected, account)
        if (selected['root'] != str(self.installed) or selected['principal'] != self.principal
                or self.installed.resolve() != self.physical_root):
            raise MemoryUnavailable('The selected ownership installation changes during the operation')
        return selected

    @contextmanager
    def _lock(self, account):
        with installation_lock(self.profile) as lease:
            self._owner(account)
            self.state.mkdir(mode=0o700, exist_ok=True)
            _directory(self.state, private=True)
            services = ProfileServices(self.profile, self.installed, units=self.units, installation_lease=lease)
            ownership = OwnershipTransaction(self.configuration, installation_lease=lease,
                verify_writers=services.verify_stopped)
            yield lease, services, ownership

    def _publish(self, document):
        publish(self.journal, (json.dumps(document, sort_keys=True, indent=2) + '\n').encode())

    def _load(self):
        if not self.journal.exists() and not self.journal.is_symlink():
            return None
        data, _ = _read(self.journal, private=True)
        try:
            document = json.loads(data)
        except (ValueError, UnicodeError, RecursionError) as error:
            raise MemoryUnavailable('The ownership setup journal has invalid content') from error
        fields = {'version', 'profile', 'installed', 'installed_physical', 'principal', 'units',
            'state', 'service_signature', 'plan'}
        if (not isinstance(document, dict) or set(document) != fields
                or type(document['version']) is not int or document['version'] != 1
                or document['profile'] != str(self.profile) or document['installed'] != str(self.installed)
                or document['installed_physical'] != str(self.physical_root)
                or document['principal'] != self.principal or document['units'] != self.units
                or not isinstance(document['state'], str) or document['state'] not in STATES
                or not _signature(document['service_signature'])):
            raise MemoryUnavailable('The ownership setup journal has invalid installation bindings')
        plan = document['plan']
        if plan is None:
            if document['state'] not in {'preparing', 'cancelled'}:
                raise MemoryUnavailable('The ownership setup journal has no reviewed plan')
        elif (not isinstance(plan, dict)
                or set(plan) != {'backup', 'backup_signature', 'ownership_signature', 'signature'}
                or not isinstance(plan['backup'], str) or not Path(plan['backup']).is_absolute()
                or any(not _signature(plan[key]) for key in ('backup_signature', 'ownership_signature', 'signature'))
                or plan['signature'] != self._plan_signature(document, plan)):
            raise MemoryUnavailable('The ownership setup journal has an invalid reviewed plan')
        return document

    @staticmethod
    def _plan_signature(document, plan):
        binding = {key: value for key, value in document.items() if key not in {'state', 'plan'}}
        binding['plan'] = {key: value for key, value in plan.items() if key != 'signature'}
        return _digest(binding)

    @staticmethod
    def _receipt(document):
        return {'state': document['state'], 'signature': document['plan']['signature'] if document['plan'] else None,
            'backup': document['plan']['backup'] if document['plan'] else None,
            'application_verified': False, 'owner_turn_verified': False}

    def prepare(self, destination, *, account=None):
        with self._lock(account) as (lease, services, ownership):
            previous = self._load()
            if previous is not None and previous['state'] not in {'returned', 'cancelled'}:
                raise MemoryUnavailable('Recover the existing ownership setup before another review')
            selected = self._owner(account)
            if selected.get('ownership_enabled', False) or selected.get('sharing_enabled', False):
                raise MemoryUnavailable('Fresh ownership setup requires ownership and sharing to be disabled')
            if ownership.status(account=account)['state'] not in {'none', 'rolled_back'}:
                raise MemoryUnavailable('Recover the existing ownership configuration before setup')
            _connector(self.configuration, selected)
            review = services.preview()
            document = {'version': 1, 'profile': str(self.profile), 'installed': str(self.installed),
                'installed_physical': str(self.physical_root), 'principal': self.principal,
                'units': self.units, 'state': 'preparing', 'service_signature': review['signature'], 'plan': None}
            self._publish(document)
            services.drain(signature=review['signature'])
            services.verify_stopped()
            snapshot = create(self.configuration, destination, account=account, installation_lease=lease)
            services.verify_stopped()
            preview = ownership.preview(Path(snapshot['snapshot']), snapshot['signature'], account=account)
            plan = {'backup': snapshot['snapshot'], 'backup_signature': snapshot['signature'],
                'ownership_signature': preview['signature']}
            plan['signature'] = self._plan_signature(document, plan)
            document['plan'] = plan
            self._publish(document)
            self._owner(account)
            services.resume()
            document['state'] = 'ready'
            self._publish(document)
            return self._receipt(document)

    def apply(self, signature, *, account=None):
        with self._lock(account) as (_, services, ownership):
            document = self._load()
            if document is None or document['state'] != 'ready':
                raise MemoryUnavailable('Ownership setup requires a completed backup review')
            plan = document['plan']
            if not _signature(signature) or signature != plan['signature']:
                raise MemoryUnavailable('Ownership setup requires the exact reviewed setup signature')
            preview = ownership.preview(Path(plan['backup']), plan['backup_signature'], account=account)
            if preview['signature'] != plan['ownership_signature']:
                raise MemoryUnavailable('The reviewed ownership configuration changes before setup')
            if services.preview()['signature'] != document['service_signature']:
                raise MemoryUnavailable('The reviewed profile service state changes before setup')
            document['state'] = 'applying'
            self._publish(document)
            services.drain(signature=document['service_signature'])
            services.verify_stopped()
            ownership.apply(Path(plan['backup']), plan['backup_signature'], plan['ownership_signature'], account=account)
            services.verify_stopped()
            self._owner(account)
            services.resume()
            document['state'] = 'configured'
            self._publish(document)
            return self._receipt(document)

    def recover(self, *, account=None):
        with self._lock(account) as (_, services, ownership):
            document = self._load()
            if document is None:
                raise MemoryUnavailable('There is no ownership setup to recover')
            if document['state'] in {'returned', 'cancelled'}:
                return self._receipt(document)
            if document['state'] in {'preparing', 'ready'}:
                if services.status()['state'] not in {'none', 'active'}:
                    self._owner(account)
                    services.resume()
                document['state'] = 'cancelled'
            else:
                plan = document['plan']
                inspect(self.configuration, Path(plan['backup']), plan['backup_signature'], account=account)
                status = ownership.status(account=account)
                # A rollback that already completed for this setup must not run again.
                rollback_required = status['state'] not in {'none', 'rolled_back'}
                if status['state'] == 'none' or (status['state'] == 'rolled_back'
                        and status['signature'] != plan['ownership_signature']):
                    preview = ownership.preview(Path(plan['backup']), plan['backup_signature'], account=account)
                    if preview['signature'] != plan['ownership_signature']:
                        raise MemoryUnavailable('The ownership configuration changes before recovery')
                    rollback_required = False
                elif status['signature'] != plan['ownership_signature']:
                    raise MemoryUnavailable('The ownership configuration journal belongs to another setup')
                document['state'] = 'returning'
                self._publish(document)
                services.quiesce()
                services.verify_stopped()
                if rollback_required:
                    ownership.rollback(account=account)
                services.verify_stopped()
                self._owner(account)
                services.resume()
                document['state'] = 'returned'
            self._publish(document)
            return self._receipt(document)

    def status(self, *, account=None):
        with self._lock(account):
            document = self._load()
            if document is None:
                return {'state': 'none', 'recovery_required': False,
                    'application_verified': False, 'owner_turn_verified': False}
            return {**self._receipt(document),
                'recovery_required': document['state'] in {'preparing', 'applying', 'returning'}}
