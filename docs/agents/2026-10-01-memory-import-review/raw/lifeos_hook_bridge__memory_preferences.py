     1	# ABOUTME: Reports native memory health and exposes authenticated owner review controls.
     2	# ABOUTME: Manages optional client grants without claiming that unfinished ownership gates have passed.
     3	from __future__ import annotations
     4	
     5	from pathlib import Path
     6	import sqlite3
     7	import subprocess
     8	from typing import Any
     9	
    10	from .memory_access import NativeMemory, MemoryUnavailable
    11	from .memory_policy import CATEGORIES, MemoryScope
    12	from .memory_service import MemoryConfiguration, MemoryService
    13	from .memory_sharing import MemorySharing
    14	
    15	
    16	REMAINING_GATES = {
    17	    'native_proposal_policy': 'Native proposals, approval, and retained source coverage',
    18	    'restricted_prompts': 'Restricted audiences, scheduled calls, and rendered LifeOS identity context',
    19	    'session_lifecycle': 'Child agents, compression, and resumed conversations',
    20	    'ownership_transaction': 'Fresh setup, backup, restore, update, and ownership rollback',
    21	    'release_review': 'Complete release tests and independent review',
    22	}
    23	
    24	
    25	class MemoryPreferences:
    26	    def __init__(self, configuration: Path, installed_root: Path, authorized_keys: Path,
    27	                 interpreter: Path, program: Path):
    28	        self.configuration = MemoryConfiguration(configuration)
    29	        self.root = installed_root.absolute()
    30	        self.connections = MemorySharing(configuration, authorized_keys, interpreter, program, installed_root=self.root)
    31	
    32	    def _configuration(self, *, account: str | None = None):
    33	        config = self.configuration.load()
    34	        if Path(config['root']).absolute() != self.root:
    35	            raise MemoryUnavailable('Memory configuration belongs to a different LifeOS installation')
    36	        self.configuration.check_owner(config, account)
    37	        return config
    38	
    39	    def status(self, *, account: str | None = None) -> dict[str, Any]:
    40	        result = {'state':'not_configured', 'ownership_enabled':False, 'sharing_enabled':False,
    41	                  'activation_ready':False, 'remaining_gates':REMAINING_GATES,
    42	                  'automatic_review':'Native LifeOS hooks', 'proposal_review_available':False,
    43	                  'native_health':'not_checked', 'active_facts':None, 'connections':[]}
    44	        if not self.configuration.path.exists() and not self.configuration.path.is_symlink():
    45	            return result
    46	        try:
    47	            config = self._configuration(account=account)
    48	            result.update(state='configured' if config.get('ownership_enabled', False) else 'prepared',
    49	                          ownership_enabled=config.get('ownership_enabled', False),
    50	                          sharing_enabled=config.get('sharing_enabled', False),
    51	                          connections=[dict(client=identifier, **grant) for identifier, grant in config.get('clients', {}).items()])
    52	            memory = NativeMemory(self.root)
    53	            with memory._transaction() as connection:
    54	                result['active_facts'] = connection.execute("SELECT COUNT(*) FROM records WHERE status='active'").fetchone()[0]
    55	            memory._native('rank', query='memory health', corpus=[], limit=1)
    56	            result['native_health'] = 'ok'
    57	            if (self.root / 'LIFEOS/PULSE/lib/memory-proposals.ts').is_file():
    58	                result['proposal_review_available'] = memory._native('proposal_capabilities').get('available') is True
    59	        except PermissionError:
    60	            raise
    61	        except (ValueError, OSError, RuntimeError, sqlite3.Error, subprocess.TimeoutExpired) as error:
    62	            result.update(state='unavailable', native_health='unavailable', message=str(error))
    63	        return result
    64	
    65	    @staticmethod
    66	    def _owner_scope(config: dict[str, Any]) -> MemoryScope:
    67	        return MemoryScope(config['principal'], 'dashboard:owner', tuple(sorted(CATEGORIES)),
    68	                           tuple(sorted(CATEGORIES)), ('*',), 'dashboard:owner', proposals=('review','approve'))
    69	
    70	    def review(self, name: str, arguments: dict[str, Any], *, account: str | None = None) -> dict[str, Any]:
    71	        config = self._configuration(account=account)
    72	        return MemoryService(self.configuration)._call(config, self._owner_scope(config), name, arguments)
    73	
    74	    def pulse_snapshot(self, view: str, *, account: str | None = None):
    75	        from .memory_pulse import snapshot
    76	        config = self._configuration(account=account)
    77	        return snapshot(NativeMemory(self.root), self._owner_scope(config), view)
    78	
    79	    def preview_adoption(self, *, account: str | None = None) -> dict[str, Any]:
    80	        config = self._configuration(account=account)
    81	        return NativeMemory(self.root).preview_adoption(self._owner_scope(config))
    82	
    83	    def adopt(self, request: dict[str, Any], *, account: str | None = None) -> dict[str, Any]:
    84	        if not isinstance(request,dict) or set(request) != {'signature','projects','request_id'}:
    85	            raise ValueError('Provide the reviewed source preview, project assignments, and request identifier')
    86	        config = self._configuration(account=account)
    87	        return NativeMemory(self.root).adopt(self._owner_scope(config),request['signature'],
    88	                                            request['projects'],request['request_id'])
    89	
    90	    def sharing(self, enabled: bool, *, account: str | None = None) -> dict[str, Any]:
    91	        if type(enabled) is not bool:
    92	            raise ValueError('Choose whether memory sharing is enabled')
    93	        self._configuration(account=account)
    94	        def change(config):
    95	            if Path(config['root']).absolute() != self.root:
    96	                raise MemoryUnavailable('Memory configuration belongs to a different LifeOS installation')
    97	            self.configuration.check_owner(config, account)
    98	            config['sharing_enabled'] = enabled
    99	        self.configuration.update(change)
   100	        return {'sharing_enabled':enabled, 'records_deleted':False}
   101	
   102	    def enroll(self, request: dict[str, Any], *, account: str | None = None) -> dict[str, Any]:
   103	        required = {'client','public_key','projects','model_route'}
   104	        if not isinstance(request, dict) or not required <= set(request) or set(request)-required-{'read','write_project'}:
   105	            raise ValueError('Provide a connection name, public key, projects, and declared model route')
   106	        self._configuration(account=account)
   107	        return self.connections.enroll(request['client'],request['public_key'],projects=request['projects'],
   108	                                       model_route=request['model_route'],read=request.get('read'),
   109	                                       write_project=request.get('write_project',False), account=account)
   110	
   111	    def revoke(self, identifier: str, *, account: str | None = None) -> dict[str, Any]:
   112	        self._configuration(account=account)
   113	        return self.connections.revoke(identifier, account=account)
