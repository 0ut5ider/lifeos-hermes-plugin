# ABOUTME: Exposes governed native memory tools through the Hermes memory provider API.
# ABOUTME: Leaves automatic recall, review, session history, and skill learning with their owners.
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from agent.memory_provider import MemoryProvider
from hermes_constants import get_hermes_home

from .memory_runtime import MemoryRuntime, MemoryAdmissionError
from .memory_service import MemoryConfiguration, MemoryService, tool_schemas


def configuration_path() -> Path:
    return get_hermes_home() / 'lifeos-memory.json'


def current_metadata() -> dict[str, str]:
    from .memory_context import current_host_metadata
    return current_host_metadata() or {}


class LifeOSMemoryProvider(MemoryProvider):
    def __init__(self, configuration: Path | None = None):
        self.configuration = MemoryConfiguration(configuration or configuration_path())
        self.runtime = MemoryRuntime(self.configuration.path)
        self.service = MemoryService(self.configuration)
        self.session_id = ''

    @property
    def name(self) -> str:
        return 'lifeos-hook-bridge'

    def is_available(self) -> bool:
        try:
            from hermes_cli.middleware import REQUIRED_MIDDLEWARE_API_VERSION
            config = self.configuration.load()
            return (REQUIRED_MIDDLEWARE_API_VERSION == 1 and config.get('ownership_enabled', False)
                    and (Path(config['root']) / 'LIFEOS/TOOLS/lib/MemoryAccess.ts').is_file())
        except (ImportError, ValueError, OSError, RuntimeError):
            return False

    def unavailable_reason(self) -> str:
        return ('LifeOS memory ownership cannot be activated in this release. '
                'Experimental ownership profiles also require the tested host extension.')

    def initialize(self, session_id: str, **kwargs) -> None:
        if kwargs.get('hermes_home') and Path(kwargs['hermes_home']).absolute() != self.configuration.path.parent.absolute():
            raise MemoryAdmissionError('Memory configuration belongs to a different Hermes profile')
        if not self.is_available():
            raise MemoryAdmissionError(self.unavailable_reason())
        self.session_id = session_id

    def system_prompt_block(self) -> str:
        return ('LifeOS owns lasting memory. Use the lifeos_memory tools for explicit remember, search, correct, and forget requests. '
                'Report the returned status. Forget removes ordinary recall, not retained history or backups.')

    def get_tool_schemas(self) -> list[dict[str, Any]]:
        return tool_schemas()

    def handle_tool_call(self, tool_name: str, args: dict[str, Any], **kwargs) -> str:
        context = self.runtime.context()
        if not self.runtime.enabled() or context is None:
            return json.dumps({'status': 'rejected', 'reason': 'Memory needs an admitted current conversation'})
        requested_session = kwargs.get('session_id')
        if requested_session and requested_session != context.session_id:
            return json.dumps({'status': 'rejected', 'reason': 'Memory call belongs to a different conversation'})
        return json.dumps(self.service.call_context(context, tool_name, args))

    def identity_signature(self) -> dict[str, Any]:
        try:
            config = self.configuration.load()
            return {'configuration': hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()}
        except (ValueError, OSError, RuntimeError):
            return {'configuration': 'unavailable'}

    def on_session_switch(self, new_session_id: str, **kwargs) -> None:
        if kwargs.get('reason') == 'compression' and not kwargs.get('reset'):
            parent = kwargs.get('parent_session_id')
            try:
                if not parent or parent != self.session_id:
                    raise MemoryAdmissionError('Compression belongs to a different provider conversation')
                self.runtime.rotate_session(new_session_id,parent)
            except Exception:
                self.runtime.clear()
                raise
            self.session_id = new_session_id
            return
        self.session_id = new_session_id
        self.runtime.clear()

    def shutdown(self) -> None:
        self.runtime.clear()


def register_provider(ctx) -> MemoryRuntime:
    provider = LifeOSMemoryProvider()
    ctx.register_memory_provider(provider)
    try:
        from hermes_cli.middleware import REQUIRED_MIDDLEWARE_API_VERSION
    except ImportError:
        if provider.runtime.enabled():
            raise MemoryAdmissionError('LifeOS lasting memory needs required model-request checks')
    else:
        if REQUIRED_MIDDLEWARE_API_VERSION == 1:
            ctx.register_middleware('llm_execution', provider.runtime.project_call, required=True)
            ctx.register_middleware('llm_admission', provider.runtime.check_call, required=True)
        else:
            try:
                enabled = provider.runtime.enabled()
            except (ValueError, OSError, RuntimeError) as error:
                raise MemoryAdmissionError(
                    'LifeOS cannot confirm that lasting memory is disabled on this Hermes version') from error
            if enabled:
                raise MemoryAdmissionError('LifeOS lasting memory needs required model-request checks')
    return provider.runtime
