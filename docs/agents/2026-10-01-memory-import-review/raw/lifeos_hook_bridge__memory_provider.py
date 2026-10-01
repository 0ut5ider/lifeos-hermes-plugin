     1	# ABOUTME: Exposes governed native memory tools through the Hermes memory provider API.
     2	# ABOUTME: Leaves automatic recall, review, session history, and skill learning with their owners.
     3	from __future__ import annotations
     4	
     5	import hashlib
     6	import json
     7	from pathlib import Path
     8	from typing import Any
     9	
    10	from agent.memory_provider import MemoryProvider
    11	from hermes_constants import get_hermes_home
    12	
    13	from .memory_runtime import MemoryRuntime, MemoryAdmissionError
    14	from .memory_service import MemoryConfiguration, MemoryService, tool_schemas
    15	
    16	
    17	def configuration_path() -> Path:
    18	    return get_hermes_home() / 'lifeos-memory.json'
    19	
    20	
    21	def current_metadata() -> dict[str, str]:
    22	    from .memory_context import current_host_metadata
    23	    return current_host_metadata() or {}
    24	
    25	
    26	class LifeOSMemoryProvider(MemoryProvider):
    27	    def __init__(self, configuration: Path | None = None):
    28	        self.configuration = MemoryConfiguration(configuration or configuration_path())
    29	        self.runtime = MemoryRuntime(self.configuration.path)
    30	        self.service = MemoryService(self.configuration)
    31	        self.session_id = ''
    32	
    33	    @property
    34	    def name(self) -> str:
    35	        return 'lifeos-hook-bridge'
    36	
    37	    def is_available(self) -> bool:
    38	        try:
    39	            from hermes_cli.middleware import REQUIRED_MIDDLEWARE_API_VERSION
    40	            config = self.configuration.load()
    41	            return (REQUIRED_MIDDLEWARE_API_VERSION == 1 and config.get('ownership_enabled', False)
    42	                    and (Path(config['root']) / 'LIFEOS/TOOLS/lib/MemoryAccess.ts').is_file())
    43	        except (ImportError, ValueError, OSError, RuntimeError):
    44	            return False
    45	
    46	    def unavailable_reason(self) -> str:
    47	        return 'Set up LifeOS lasting memory in the plugin page and verify the required host extension first.'
    48	
    49	    def initialize(self, session_id: str, **kwargs) -> None:
    50	        if kwargs.get('hermes_home') and Path(kwargs['hermes_home']).absolute() != self.configuration.path.parent.absolute():
    51	            raise MemoryAdmissionError('Memory configuration belongs to a different Hermes profile')
    52	        if not self.is_available():
    53	            raise MemoryAdmissionError(self.unavailable_reason())
    54	        self.session_id = session_id
    55	
    56	    def system_prompt_block(self) -> str:
    57	        return ('LifeOS owns lasting memory. Use the lifeos_memory tools for explicit remember, search, correct, and forget requests. '
    58	                'Report the returned status. Forget removes ordinary recall, not retained history or backups.')
    59	
    60	    def get_tool_schemas(self) -> list[dict[str, Any]]:
    61	        return tool_schemas()
    62	
    63	    def handle_tool_call(self, tool_name: str, args: dict[str, Any], **kwargs) -> str:
    64	        context = self.runtime.context()
    65	        if not self.runtime.enabled() or context is None:
    66	            return json.dumps({'status': 'rejected', 'reason': 'Memory needs an admitted current conversation'})
    67	        requested_session = kwargs.get('session_id')
    68	        if requested_session and requested_session != context.session_id:
    69	            return json.dumps({'status': 'rejected', 'reason': 'Memory call belongs to a different conversation'})
    70	        return json.dumps(self.service.call_context(context, tool_name, args))
    71	
    72	    def identity_signature(self) -> dict[str, Any]:
    73	        try:
    74	            config = self.configuration.load()
    75	            return {'configuration': hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()}
    76	        except (ValueError, OSError, RuntimeError):
    77	            return {'configuration': 'unavailable'}
    78	
    79	    def on_session_switch(self, new_session_id: str, **kwargs) -> None:
    80	        self.session_id = new_session_id
    81	        self.runtime.clear()
    82	
    83	    def shutdown(self) -> None:
    84	        self.runtime.clear()
    85	
    86	
    87	def register_provider(ctx) -> MemoryRuntime:
    88	    provider = LifeOSMemoryProvider()
    89	    ctx.register_memory_provider(provider)
    90	    try:
    91	        from hermes_cli.middleware import REQUIRED_MIDDLEWARE_API_VERSION
    92	    except ImportError:
    93	        if provider.runtime.enabled():
    94	            raise MemoryAdmissionError('LifeOS lasting memory needs required model-request checks')
    95	    else:
    96	        if REQUIRED_MIDDLEWARE_API_VERSION == 1:
    97	            ctx.register_middleware('llm_execution', provider.runtime.project_call, required=True)
    98	            ctx.register_middleware('llm_admission', provider.runtime.check_call, required=True)
    99	    return provider.runtime
