# ABOUTME: Reports native memory health and exposes authenticated owner review controls.
# ABOUTME: Manages optional client grants without claiming that unfinished ownership gates have passed.
from __future__ import annotations

from pathlib import Path
import sqlite3
import subprocess
from typing import Any

from .memory_access import NativeMemory, MemoryUnavailable
from .memory_policy import CATEGORIES, MemoryScope
from .memory_service import MemoryConfiguration, MemoryService
from .memory_sharing import MemorySharing


REMAINING_GATES = {
    'native_proposal_policy': 'Native proposals, approval, and retained source coverage',
    'restricted_prompts': 'Restricted audiences, scheduled calls, and rendered LifeOS identity context',
    'session_lifecycle': 'Child agents, compression, and resumed conversations',
    'ownership_transaction': 'Fresh setup, backup, restore, update, and ownership rollback',
    'release_review': 'Complete release tests and independent review',
}


class MemoryPreferences:
    def __init__(self, configuration: Path, installed_root: Path, authorized_keys: Path,
                 interpreter: Path, program: Path):
        self.configuration = MemoryConfiguration(configuration)
        self.root = installed_root.absolute()
        self.connections = MemorySharing(configuration, authorized_keys, interpreter, program, installed_root=self.root)

    def _configuration(self):
        config = self.configuration.load()
        if Path(config['root']).absolute() != self.root:
            raise MemoryUnavailable('Memory configuration belongs to a different LifeOS installation')
        return config

    def status(self) -> dict[str, Any]:
        result = {'state':'not_configured', 'ownership_enabled':False, 'sharing_enabled':False,
                  'activation_ready':False, 'remaining_gates':REMAINING_GATES,
                  'automatic_review':'Native LifeOS hooks', 'proposal_review_available':False,
                  'native_health':'not_checked', 'active_facts':None, 'connections':[]}
        if not self.configuration.path.exists() and not self.configuration.path.is_symlink():
            return result
        try:
            config = self._configuration()
            result.update(state='configured' if config.get('ownership_enabled', False) else 'prepared',
                          ownership_enabled=config.get('ownership_enabled', False),
                          sharing_enabled=config.get('sharing_enabled', False),
                          connections=[dict(client=identifier, **grant) for identifier, grant in config.get('clients', {}).items()])
            memory = NativeMemory(self.root)
            with memory._transaction() as connection:
                result['active_facts'] = connection.execute("SELECT COUNT(*) FROM records WHERE status='active'").fetchone()[0]
            memory._native('rank', query='memory health', corpus=[], limit=1)
            result['native_health'] = 'ok'
            if (self.root / 'LIFEOS/PULSE/lib/memory-proposals.ts').is_file():
                result['proposal_review_available'] = memory._native('proposal_capabilities').get('available') is True
        except (ValueError, OSError, RuntimeError, sqlite3.Error, subprocess.TimeoutExpired) as error:
            result.update(state='unavailable', native_health='unavailable', message=str(error))
        return result

    @staticmethod
    def _owner_scope(config: dict[str, Any]) -> MemoryScope:
        return MemoryScope(config['principal'], 'dashboard:owner', tuple(sorted(CATEGORIES)),
                           tuple(sorted(CATEGORIES)), ('*',), 'dashboard:owner', proposals=('review','approve'))

    def review(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        config = self._configuration()
        return MemoryService(self.configuration)._call(config, self._owner_scope(config), name, arguments)

    def pulse_snapshot(self, view: str, *, account: str | None = None):
        from .memory_pulse import snapshot
        config = self._configuration()
        if account is not None and (not isinstance(account, str)
                or config.get('accounts', {}).get(account) != config['principal']):
            raise PermissionError('This dashboard account has no installation owner binding')
        return snapshot(NativeMemory(self.root), self._owner_scope(config), view)

    def preview_adoption(self) -> dict[str, Any]:
        config = self._configuration()
        return NativeMemory(self.root).preview_adoption(self._owner_scope(config))

    def adopt(self, request: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(request,dict) or set(request) != {'signature','projects','request_id'}:
            raise ValueError('Provide the reviewed source preview, project assignments, and request identifier')
        config = self._configuration()
        return NativeMemory(self.root).adopt(self._owner_scope(config),request['signature'],
                                            request['projects'],request['request_id'])

    def sharing(self, enabled: bool) -> dict[str, Any]:
        if type(enabled) is not bool:
            raise ValueError('Choose whether memory sharing is enabled')
        self._configuration()
        def change(config):
            if Path(config['root']).absolute() != self.root:
                raise MemoryUnavailable('Memory configuration belongs to a different LifeOS installation')
            config['sharing_enabled'] = enabled
        self.configuration.update(change)
        return {'sharing_enabled':enabled, 'records_deleted':False}

    def enroll(self, request: dict[str, Any]) -> dict[str, Any]:
        required = {'client','public_key','projects','model_route'}
        if not isinstance(request, dict) or not required <= set(request) or set(request)-required-{'read','write_project'}:
            raise ValueError('Provide a connection name, public key, projects, and declared model route')
        self._configuration()
        return self.connections.enroll(request['client'],request['public_key'],projects=request['projects'],
                                       model_route=request['model_route'],read=request.get('read'),
                                       write_project=request.get('write_project',False))

    def revoke(self, identifier: str) -> dict[str, Any]:
        self._configuration()
        return self.connections.revoke(identifier)
