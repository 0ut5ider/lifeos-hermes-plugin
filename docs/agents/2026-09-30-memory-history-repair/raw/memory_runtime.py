# ABOUTME: Binds native memory access to admitted Hermes conversations and model routes.
# ABOUTME: Blocks retained context after permission changes, corrections, or forgetting.
from __future__ import annotations

from contextvars import ContextVar
from collections.abc import Mapping as ContentMapping
from dataclasses import asdict, replace
from datetime import datetime, timezone
import hashlib
import json
import os
import stat
import sys
import types
from pathlib import Path
from typing import Any, Mapping

from .memory_access import NativeMemory, MemoryUnavailable
from .memory_context import host_context, route_identity, parse_context, current_host_metadata
from .memory_policy import CATEGORIES, MemoryPolicy, SessionContext
from .memory_service import MemoryConfiguration
from .memory_transaction import publish
from .memory_history import project_request, retained_messages


class MemoryAdmissionError(RuntimeError):
    pass


# Hermes imports the same installed plugin through general and provider namespaces.
_binding = sys.modules.setdefault('_lifeos_memory_admission', types.ModuleType('_lifeos_memory_admission'))
if not hasattr(_binding, 'context'):
    _binding.context = ContextVar('lifeos_memory_admission', default=None)
_BOUND = _binding.context


def _prompt_text(value: Any) -> str:
    if value is None:
        return ''
    if isinstance(value,str):
        return value
    if isinstance(value,(list,tuple)):
        if any(not isinstance(block,ContentMapping) for block in value):
            raise MemoryAdmissionError('Memory admission requires materialized prompt blocks')
        return '\n'.join(block['text'] for block in value
                         if isinstance(block.get('text'),str))
    raise MemoryAdmissionError('Memory admission requires materialized prompt text')


def _request_body(request: dict[str, Any]) -> dict[str, Any]:
    extra = request.get('extra_body')
    if extra is None:
        return request
    if not isinstance(extra,ContentMapping):
        raise MemoryAdmissionError('Memory admission requires a materialized request body')
    # The supported SDK merges these fields after its typed request conversion.
    return {**request,**extra}


def _messages(request: dict[str, Any]):
    for key in ('messages','input'):
        messages = request.get(key)
        if messages is None or isinstance(messages,str) and key == 'input':
            continue
        if not isinstance(messages,(list,tuple)) or any(not isinstance(message,ContentMapping) for message in messages):
            raise MemoryAdmissionError('Memory admission requires materialized request messages')
        yield from messages


def _system_text(request: dict[str, Any]) -> str:
    parts = [_prompt_text(request.get(key)) for key in ('system','instructions')]
    parts.extend(_prompt_text(message.get('content')) for message in _messages(request)
                 if message.get('role') in ('system','developer'))
    return '\n'.join(part for part in parts if part)


def _generated_text(value: Any, depth: int = 0) -> list[str]:
    if depth > 32:
        raise MemoryAdmissionError('Memory admission requires bounded generated input')
    if isinstance(value,str):
        # Tool results and arguments can contain JSON with escaped claim text.
        try:
            decoded = json.loads(value)
        except RecursionError as error:
            raise MemoryAdmissionError('Memory admission requires bounded generated input') from error
        except ValueError:
            return [value]
        return [value,*_generated_text(decoded,depth+1)]
    if isinstance(value,ContentMapping):
        return [text for key,item in value.items() for part in (key,item)
                for text in _generated_text(part,depth+1)]
    if isinstance(value,(list,tuple)):
        return [text for item in value for text in _generated_text(item,depth+1)]
    if value is None or isinstance(value,(bool,int,float)):
        return []
    raise MemoryAdmissionError('Memory admission requires materialized generated input')


