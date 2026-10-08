# ABOUTME: Reports native memory health and exposes authenticated owner review controls.
# ABOUTME: Manages optional client grants without claiming that unfinished ownership gates have passed.
from __future__ import annotations

from dataclasses import replace
import hashlib
import os
from pathlib import Path
import sqlite3
import stat
import subprocess
import sys
import types
from typing import Any

from .memory_access import NativeMemory, MemoryUnavailable
from .memory_policy import CATEGORIES, MemoryPolicy, MemoryScope
from .memory_service import MemoryConfiguration, MemoryService


REMAINING_GATES = {
    'native_proposal_policy': 'Native proposals, approval, and retained source coverage',
    'restricted_prompts': 'Restricted audiences, scheduled calls, and rendered LifeOS identity context',
    'session_lifecycle': 'Child agents, compression, and resumed conversations',
    'ownership_transaction': 'Fresh setup, backup, restore, update, and ownership rollback',
    'release_review': 'Complete release tests and independent review',
}


SHARING_COMPONENT_SHA256 = '677cc5909520029dba91009161d615f5f699286f8d2b96f9e80cbd9a28e70515'


def load_sharing_component(directory: Path):
    directory = Path(directory).absolute()
    source = directory / 'memory_sharing.py'
    try:
        parent, folder = directory.parent.stat(), directory.lstat()
        descriptor = os.open(source, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    except FileNotFoundError as error:
        raise MemoryUnavailable('SSH memory connections require the optional sharing component') from error
    except OSError as error:
        raise MemoryUnavailable('The sharing component needs physical owner files without shared write access') from error
    try:
        with os.fdopen(descriptor, 'rb') as stream:
            program = os.fstat(stream.fileno())
            data = stream.read()
    except OSError as error:
        raise MemoryUnavailable('The sharing component needs physical owner files without shared write access') from error
    if (not stat.S_ISDIR(folder.st_mode) or not stat.S_ISREG(program.st_mode)
            or any(info.st_uid != os.getuid() or info.st_mode & 0o022 for info in (parent, folder, program))):
        raise MemoryUnavailable('The sharing component needs physical owner files without shared write access')
    if hashlib.sha256(data).hexdigest() != SHARING_COMPONENT_SHA256:
        raise MemoryUnavailable('The installed sharing component differs from the reviewed release')
    # The verified bytes run directly. The standard source loader would read the file again
    # and would prefer an unverified bytecode file beside the source.
    name = __package__ + '.memory_sharing'
    module = types.ModuleType(name)
    module.__package__, module.__file__ = __package__, str(source)
    sys.modules[name] = module
    try:
        exec(compile(data, str(source), 'exec', dont_inherit=True), module.__dict__)
    except BaseException:
        sys.modules.pop(name, None)
        raise
    return module


class MemoryPreferences:
    def __init__(self, configuration: Path, installed_root: Path, interpreter: Path, program: Path,
                 *, sharing_component: Path | None = None, sharing_options: dict[str, Any] | None = None):
        self.configuration = MemoryConfiguration(configuration)
        self.root = installed_root.absolute()
        self.sharing_component = Path(sharing_component or Path(configuration).parent / 'lifeos-memory-sharing')
        self._sharing = (Path(configuration), interpreter, program, dict(sharing_options or {}))
        if any(not path.is_absolute() for path in (Path(configuration), interpreter, program)):
            raise ValueError('Memory connection paths must be absolute')

    @property
    def connections(self):
        configuration, interpreter, program, options = self._sharing
        return load_sharing_component(self.sharing_component).MemorySharing(
            configuration, interpreter, program, installed_root=self.root, **options)

    def connection_enrollment_available(self) -> bool:
        try:
            load_sharing_component(self.sharing_component)
        except MemoryUnavailable:
            return False
        return True

    def _configuration(self, *, account: str | None = None):
        config = self.configuration.load()
        if Path(config['root']).absolute() != self.root:
            raise MemoryUnavailable('Memory configuration belongs to a different LifeOS installation')
        self.configuration.check_owner(config, account)
        return config

    def status(self, *, account: str | None = None) -> dict[str, Any]:
        result = {'state':'not_configured', 'ownership_enabled':False, 'sharing_enabled':False,
                  'activation_ready':False, 'remaining_gates':REMAINING_GATES,
                  'automatic_review':'Native LifeOS hooks', 'proposal_review_available':False,
                  'native_health':'not_checked', 'active_facts':None, 'connections':[],
                  'connection_enrollment_available':self.connection_enrollment_available()}
        if not self.configuration.path.exists() and not self.configuration.path.is_symlink():
            return result
        try:
            config = self._configuration(account=account)
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
        except PermissionError:
            raise
        except (ValueError, OSError, RuntimeError, sqlite3.Error, subprocess.TimeoutExpired) as error:
            result.update(state='unavailable', native_health='unavailable', message=str(error))
        return result

    def claim(self, *, account: str) -> dict[str, Any]:
        """Bind an unconfigured installation to the authenticated dashboard account."""
        if not isinstance(account, str) or not account.startswith('dashboard:'):
            raise PermissionError('An authenticated dashboard account must claim the installation')
        if not (self.root / 'LIFEOS/VERSION').is_file():
            raise MemoryUnavailable('Install LifeOS before claiming the installation')
        config = {'version': 1, 'root': str(self.root), 'principal': 'owner', 'ownership_enabled': False,
                  'sharing_enabled': False, 'accounts': {account: 'owner'}, 'destinations': {}, 'clients': {}}
        self.configuration.validate(config)
        with self.configuration._lock():
            if self.configuration.path.exists() or self.configuration.path.is_symlink():
                raise MemoryUnavailable('This installation already has an owner')
            self.configuration._publish(config)
        return self.status(account=account)

    @staticmethod
    def _owner_scope(config: dict[str, Any]) -> MemoryScope:
        return MemoryScope(config['principal'], 'dashboard:owner', tuple(sorted(CATEGORIES)),
                           tuple(sorted(CATEGORIES)), ('*',), 'dashboard:owner', proposals=('review','approve'))

    def review(self, name: str, arguments: dict[str, Any], *, account: str | None = None) -> dict[str, Any]:
        config = self._configuration(account=account)
        return MemoryService(self.configuration)._call(config, self._owner_scope(config), name, arguments)

    def _response(self, config, result, *, account):
        from .memory_http import installation_binding
        if self._configuration(account=account) != config:
            raise MemoryUnavailable('Current memory authority changes before the dashboard response')
        return result, installation_binding(config, self.configuration.path)

    def pulse_snapshot(self, view: str, *, account: str | None = None):
        return self.pulse_response(view,account=account)[0]

    def pulse_response(self, view: str, *, account: str | None = None):
        from .memory_pulse import snapshot
        config = self._configuration(account=account)
        from .memory_freshness import HTTP_VIEWS
        if isinstance(view, str) and view in HTTP_VIEWS:
            from .memory_freshness import view as freshness_view

            def check_current():
                if self._configuration(account=account) != config:
                    raise MemoryUnavailable('The memory configuration changed during freshness rendering')

            return self._response(config, freshness_view(NativeMemory(self.root), self._owner_scope(config), view,
                                   check_current=check_current), account=account)
        if view == 'graph':
            from .memory_graph import view as graph_view

            def check_current():
                if self._configuration(account=account) != config:
                    raise MemoryUnavailable('The memory configuration changed during graph rendering')

            return self._response(config, graph_view(NativeMemory(self.root), self._owner_scope(config),
                                                    check_current=check_current), account=account)
        return self._response(config, snapshot(NativeMemory(self.root), self._owner_scope(config), view),
                              account=account)

    def preview_prompt(self, *, keep_output_format: bool = False, account: str | None = None):
        from .memory_prompt import preview
        config = self._configuration(account=account)
        return preview(NativeMemory(self.root), self._owner_scope(config), self.configuration.path.parent,
                       keep_output_format=keep_output_format)

    def authorize_mount(self, *, account=None, ttl=600, binding=None):
        from .memory_administration import issue
        self._configuration(account=account)
        return issue(self.configuration, account, ttl=ttl, binding=binding)

    def revoke_mount(self, authorization):
        from .memory_administration import revoke
        revoke(self.configuration, authorization)

    def publish_prompt(self, request: dict[str, Any], *, account: str | None = None):
        from .memory_prompt import publish_prompt
        if not isinstance(request, dict) or set(request) != {'signature', 'previous_digest', 'keep_output_format'}:
            raise ValueError('Provide the reviewed prompt snapshot, installed prompt digest, and output format choice')
        config = self._configuration(account=account)
        def check_current():
            if self._configuration(account=account) != config:
                raise MemoryUnavailable('The memory configuration changed during prompt publication')
        return publish_prompt(NativeMemory(self.root), self._owner_scope(config), self.configuration.path.parent,
                              **request, check_current=check_current)

    def preview_adoption(self, *, account: str | None = None) -> dict[str, Any]:
        config = self._configuration(account=account)
        return NativeMemory(self.root).preview_adoption(self._owner_scope(config))

    def preview_import(self, *, account=None):
        from .memory_import import MemoryImport
        self._configuration(account=account)
        return MemoryImport(self.configuration).preview(account=account)

    def prepare_fresh(self, candidate, *, principal_name, assistant_name, account=None):
        from .fresh_store import FreshStore
        from .install_source import IncompatibleLifeOS
        self._configuration(account=account)
        try:
            return FreshStore(self.configuration).prepare(candidate,principal_name=principal_name,
                assistant_name=assistant_name,account=account)
        except IncompatibleLifeOS as error:
            raise MemoryUnavailable('Fresh store preparation requires a verified native candidate') from error

    def fresh_home(self, identifier, *, account=None):
        from .fresh_store import FreshStore
        self._configuration(account=account)
        return FreshStore(self.configuration).review_home(identifier, account=account)

    def remove_fresh(self, identifier, *, account=None):
        from .fresh_store import FreshStore
        self._configuration(account=account)
        return FreshStore(self.configuration).remove(identifier, account=account)

    def fresh_status(self, *, account=None):
        from .fresh_store import FreshStore
        self._configuration(account=account)
        return FreshStore(self.configuration).status(account=account)

    def prepare_import(self, request, *, account=None):
        import hashlib
        from uuid import uuid4
        from .memory_import import MemoryImport
        self._configuration(account=account)
        if not isinstance(request, dict) or set(request) != {'signature'}:
            raise ValueError('Provide the reviewed Hermes import signature')
        profile = self.configuration.path.parent.absolute()
        identity = hashlib.sha256(str(profile).encode()).hexdigest()[:24]
        from .lifeos_installation import state_home
        destination = state_home(profile) / '.local/state/lifeos-hook-bridge/imports' / identity / uuid4().hex
        return MemoryImport(self.configuration).prepare(destination, request['signature'], account=account)

    def preview_sources(self, paths: list[str], *, account: str | None = None):
        from .memory_source_review import preview
        config = self._configuration(account=account)
        scope = replace(self._owner_scope(config), signature=MemoryPolicy(config).revision)
        return preview(NativeMemory(self.root), scope, paths)

    def approve_sources(self, request: dict[str, Any], *, account: str | None = None):
        from .memory_source_review import approve
        config = self._configuration(account=account)
        if not isinstance(request, dict) or set(request) != {'paths', 'signature'}:
            raise ValueError('Provide the reviewed installed paths and source signature')
        def check_current():
            if self._configuration(account=account) != config:
                raise MemoryUnavailable('The memory configuration changed during source review')
        scope = replace(self._owner_scope(config), signature=MemoryPolicy(config).revision)
        return approve(NativeMemory(self.root), scope, **request, check_current=check_current)

    def review_hypothesis(self, target, note, request_id, *, account=None):
        from .memory_hypothesis_review import review
        config = self._configuration(account=account)
        def check_current():
            if self._configuration(account=account) != config:
                raise MemoryUnavailable('The memory configuration changes during hypothesis review')
        return self._response(config, review(NativeMemory(self.root), self._owner_scope(config),
            target=target, note=note, request_id=request_id, check_current=check_current), account=account)

    def review_upgrade(self, target, note, request_id, *, account=None):
        from .memory_upgrade_queue import review
        config = self._configuration(account=account)
        def check_current():
            if self._configuration(account=account) != config:
                raise MemoryUnavailable('The memory configuration changes during upgrade review')
        return self._response(config, review(NativeMemory(self.root), self._owner_scope(config),
            target=target, note=note, request_id=request_id, check_current=check_current), account=account)

    def tab_freshness_response(self, target, *, account=None):
        from .memory_tab_freshness import view
        config = self._configuration(account=account)
        def check_current():
            if self._configuration(account=account) != config:
                raise MemoryUnavailable('The memory configuration changes during tab freshness rendering')
        return self._response(config, view(NativeMemory(self.root), self._owner_scope(config), target,
            check_current=check_current), account=account)

    def upgrade_response(self, target, *, account=None):
        from .memory_upgrade_queue import view
        config = self._configuration(account=account)
        def check_current():
            if self._configuration(account=account) != config:
                raise MemoryUnavailable('The memory configuration changes during upgrade rendering')
        return self._response(config, view(NativeMemory(self.root), self._owner_scope(config), target,
            check_current=check_current), account=account)

    def hypothesis_response(self, target: str, *, account: str | None = None):
        from .memory_hypothesis_queue import view
        config = self._configuration(account=account)
        def check_current():
            if self._configuration(account=account) != config:
                raise MemoryUnavailable('The memory configuration changes during hypothesis rendering')
        return self._response(config, view(NativeMemory(self.root), self._owner_scope(config), target,
                                          check_current=check_current), account=account)

    def wiki_response(self, target: str, *, account: str | None = None):
        from .memory_wiki import view
        config = self._configuration(account=account)
        return self._response(config, view(NativeMemory(self.root), self._owner_scope(config), target),
                              account=account)

    def knowledge_response(self, target: str, *, account: str | None = None):
        from .memory_knowledge import view
        config = self._configuration(account=account)
        return self._response(config, view(NativeMemory(self.root), self._owner_scope(config), target),
                              account=account)

    def adopt(self, request: dict[str, Any], *, account: str | None = None) -> dict[str, Any]:
        if not isinstance(request,dict) or set(request) != {'signature','projects','request_id'}:
            raise ValueError('Provide the reviewed source preview, project assignments, and request identifier')
        config = self._configuration(account=account)
        return NativeMemory(self.root).adopt(self._owner_scope(config),request['signature'],
                                            request['projects'],request['request_id'])

    def sharing(self, enabled: bool, *, account: str | None = None) -> dict[str, Any]:
        if type(enabled) is not bool:
            raise ValueError('Choose whether memory sharing is enabled')
        self._configuration(account=account)
        def change(config):
            if Path(config['root']).absolute() != self.root:
                raise MemoryUnavailable('Memory configuration belongs to a different LifeOS installation')
            self.configuration.check_owner(config, account)
            config['sharing_enabled'] = enabled
        self.configuration.update(change)
        return {'sharing_enabled':enabled, 'records_deleted':False}

    def enroll(self, request: dict[str, Any], *, account: str | None = None) -> dict[str, Any]:
        required = {'client','public_key','projects','model_route'}
        if not isinstance(request, dict) or not required <= set(request) or set(request)-required-{'read','write_project'}:
            raise ValueError('Provide a connection name, public key, projects, and declared model route')
        self._configuration(account=account)
        return self.connections.enroll(request['client'],request['public_key'],projects=request['projects'],
                                       model_route=request['model_route'],read=request.get('read'),
                                       write_project=request.get('write_project',False), account=account)

    def revoke(self, identifier: str, *, account: str | None = None) -> dict[str, Any]:
        self._configuration(account=account)
        if self.connection_enrollment_available():
            result = self.connections.revoke(identifier, account=account)
            self.configuration.update(lambda config: config.get('clients', {}).get(identifier, {}).pop(
                'credential_entry_pending', None))
            return result
        def disable(config):
            if Path(config['root']).absolute() != self.root:
                raise MemoryUnavailable('Memory configuration belongs to a different LifeOS installation')
            self.configuration.check_owner(config, account)
            grant = config.get('clients', {}).get(identifier)
            if grant is None:
                raise ValueError('This memory connection does not exist')
            grant['enabled'] = False
            grant['credential_entry_pending'] = True
        self.configuration.update(disable)
        return {'status':'revoked', 'client':identifier, 'records_deleted':False, 'credential_entry_removed':False}