class MemoryRuntime:
    def __init__(self, configuration: Path):
        self.configuration = MemoryConfiguration(configuration)
        self.key = str(configuration.absolute())
        self.state_path = configuration.parent / 'lifeos-memory-contexts.json'

    def enabled(self) -> bool:
        if not self.configuration.path.exists() and not self.configuration.path.is_symlink():
            return False
        return self.configuration.load().get('ownership_enabled', False)

    def clear(self) -> None:
        bound = _BOUND.get()
        if bound and bound[0] == self.key:
            _BOUND.set(None)

    def context(self) -> SessionContext | None:
        bound = _BOUND.get()
        return bound[1] if bound and bound[0] == self.key else None

    @staticmethod
    def _scope(configuration: dict[str, Any], context: SessionContext):
        if context.model_route == 'unknown':
            raise MemoryAdmissionError('The actual model route is unknown and cannot receive lasting memory')
        scope = MemoryPolicy(configuration).resolve(context)
        if scope.reason:
            raise MemoryAdmissionError(scope.reason)
        # The installed LifeOS identity prompt is not yet category-filtered.
        if set(scope.read) != CATEGORIES or '*' not in scope.projects:
            raise MemoryAdmissionError('This installed LifeOS prompt requires unrestricted owner recall. Restricted conversation prompts are not yet verified.')
        return scope

    def _rendered_prompt(self, configuration: dict[str, Any], scope, connection) -> str:
        path = self.configuration.path.parent/'SOUL.md'
        try:
            info = path.lstat()
        except FileNotFoundError:
            return 'absent'
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
            raise MemoryAdmissionError('LifeOS lasting memory requires a regular owner prompt file')
        content = path.read_text(encoding='utf-8')
        memory = NativeMemory(Path(configuration['root']))
        # SOUL is a current prompt, not historical learning. Compare its exact
        # claims without excluding unrelated constitution text by snapshot age.
        filtered = memory._filter_history(connection,scope,content,datetime.now(timezone.utc).isoformat())
        if filtered['excluded']:
            raise MemoryAdmissionError('The rendered LifeOS prompt contains a removed or superseded claim. Refresh the LifeOS prompt before starting a conversation.')
        return hashlib.sha256(content.encode()).hexdigest()

    def _stamp(self, configuration: dict[str, Any], context: SessionContext, connection) -> dict[str, Any]:
        scope = self._scope(configuration, replace(context, session_id=''))
        retained = [tuple(row) for row in connection.execute("SELECT id, revision, status FROM records WHERE status != 'active' ORDER BY id")]
        applied = [tuple(row) for row in connection.execute("SELECT id, revision, status FROM proposals WHERE status IN ('accepted','edited','auto-applied') ORDER BY id")]
        rendered = self._rendered_prompt(configuration,scope,connection)
        generation = hashlib.sha256(json.dumps({'retained':retained,'applied':applied,'rendered':rendered}, separators=(',', ':')).encode()).hexdigest()
        return {'scope': scope.signature, 'generation': generation, 'rendered': rendered,
                'context': json.loads(json.dumps(asdict(context)))}

    def _states(self) -> dict[str, Any]:
        if not self.state_path.exists() and not self.state_path.is_symlink():
            return {}
        info = self.state_path.stat()
        if self.state_path.is_symlink() or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise MemoryAdmissionError('Memory conversation state requires private owner permissions')
        states = json.loads(self.state_path.read_text())
        if not isinstance(states, dict):
            raise MemoryAdmissionError('Memory conversation state is invalid')
        return states

    def admit(self, metadata: Mapping[str, str], *, provider: str = '', model: str = '', base_url: str = '',
              api_mode: str = '', is_first_turn: bool = False, session_id: str = '', platform: str = '', **kwargs) -> None:
        if not self.enabled():
            self._refuse_inactive_context(session_id or metadata.get('HERMES_SESSION_ID', ''),
                                          os.environ.get('LIFEOS_MEMORY_CONTEXT', ''))
            _BOUND.set(None)
            return
        _BOUND.set(None)
        configuration = self.configuration.load()
        metadata = dict(metadata)
        metadata['HERMES_SESSION_ID'] = session_id or metadata.get('HERMES_SESSION_ID', '')
        if not metadata.get('HERMES_SESSION_PLATFORM'):
            metadata['HERMES_SESSION_PLATFORM'] = platform
        context = host_context(configuration, metadata, model_route=route_identity(provider, model, base_url, api_mode),
                               hermes_home=str(self.configuration.path.parent))
        self._scope(configuration, context)
        if not context.session_id:
            raise MemoryAdmissionError('Memory needs a host-bound conversation identifier')
        memory = NativeMemory(Path(configuration['root']))
        with memory._transaction() as connection:
            stamp = self._stamp(configuration, context, connection)
            states = self._states()
            previous = states.get(context.session_id)
            if previous is None and not is_first_turn:
                raise MemoryAdmissionError('This conversation has no verified memory context. Start a new conversation.')
            if previous is not None and previous != stamp:
                raise MemoryAdmissionError('Memory permissions or current facts changed. Start a new conversation before continuing.')
            states[context.session_id] = stamp
            publish(self.state_path, (json.dumps(states, sort_keys=True) + '\n').encode())
        _BOUND.set((self.key, context, stamp))

    def _refuse_inactive_context(self, session_id: str, inherited: str) -> None:
        if self.context() is not None or inherited or (session_id and session_id in self._states()):
            raise MemoryAdmissionError('Memory ownership changed for retained context. Start a new conversation.')

    def bind_environment(self, environment: dict[str, str], *, session_id: str = '') -> None:
        inherited = environment.get('LIFEOS_MEMORY_CONTEXT', '')
        environment.pop('LIFEOS_MEMORY_INTERNAL', None)
        environment.pop('LIFEOS_MEMORY_CONTEXT', None)
        environment['LIFEOS_MEMORY_CONFIGURATION'] = self.key
        environment['HERMES_HOME'] = str(self.configuration.path.parent.absolute())
        context = self.context()
        environment['LIFEOS_MEMORY_SESSION'] = session_id or (context.session_id if context is not None else '')
        if not self.enabled():
            self._refuse_inactive_context(session_id, inherited)
            return
        if context is not None:
            environment['LIFEOS_MEMORY_CONTEXT'] = json.dumps(asdict(context))

    def check_call(self, **kwargs) -> None:
        self._check_call(**kwargs)

    def project_call(self, *, request, next_call, **kwargs):
        projected = self._check_call(request=request, project=True, **kwargs)
        return next_call(projected)

    def _check_call(self, *, request: dict[str, Any], provider: str = '', model: str = '', base_url: str = '',
                   api_mode: str = '', session_id: str = '', platform: str = '',
                   metadata: Mapping[str, str] | None = None, project: bool = False, **kwargs):
        bound = _BOUND.get()
        metadata = current_host_metadata() if metadata is None else metadata
        session_id = session_id or (metadata or {}).get('HERMES_SESSION_ID', '') or os.environ.get('LIFEOS_MEMORY_SESSION', '')
        if metadata is not None or platform:
            metadata = dict(metadata or {})
            metadata['HERMES_SESSION_ID'] = session_id
            if not metadata.get('HERMES_SESSION_PLATFORM'):
                metadata['HERMES_SESSION_PLATFORM'] = platform
        states = self._states()
        if not self.enabled():
            if (bound and bound[0] == self.key) or (session_id and session_id in states) or os.environ.get('LIFEOS_MEMORY_CONTEXT'):
                raise MemoryAdmissionError('Memory ownership changed for retained context. Start a new conversation.')
            return request
        configuration = self.configuration.load()
        if bound is None or bound[0] != self.key:
            try:
                if os.environ.get('LIFEOS_MEMORY_CONTEXT'):
                    inherited = parse_context(json.loads(os.environ['LIFEOS_MEMORY_CONTEXT']))
                else:
                    saved = states.get(session_id, {})
                    inherited = parse_context(saved.get('context'))
                    if metadata is None or not metadata.get('HERMES_SESSION_PLATFORM'):
                        raise ValueError('The caller has no trusted host identity metadata')
                    observed = host_context(configuration, metadata, model_route=inherited.model_route,
                                            hermes_home=str(self.configuration.path.parent))
                    if asdict(observed) != asdict(inherited):
                        raise ValueError('The current host metadata differs from admission')
                admitted = states.get(inherited.session_id)
                if not isinstance(admitted, dict):
                    raise ValueError('The inherited conversation has no recorded admission')
                bound = (self.key, inherited, admitted)
            except ValueError as error:
                raise MemoryAdmissionError('This model call has no admitted memory context') from error
        _, context, admitted = bound
        if session_id and session_id != context.session_id:
            raise MemoryAdmissionError('The model call belongs to a different conversation')
        if metadata and metadata.get('HERMES_SESSION_PLATFORM'):
            observed = host_context(configuration, metadata, model_route=context.model_route,
                                    hermes_home=str(self.configuration.path.parent))
            if asdict(observed) != asdict(context):
                raise MemoryAdmissionError('The current author or destination differs from admission')
        body = _request_body(request)
        route = route_identity(provider, body.get('model',model), base_url, api_mode)
        self._scope(configuration, replace(context, model_route=route))
        memory = NativeMemory(Path(configuration['root']))
        with memory._transaction() as connection:
            current = self._stamp(configuration, context, connection)
            saved = states.get(context.session_id)
            can_refresh = (project and saved in (admitted,current)
                           and all(current.get(key)==admitted.get(key) for key in ('scope','context','rendered')))
            if (current != admitted or saved != admitted) and not can_refresh:
                raise MemoryAdmissionError('The model call contains an invalidated memory context. Start a new conversation.')
            scope = self._scope(configuration,context)
            timestamp = datetime.now(timezone.utc).isoformat()
            excluded = lambda content: memory._filter_history(connection,scope,content,timestamp)['excluded']
            if project and ('messages' in body or current != admitted):
                try:
                    projected = project_request(body,excluded)
                except ValueError as error:
                    raise MemoryAdmissionError(str(error)) from error
                request = {**request,'messages':projected['messages']}
                if isinstance(request.get('extra_body'),ContentMapping) and 'messages' in request['extra_body']:
                    request['extra_body'] = {**request['extra_body'],'messages':projected['messages']}
                body = _request_body(request)
            content = _system_text(body)
            if content and memory._filter_history(connection,self._scope(configuration,context),content,
                                                  datetime.now(timezone.utc).isoformat())['excluded']:
                raise MemoryAdmissionError('The model system prompt contains a removed or superseded claim. Refresh the LifeOS prompt and start a new conversation.')
            if kwargs.get('aux_task') == 'compression':
                content = '\n'.join(text for key in ('messages','input')
                                    for text in _generated_text(body.get(key)))
                if content and memory._filter_history(connection,self._scope(configuration,context),content,
                                                      datetime.now(timezone.utc).isoformat())['excluded']:
                    raise MemoryAdmissionError('The compression prompt contains a removed or superseded claim. Rebuild the conversation before compressing it.')
            # Retained user turns and generated messages must not recreate a
            # removed fact. The current explicit user quote remains permitted.
            messages = list(_messages(body))
            content = '\n'.join(text for _,message in retained_messages(messages) for text in _generated_text(message))
            if content and excluded(content):
                raise MemoryAdmissionError('The model history contains a removed or superseded claim. Rebuild the conversation before continuing.')
            if project and current != admitted:
                states[context.session_id] = current
                publish(self.state_path,(json.dumps(states,sort_keys=True)+'\n').encode())
                bound = (self.key,context,current)
        _BOUND.set(bound)
        return request
