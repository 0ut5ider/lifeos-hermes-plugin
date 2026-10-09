# ABOUTME: Gives Hermes and authenticated clients the same native memory tool operations.
# ABOUTME: Loads private server-owned identity grants for each request and reports truthful results.

from __future__ import annotations

import json
from contextlib import contextmanager
import fcntl
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import stat
from typing import Any

from .memory_access import HOT_FILES, NativeMemory, MemoryUnavailable
from .memory_policy import CATEGORIES, MemoryPolicy, MemoryScope, SessionContext
from .memory_transaction import publish


REFERENCE = {"type": "object", "properties": {"id": {"type": "string"}, "revision": {"type": "integer", "minimum": 1}},
             "required": ["id", "revision"], "additionalProperties": False}
FIELDS = {
    "query": {"type": "string", "minLength": 1, "maxLength": 4096},
    "limit": {"type": "integer", "minimum": 1, "maximum": 100},
    "reference": REFERENCE,
    "decision": {"type":"string", "enum":["accept", "reject", "edit", "applied_elsewhere"]},
    "proposal": {"type":"object", "properties":{
        "type":{"type":"string", "enum":["proposal"]},
        "target_kind":{"type":"string", "maxLength":64}, "target_file":{"type":"string", "minLength":1, "maxLength":4096},
        "edit":{"type":"string", "minLength":1, "maxLength":65536},
        "confidence":{"type":"number", "minimum":0, "maximum":1},
        "rationale":{"type":"string", "minLength":1, "maxLength":8192},
        "source_session":{"type":"string", "maxLength":256},
        "observed_across_sessions":{"type":"integer", "minimum":1, "maximum":1000000}},
        "required":["type", "target_file", "edit", "confidence", "rationale"], "additionalProperties":False},
    "category": {"type": "string", "enum": sorted(CATEGORIES)},
    "content": {"type": "string", "minLength": 1, "maxLength": 65536},
    "note": {"type":"string", "minLength":1, "maxLength":65536},
    "title": {"type": "string", "maxLength": 1024}, "project": {"type": "string", "maxLength": 256},
    "request_id": {"type": "string", "minLength": 1, "maxLength": 256},
}
TOOLS = {
    "lifeos_memory_propose": ("Submit a native LifeOS change for review. Pending and diverted changes are not applied edits.",
                              ("proposal", "request_id"), ()),
    "lifeos_memory_proposals": ("List permitted pending native LifeOS changes and their references.", (), ()),
    "lifeos_memory_decide_proposal": ("Apply or reject a referenced proposal with a separate approval grant.",
                                     ("reference", "decision", "request_id"), ("content", "note")),
    "lifeos_memory_status": ("Check lasting memory access and availability.", (), ()),
    "lifeos_memory_search": ("Find permitted current LifeOS facts and their references.", ("query",), ("limit",)),
    "lifeos_memory_get": ("Read one current fact by its returned reference.", ("reference",), ()),
    "lifeos_memory_remember": ("Save a fact. Report the returned status; reuse request_id only for an identical retry.",
                               ("category", "content", "title", "project", "request_id"), ()),
    "lifeos_memory_correct": ("Correct a referenced current fact. Superseded facts leave ordinary recall.",
                              ("reference", "content", "request_id"), ()),
    "lifeos_memory_forget": ("Exclude a fact from ordinary recall. Retained history and backups are not erased.",
                             ("reference", "request_id"), ()),
}


def tool_schemas() -> list[dict[str, Any]]:
    return [{"name": name, "description": description,
             "parameters": {"type": "object", "properties": {key: FIELDS[key] for key in (*required, *optional)},
                            "required": list(required), "additionalProperties": False}}
            for name, (description, required, optional) in TOOLS.items()]


def _validate_arguments(name: str, arguments: Any) -> None:
    if name not in TOOLS or not isinstance(arguments, dict):
        raise ValueError("Unknown memory tool or invalid arguments")
    _, required, optional = TOOLS[name]
    if set(arguments) - set((*required, *optional)) or set(required) - set(arguments):
        raise ValueError("Memory tool arguments contain missing or unrecognized fields")
    for key, value in arguments.items():
        schema = FIELDS[key]
        if schema["type"] == "string":
            if not isinstance(value, str) or not schema.get("minLength", 0) <= len(value) <= schema.get("maxLength", 65536):
                raise ValueError(f"Invalid {key}")
            if "enum" in schema and value not in schema["enum"]:
                raise ValueError(f"Invalid {key}")
        elif schema["type"] == "integer":
            if type(value) is not int or not schema["minimum"] <= value <= schema["maximum"]:
                raise ValueError(f"Invalid {key}")
        elif key == "proposal":
            if (not isinstance(value, dict) or set(value) - set(schema["properties"])
                    or set(schema["required"]) - set(value) or value.get("type") != "proposal"):
                raise ValueError("Invalid native proposal fields")
            # A client controls every nested field; bound them before the native worker serializes them.
            for field, item in value.items():
                rule = schema["properties"][field]
                if rule["type"] == "string":
                    valid = isinstance(item, str) and rule.get("minLength", 0) <= len(item) <= rule.get("maxLength", 65536)
                elif rule["type"] == "integer":
                    valid = type(item) is int and rule["minimum"] <= item <= rule["maximum"]
                else:
                    valid = type(item) in (int, float) and rule["minimum"] <= item <= rule["maximum"]
                if not valid:
                    raise ValueError(f"Invalid native proposal field: {field}")
        elif key == "reference":
            if not isinstance(value, dict) or set(value) != {"id", "revision"} or not isinstance(value["id"], str) or not value["id"]:
                raise ValueError("Invalid memory reference")
            if type(value["revision"]) is not int or value["revision"] < 1:
                raise ValueError("Invalid memory revision")


class MemoryConfiguration:
    def __init__(self, path: Path):
        self.path = Path(path)

    @staticmethod
    def check_owner(configuration: dict[str, Any], account: str | None) -> None:
        # Internal owner helpers have no HTTP account; HTTP callers supply a verified qualified account.
        if account is not None and (not isinstance(account, str)
                or configuration.get('accounts', {}).get(account) != configuration['principal']):
            raise PermissionError('This dashboard account has no installation owner binding')

    @staticmethod
    def validate(configuration: Any) -> None:
        if not isinstance(configuration, dict) or type(configuration.get("version")) is not int or configuration["version"] != 1:
            raise ValueError("Unsupported memory configuration")
        if not isinstance(configuration.get("root"), str) or not Path(configuration["root"]).is_absolute():
            raise ValueError("Memory needs an absolute installed LifeOS root")
        if type(configuration.get("ownership_enabled", False)) is not bool:
            raise ValueError("Memory ownership must be enabled explicitly")
        if type(configuration.get("sharing_enabled", False)) is not bool:
            raise ValueError("Memory sharing must be enabled explicitly")
        workspace = configuration.get('hermes_workspace')
        if workspace is not None and (not isinstance(workspace, str) or not Path(workspace).is_absolute()):
            raise ValueError('Hermes publication needs an absolute installed workspace')
        MemoryPolicy(configuration)
        from .discord_audience import validate_bindings
        validate_bindings(configuration)
        clients = configuration.get("clients", {})
        if not isinstance(clients, dict):
            raise ValueError("Memory clients must have server-owned grants")
        for identifier, grant in clients.items():
            if not isinstance(identifier, str) or not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", identifier):
                raise ValueError("Invalid memory client identifier")
            if not isinstance(grant, dict) or type(grant.get("enabled")) is not bool:
                raise ValueError("Invalid memory client grant")
            for key in ("read", "write", "projects"):
                values = grant.get(key, [])
                if not isinstance(values, list) or any(not isinstance(value, str) or not value.strip() for value in values):
                    raise ValueError("Invalid memory client permissions")
            if not set(grant.get("read", [])) <= CATEGORIES or not set(grant.get("write", [])) <= {"project"}:
                raise ValueError("Clients can write project facts; identity changes require native review")
            if (not isinstance(grant.get("proposals", []), list)
                    or any(not isinstance(value, str) or value not in {"create", "review"} for value in grant.get("proposals", []))):
                raise ValueError("External clients cannot approve native proposals")
            if not isinstance(grant.get("model_route", "unknown"), str) or not grant.get("model_route", "unknown"):
                raise ValueError("Invalid declared client model route")

    def load(self) -> dict[str, Any]:
        if self.path.is_symlink() or not self.path.is_file():
            raise MemoryUnavailable("Memory setup is unavailable")
        info = self.path.stat()
        if info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise MemoryUnavailable("Memory configuration needs private owner permissions")
        configuration = json.loads(self.path.read_text())
        self.validate(configuration)
        if 'LIFEOS_MEMORY_CONFIGURATION_REVISION' in os.environ:
            self.check_revision(configuration, os.environ['LIFEOS_MEMORY_CONFIGURATION_REVISION'])
        return configuration

    @staticmethod
    def check_revision(configuration, expected):
        if (not isinstance(expected, str) or re.fullmatch('[0-9a-f]{64}', expected) is None
                or MemoryPolicy(configuration).revision != expected):
            raise MemoryUnavailable('The initiating owner configuration changed before this job operation')

    def save(self, configuration: dict[str, Any]) -> None:
        self.validate(configuration)
        with self._lock():
            self._publish(configuration)

    @contextmanager
    def _lock(self):
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        descriptor = os.open(self.path.with_name(self.path.name + '.lock'),
                             os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            info = os.fstat(descriptor)
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
                raise MemoryUnavailable('Memory configuration lock needs private owner permissions')
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            yield
        finally:
            os.close(descriptor)

    def _publish(self, configuration: dict[str, Any]) -> None:
        if self.path.is_symlink():
            raise MemoryUnavailable('Memory configuration must not be a symlink')
        publish(self.path, (json.dumps(configuration, indent=2) + '\n').encode())

    def update(self, change) -> dict[str, Any]:
        with self._lock():
            configuration = self.load()
            change(configuration)
            self.validate(configuration)
            self._publish(configuration)
            return configuration


class MemoryService:
    def __init__(self, configuration: MemoryConfiguration, *, audience_lookup=None):
        self.configuration = configuration
        self.audience_lookup = audience_lookup

    def scope(self, context: SessionContext) -> MemoryScope:
        return self._context_scope(self.configuration.load(), context)

    def _prompt(self, configuration, scope, operation, arguments, *, check_authority=None):
        from .memory_prompt import bundle, preview, publish_prompt
        memory = NativeMemory(Path(configuration['root']))
        if operation == 'prompt_bundle' and set(arguments) == {'keepOutputFormat'}:
            result = {'ok': True, 'bundle': bundle(memory, scope, keep_output_format=arguments['keepOutputFormat'])}
        elif operation in ('prompt_preview', 'prompt_publish'):
            if not isinstance(arguments.get('home'), str) or Path(arguments['home']).absolute() != self.configuration.path.parent.absolute():
                raise ValueError('Prompt publication requires the configured Hermes profile')
            if operation == 'prompt_preview' and set(arguments) == {'home', 'keepOutputFormat'}:
                result = {'ok': True, **preview(memory, scope, self.configuration.path.parent,
                                               keep_output_format=arguments['keepOutputFormat'])}
            elif operation == 'prompt_publish' and set(arguments) == {'home', 'keepOutputFormat', 'signature', 'previous_digest'}:
                def check_current():
                    if self.configuration.load() != configuration:
                        raise MemoryUnavailable('The memory configuration changed during prompt publication')
                    if check_authority is not None:
                        check_authority()
                receipt = publish_prompt(memory, scope, self.configuration.path.parent,
                    arguments['signature'], arguments['previous_digest'],
                    keep_output_format=arguments['keepOutputFormat'], check_current=check_current)
                result = {'ok': receipt['status'] in ('committed', 'unchanged'), 'receipt': receipt}
            else:
                raise ValueError('Choose a fixed prompt preview or publication action')
        else:
            raise ValueError('Choose a fixed prompt preview or publication action')
        if check_authority is not None:
            check_authority()
        return result

    def administrative(self, authorization, operation, arguments):
        from .memory_administration import validate
        try:
            if operation not in ('prompt_bundle', 'prompt_preview', 'prompt_publish') or not isinstance(arguments, dict):
                raise ValueError('Administrative authorization permits only prompt mount operations')
            configuration, scope = validate(self.configuration, authorization)
            return self._prompt(configuration, scope, operation, arguments,
                                check_authority=lambda: validate(self.configuration, authorization))
        except (MemoryUnavailable, PermissionError, ValueError, OSError, sqlite3.Error, subprocess.TimeoutExpired):
            return {'ok': False, 'code': 'EWRITE_FAILED', 'message': 'Administrative prompt mounting is unavailable'}

    def native(self, context: SessionContext, operation: str, arguments: dict[str, Any]) -> dict[str, Any]:
        try:
            configuration = self.configuration.load()
            scope = self._context_scope(configuration, context)
        except (MemoryUnavailable, ValueError, OSError, sqlite3.Error, subprocess.TimeoutExpired) as error:
            return {'ok':False, 'code':'EWRITE_FAILED' if operation in ('add','set') else 'EINVAL_PATH',
                    'message':str(error)}
        result = self._native_operation(context, operation, arguments, configuration, scope)
        try:
            self._check_current_context(configuration, context, scope)
        except (MemoryUnavailable, ValueError, OSError):
            return {'ok':False, 'code':'EACCESS_CHANGED',
                    'message':'Current memory authority is unavailable; the operation response is withheld.'}
        return result

    def _native_operation(self, context, operation, arguments, configuration, scope):
        try:
            memory = NativeMemory(Path(configuration["root"]))
            if operation == 'atlas_collect' and set(arguments) == {'collector'}:
                from .memory_atlas import collect
                return collect(memory, scope, **arguments,
                    check_current=lambda:self._check_current_context(configuration,context,scope))
            if operation == 'user_index' and set(arguments) == {'query','publish_index','request_id'}:
                from .memory_user_index_publish import run
                return run(memory, scope, **arguments,
                    check_current=lambda:self._check_current_context(configuration,context,scope))
            if operation == 'manual_state' and set(arguments) == {'tool', 'args'}:
                from .memory_manual_state import run
                return run(memory, scope, **arguments,
                    check_current=lambda:self._check_current_context(configuration,context,scope))
            if operation in {'local_run_start', 'local_run_finish'}:
                from .memory_local_runs import run
                return run(memory, scope, operation, arguments,
                    check_current=lambda:self._check_current_context(configuration,context,scope))
            if operation == 'local_inputs':
                from .memory_local_refresh import inputs
                return inputs(memory, scope, operation, arguments,
                    check_current=lambda:self._check_current_context(configuration,context,scope))
            if operation in {'local_refresh_prepare', 'local_refresh_check', 'local_refresh_publish'}:
                from .memory_local_refresh import synthesis
                return synthesis(memory, scope, operation, arguments,
                    check_current=lambda:self._check_current_context(configuration,context,scope))
            if operation in {'algorithm_summary_prepare', 'algorithm_summary_check', 'algorithm_summary_publish'}:
                from .memory_algorithm_summary import synthesis
                return synthesis(memory, scope, operation, arguments,
                    check_current=lambda:self._check_current_context(configuration,context,scope))
            if operation in {'atlas_insight_prepare', 'atlas_insight_check', 'atlas_insight_publish'}:
                from .memory_atlas_insight import synthesis
                return synthesis(memory, scope, operation, arguments,
                    check_current=lambda:self._check_current_context(configuration,context,scope))
            if operation in {'conduit_prepare', 'conduit_check', 'conduit_publish'}:
                from .memory_conduit_insight import synthesis
                return synthesis(memory, scope, operation, arguments,
                    check_current=lambda:self._check_current_context(configuration,context,scope))
            if operation == 'telos_template' and not arguments:
                from .memory_telos_template import view
                return view(memory, scope,
                    check_current=lambda:self._check_current_context(configuration,context,scope))
            if operation == 'skill_hygiene' and set(arguments) == {'args'}:
                from .memory_skill_hygiene import run
                return run(memory, scope, **arguments,
                    check_current=lambda:self._check_current_context(configuration,context,scope))
            if operation == 'banner' and set(arguments) == {'args', 'width'}:
                from .memory_banner import run
                return run(memory, scope, **arguments,
                    check_current=lambda:self._check_current_context(configuration,context,scope))
            if operation == 'recommend' and set(arguments) == {'args'}:
                from .memory_recommend import run
                return run(memory, scope, **arguments,
                    check_current=lambda:self._check_current_context(configuration,context,scope))
            if operation == 'morning_brief' and not arguments:
                from .memory_morning_brief import run
                return run(memory,scope,check_current=lambda:self._check_current_context(configuration,context,scope))
            if operation == 'upgrade_store' and set(arguments)=={'action','arguments','request_id'}:
                from .memory_upgrades import run
                return run(memory,scope,**arguments,source_session=context.session_id,
                    check_current=lambda:self._check_current_context(configuration,context,scope))
            if operation == 'hypothesis_list' and not arguments:
                from .memory_hypothesis_queue import pending
                return {'ok':True,'hypotheses':pending(memory,scope,
                    check_current=lambda: self._check_current_context(configuration,context,scope))}
            if operation == 'hypothesis_review' and set(arguments) == {'target','note','request_id'}:
                from .memory_hypothesis_review import review
                return review(memory, scope, **arguments,
                    check_current=lambda: self._check_current_context(configuration, context, scope))
            if operation == 'hypothesis_view' and set(arguments) == {'target'}:
                from .memory_hypothesis_queue import view
                return view(memory, scope, **arguments,
                    check_current=lambda: self._check_current_context(configuration, context, scope))
            if operation == 'event_append' and set(arguments) == {'path','event','request_id'}:
                from .memory_events import append
                return append(memory, scope, **arguments, source_session=context.session_id,
                    check_current=lambda: self._check_current_context(configuration, context, scope))
            if operation == 'knowledge_conformance' and set(arguments) == {'request_id'}:
                from .memory_knowledge_conformance import run
                return run(memory, scope, **arguments, source_session=context.session_id,
                    check_current=lambda: self._check_current_context(configuration, context, scope))
            if operation == 'knowledge_lint' and set(arguments) == {'json','list','directory'}:
                from .memory_knowledge_lint import run
                return run(memory, scope, **arguments,
                    check_current=lambda: self._check_current_context(configuration, context, scope))
            if operation == 'knowledge_view' and set(arguments) == {'view','request_id'}:
                from .memory_knowledge_views import run
                return run(memory, scope, **arguments, source_session=context.session_id,
                    check_current=lambda: self._check_current_context(configuration, context, scope))
            if operation == 'knowledge_harvest' and set(arguments) == {'source','dry_run','max_notes','request_id'}:
                from .memory_knowledge_harvest import run
                return run(memory, scope, **arguments, source_session=context.session_id,
                    check_current=lambda: self._check_current_context(configuration, context, scope))
            if operation == 'session_harvest' and set(arguments) == {'recent','all','session','projects_dir','dry_run','mine'}:
                from .memory_session_harvest import run
                return run(memory, scope, configuration, self.configuration.path.parent, **arguments,
                    check_current=lambda: self._check_current_context(configuration, context, scope),
                    session_scope=lambda session: self._context_scope(configuration, session))
            if operation == 'proposal_gc' and set(arguments) == {'apply', 'auto', 'route'}:
                from .memory_proposal_gc import run
                return run(memory, scope, **arguments,
                    check_current=lambda: self._check_current_context(configuration, context, scope))
            if operation in ('prompt_bundle', 'prompt_preview', 'prompt_publish'):
                return self._prompt(configuration, scope, operation, arguments,
                    check_authority=lambda: self._check_current_context(configuration, context, scope))
            if operation == 'staged_preview' and set(arguments) == {'target','all','project'}:
                from .memory_staging import preview
                return {'ok':True,**preview(memory,scope,**arguments)}
            if operation == 'learning_hypotheses' and set(arguments) == {'path','window','dry_run','no_inference','once_daily','request_id'}:
                from .memory_hypotheses import derive
                def check_current():
                    self._check_current_context(configuration, context, scope)
                return derive(memory, scope, arguments, check_current=check_current)
            if (operation == 'recurrence_sources' and set(arguments) == {'base'}
                    or operation == 'recurrence_append' and set(arguments) == {'base','record','request_id'}):
                from .memory_recurrence import sources, append
                def check_current():
                    self._check_current_context(configuration, context, scope)
                if operation == 'recurrence_sources':
                    return sources(memory, scope, arguments['base'], check_current=check_current)
                return append(memory, scope, arguments, check_current=check_current)
            if operation == 'learning_ratings' and set(arguments) == {'path','month','all','dry_run','request_id'}:
                from .memory_learning import ratings
                def check_current():
                    self._check_current_context(configuration, context, scope)
                return ratings(memory, scope, arguments, check_current=check_current)
            if (operation == 'wisdom_frames' and set(arguments) == {'base'}
                    or operation == 'wisdom_synthesis' and set(arguments) == {'base','health','dry_run','request_id'}):
                from .memory_wisdom import frames, synthesize
                def check_current():
                    self._check_current_context(configuration, context, scope)
                if operation == 'wisdom_frames':
                    return frames(memory, scope, arguments['base'], check_current=check_current)
                return synthesize(memory, scope, arguments, check_current=check_current)
            if operation == 'wisdom_frame_update' and set(arguments) == {'domain','observation','type','path','request_id'}:
                from .memory_wisdom import update_frame
                def check_current():
                    self._check_current_context(configuration, context, scope)
                return update_frame(memory, scope, arguments, check_current=check_current)
            if operation == 'staged_promote' and set(arguments) == {'target','all','project','signature','request_id'}:
                from .memory_staging import promote
                receipt=promote(memory,scope,**arguments,source_session=context.session_id,
                    check_current=lambda:self._check_current_context(configuration,context,scope))
                return {'ok':receipt['status'] in ('committed','unchanged'),'receipt':receipt}
            if operation == 'staged_reject' and set(arguments) == {'target','all','request_id'}:
                from .memory_staging import reject
                receipt=reject(memory,scope,**arguments,source_session=context.session_id,
                    check_current=lambda:self._check_current_context(configuration,context,scope))
                return {'ok':receipt['status'] in ('committed','unchanged'),'receipt':receipt}
            if operation == 'restore_list' and set(arguments) == {'category'}:
                from .memory_restore import list_snapshots
                return list_snapshots(memory,scope,arguments['category'])
            if operation == 'restore_preview' and set(arguments) == {'snapshot'}:
                from .memory_restore import preview
                return {'ok':True,**preview(memory,scope,arguments['snapshot'])}
            if operation == 'restore' and set(arguments) == {'snapshot','signature','request_id'}:
                from .memory_restore import restore
                receipt=restore(memory,scope,**arguments)
                return {'ok':receipt['status'] in ('committed','unchanged'),'receipt':receipt}
            if operation == 'canonical_corpus' and set(arguments) == {'root'}:
                from .memory_canonical import corpus
                return corpus(memory,scope,arguments['root'])
            if operation in {'distill_read', 'distill_mark', 'distill_prepare', 'distill_check', 'distill_publish'}:
                from .memory_distill import read, mark, synthesis

                def check_current():
                    current = self.configuration.load()
                    if current != configuration or self._context_scope(current, context).signature != scope.signature:
                        raise MemoryUnavailable('Distill authority changed during collection')

                if operation == 'distill_read' and set(arguments) == {'args'}:
                    return read(memory, scope, **arguments, check_current=check_current)
                if operation == 'distill_mark' and set(arguments) == {'path'}:
                    return mark(memory, scope, **arguments, check_current=check_current)
                if operation.startswith(('distill_prepare', 'distill_check', 'distill_publish')):
                    return synthesis(memory, scope, operation, arguments, check_current=check_current)
                raise ValueError('Choose declared native distill arguments')
            if operation == 'read_freshness' and set(arguments) == {'view', 'path', 'slug'}:
                from .memory_freshness import read

                def check_current():
                    current = self.configuration.load()
                    if current != configuration or self._context_scope(current, context).signature != scope.signature:
                        raise MemoryUnavailable('Freshness authority changed during rendering')

                return read(memory, scope, **arguments, check_current=check_current)
            if operation in {'pulse_adapter_inputs', 'pulse_adapter_check', 'pulse_adapter_log', 'inference_log', 'pulse_data', 'pulse_manifests', 'pulse_manifest_read'}:
                from .memory_pulse_adapters import inputs, log, data, manifests

                def check_current():
                    current = self.configuration.load()
                    if current != configuration or self._context_scope(current, context).signature != scope.signature:
                        raise MemoryUnavailable('PULSE authority changed during execution')

                if operation == 'pulse_manifests' and not arguments:
                    return manifests(memory, scope, check_current=check_current)
                if operation == 'pulse_manifest_read' and set(arguments) == {'path'}:
                    if not isinstance(arguments['path'], str):
                        raise ValueError('PULSE manifest read requires its declared installed path')
                    return manifests(memory, scope, **arguments, check_current=check_current)
                if operation == 'pulse_adapter_inputs' and set(arguments) == {'manifest', 'force'}:
                    return inputs(memory, scope, **arguments, check_current=check_current)
                if operation == 'pulse_adapter_check' and set(arguments) == {'manifest', 'force', 'signature'}:
                    if not isinstance(arguments['signature'], str):
                        raise ValueError('PULSE input checks require their plan signature')
                    return inputs(memory, scope, **arguments, check_current=check_current)
                if operation == 'inference_log' and set(arguments) == {'entry'}:
                    return log(memory, scope, **arguments, check_current=check_current, inference=True)
                if operation == 'pulse_adapter_log' and set(arguments) == {'entry'}:
                    return log(memory, scope, **arguments, check_current=check_current)
                if operation == 'pulse_data' and set(arguments) == {'action', 'identifier', 'value'}:
                    return data(memory, scope, **arguments, check_current=check_current)
                raise ValueError('PULSE requires its declared native arguments')
            if operation in {'derived_sync_plan', 'derived_sync_check', 'derived_sync_publish'}:
                from .memory_derived_sync import handle

                def check_current():
                    current = self.configuration.load()
                    if current != configuration or self._context_scope(current, context).signature != scope.signature:
                        raise MemoryUnavailable('Derivative sync authority changed during execution')

                return handle(memory, scope, operation, arguments, check_current=check_current)
            if operation == 'deny_hashes' and set(arguments) == {'args'}:
                from .memory_deny_hashes import run

                def check_current():
                    current = self.configuration.load()
                    if current != configuration or self._context_scope(current, context).signature != scope.signature:
                        raise MemoryUnavailable('Deny hash authority changed during rendering')

                return run(memory, scope, **arguments, check_current=check_current)
            if operation == 'hermes_soul' and set(arguments) == {'args', 'home', 'workspace'}:
                from .memory_hermes_soul import run

                def check_current():
                    current = self.configuration.load()
                    if current != configuration or self._context_scope(current, context).signature != scope.signature:
                        raise MemoryUnavailable('Hermes soul authority changed during rendering')

                return run(memory, scope, self.configuration.path.parent, configuration.get('hermes_workspace'),
                           **arguments, check_current=check_current)
            if operation == 'interview_scan' and set(arguments) == {'args'}:
                from .memory_interview_scan import read

                def check_current():
                    current = self.configuration.load()
                    if current != configuration or self._context_scope(current, context).signature != scope.signature:
                        raise MemoryUnavailable('Interview scan authority changed during rendering')

                return read(memory, scope, **arguments, check_current=check_current)
            if operation in {'interview_due_inputs', 'interview_due_mark', 'interview_due_cache_write'}:
                from .memory_interview import read, write
                handlers = {'interview_due_inputs': (read, {'now', 'evidence_present'}),
                            'interview_due_mark': (write, {'now', 'path'}),
                            'interview_due_cache_write': (write, {'verdict', 'path'})}
                handler, fields = handlers[operation]
                if set(arguments) != fields:
                    raise ValueError('Interview calculation requires its declared native arguments')

                def check_current():
                    current = self.configuration.load()
                    if current != configuration or self._context_scope(current, context).signature != scope.signature:
                        raise MemoryUnavailable('Interview authority changed during rendering')

                return handler(memory, scope, **arguments, check_current=check_current)
            if operation in {'state_evidence_read', 'state_evidence_cache_read', 'state_evidence_cache_write'}:
                from .memory_evidence import read, cache_read, cache_write
                handlers = {'state_evidence_read': (read, {'domain', 'now'}),
                            'state_evidence_cache_read': (cache_read, {'path'}),
                            'state_evidence_cache_write': (cache_write, {'path', 'evidence'})}
                handler, fields = handlers[operation]
                if set(arguments) != fields:
                    raise ValueError('State evidence requires its declared native arguments')

                def check_current():
                    current = self.configuration.load()
                    if current != configuration or self._context_scope(current, context).signature != scope.signature:
                        raise MemoryUnavailable('State evidence authority changed during rendering')

                return handler(memory, scope, **arguments, check_current=check_current)
            if operation == 'freshness_migration' and set(arguments) == {'dry_run', 'state'}:
                from .memory_freshness_migration import run

                def check_current():
                    current = self.configuration.load()
                    if current != configuration or self._context_scope(current, context).signature != scope.signature:
                        raise MemoryUnavailable('Freshness migration authority changed during rendering')

                return run(memory, scope, **arguments, check_current=check_current)
            if operation == 'freshness_cache' and not arguments:
                from .memory_freshness_cache import run

                def check_current():
                    current = self.configuration.load()
                    if current != configuration or self._context_scope(current, context).signature != scope.signature:
                        raise MemoryUnavailable('Freshness cache authority changed during rendering')

                return run(memory, scope, check_current=check_current)
            if operation == 'write_freshness' and set(arguments) == {'kind', 'path', 'slug', 'by'}:
                from .memory_freshness import write

                def check_current():
                    current = self.configuration.load()
                    if current != configuration or self._context_scope(current, context).signature != scope.signature:
                        raise MemoryUnavailable('Timestamp authority changed during rendering')

                return write(memory, scope, **arguments, check_current=check_current)
            if operation == 'memory_graph' and set(arguments) == {'root', 'command', 'layer', 'target'}:
                from .memory_graph import run

                def check_current():
                    current = self.configuration.load()
                    if current != configuration or self._context_scope(current, context).signature != scope.signature:
                        raise MemoryUnavailable('Graph authority changed during rendering')

                return run(memory, scope, **arguments, check_current=check_current)
            if operation == 'counts' and set(arguments) == {'root', 'lifeos_dir', 'only'}:
                from .memory_counts import read

                def check_current():
                    current = self.configuration.load()
                    if current != configuration or self._context_scope(current, context).signature != scope.signature:
                        raise MemoryUnavailable('Native count authority changes during collection')

                return read(memory, scope, **arguments, check_current=check_current)
            if operation == 'context_audit' and set(arguments) == {'root', 'json_output'}:
                from .memory_context_audit import run

                def check_current():
                    current = self.configuration.load()
                    if current != configuration or self._context_scope(current, context).signature != scope.signature:
                        raise MemoryUnavailable('Context audit authority changes during the operation')

                return run(memory, scope, **arguments, check_current=check_current)
            if operation == 'seed_pulse' and set(arguments) in ({'root', 'config_dir', 'generators'},
                    {'root', 'config_dir', 'generators', 'request_id'}):
                from .memory_seed import run

                def check_current():
                    current = self.configuration.load()
                    if current != configuration or self._context_scope(current, context).signature != scope.signature:
                        raise MemoryUnavailable('Interview seed authority changes during publication')

                return run(memory, scope, **arguments, check_current=check_current)
            if operation == 'lifeos_state' and set(arguments) == {'root', 'json_output'}:
                from .memory_state import run

                def check_current():
                    current = self.configuration.load()
                    if current != configuration or self._context_scope(current, context).signature != scope.signature:
                        raise MemoryUnavailable('State authority changed during rendering')

                return run(memory, scope, **arguments, check_current=check_current)
            if operation == 'telos_summary' and set(arguments) == {'root'}:
                from .memory_telos import run

                def check_current():
                    current = self.configuration.load()
                    if current != configuration or self._context_scope(current, context).signature != scope.signature:
                        raise MemoryUnavailable('TELOS summary authority changed during rendering')

                return run(memory, scope, **arguments, check_current=check_current)
            if operation == "check_sources" and not arguments:
                from .memory_sources import authorize
                return authorize(scope)
            if operation == "check_source" and set(arguments) == {"path"}:
                from .memory_sources import check
                return check(memory,scope,arguments['path'])
            if operation == "filter_source" and set(arguments) == {"content","timestamp"}:
                from .memory_sources import filter_content
                return filter_content(memory,scope,**arguments)
            if operation == "read_source" and set(arguments) == {"path"}:
                from .memory_sources import read
                return read(memory,scope,arguments['path'])
            if operation == "read_diagnostic" and set(arguments) == {"path"}:
                from .memory_diagnostics import read
                return read(memory,scope,arguments['path'])
            if operation == "check_diagnostic" and set(arguments) == {"path"}:
                from .memory_diagnostics import check
                return check(memory,scope,arguments['path'])
            if operation == "check_diagnostic_report" and set(arguments) == {"path"}:
                from .memory_diagnostics import check
                return check(memory,scope,arguments['path'],report=True)
            if operation == "filter_diagnostic" and set(arguments) == {"content", "timestamp"}:
                from .memory_diagnostics import filter_report
                return filter_report(memory,scope,**arguments)
            if operation == "diagnose_hot" and set(arguments) == {"path"}:
                from .memory_diagnostics import diagnose_hot
                return diagnose_hot(memory,scope,arguments['path'])
            if operation == "proposal_list" and set(arguments) == {"path"}:
                from .memory_proposals import QUEUE
                if not isinstance(arguments['path'], str) or Path(arguments['path']).absolute() != memory._path(QUEUE):
                    raise ValueError("Native proposal review needs the installed queue")
                return {"rows":memory.review_proposals(scope, include_resolved=True)}
            if operation == "proposal_decision":
                required = {"reference", "decision", "request_id"}
                if not required <= set(arguments) or set(arguments) - required - {"content", "note", "confidence_threshold"}:
                    raise ValueError("Invalid native proposal decision fields")
                receipt = memory.decide_proposal(scope, **arguments,
                    check_current=lambda _connection: self._check_current_context(configuration, context, scope))
                row = memory.proposal_decision_row(scope, receipt['proposal_reference']) if receipt['status'] == 'committed' else None
                return {"ok":receipt['status'] == 'committed', "row":row, "receipt":receipt,
                        "reason":receipt.get('reason', '')}
            if operation == "retrieve" and set(arguments) == {"query", "options"}:
                return memory.relevant_context(scope, **arguments)
            if operation == "filter_history" and set(arguments) == {"content", "timestamp"}:
                return memory.filter_history(scope, **arguments)
            if operation in ("read", "set"):
                if not isinstance(arguments.get("path"), str):
                    raise ValueError("A native hot-memory path is required")
                categories = {str(memory._path(path)): category for category, path in HOT_FILES.items()}
                category = categories.get(str(Path(arguments["path"]).absolute()))
                if category is None:
                    raise ValueError("This is not a supported native hot-memory path")
                if operation == "read" and set(arguments) == {"path"}:
                    return memory.read_hot(scope, category)
                if operation == "set" and set(arguments) == {"path", "entries", "request_id", "observed_revision", "allow_drastic"}:
                    return memory.native_set(scope, category, source_session=context.session_id,
                                             check_current=lambda _connection: self._check_current_context(configuration, context, scope),
                                             **{key: value for key, value in arguments.items() if key != "path"})
            if operation == "add" and set(arguments) == {"item", "request_id", "project", "observed_revision"}:
                return memory.native_add(scope, **arguments, source_session=context.session_id,
                    check_current=lambda _connection: self._check_current_context(configuration, context, scope))
            raise ValueError("Unsupported native memory operation or arguments")
        except (MemoryUnavailable, ValueError, OSError, sqlite3.Error, subprocess.TimeoutExpired) as error:
            return {"ok": False, "code": "EWRITE_FAILED" if operation in ("add", "set") else "EINVAL_PATH", "message": str(error)}

    @staticmethod
    def client_scope(configuration: dict[str, Any], identifier: str) -> MemoryScope:
        grant = configuration.get("clients", {}).get(identifier)
        if not configuration.get("sharing_enabled", False) or grant is None or not grant["enabled"]:
            raise MemoryUnavailable("This memory connection is disabled or revoked")
        principal = f"client:{identifier}"
        policy = MemoryPolicy({"version": 1, "principal": configuration["principal"],
                               "accounts": {f"mcp:{identifier}": principal},
                               "destinations": {f"mcp:{identifier}": {
                                   "visibility": "private", "participants": [principal],
                                   "read": grant.get("read", ["project"]), "write": grant.get("write", []),
                                   "projects": grant.get("projects", []), "model_routes": [grant.get("model_route", "unknown")],
                                   "proposals": grant.get("proposals", []),
                               }}})
        return policy.resolve(SessionContext("mcp", identifier, identifier, "private", (principal,),
                                             grant.get("model_route", "unknown"), ""))

    def call_client(self, identifier: str, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        try:
            configuration = self.configuration.load()
            scope = self.client_scope(configuration, identifier)
        except (MemoryUnavailable, ValueError, OSError) as error:
            return {"status": "rejected", "reason": str(error)}

        def check_current(*_):
            current = self.configuration.load()
            if current["root"] != configuration["root"] or self.client_scope(current, identifier) != scope:
                raise MemoryUnavailable("This memory connection changed during the request")
        result = self._call(configuration, scope, name, arguments, check_current=check_current)
        try:
            check_current()
        except (MemoryUnavailable, ValueError, OSError) as error:
            return {"status": "rejected", "reason": str(error)}
        return result

    def call_context(self, context: SessionContext, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        try:
            configuration = self.configuration.load()
            scope = self._context_scope(configuration, context)
        except (MemoryUnavailable, ValueError, OSError) as error:
            return {"status": "unavailable", "reason": str(error)}
        def check_current(_connection=None):
            self._check_current_context(configuration, context, scope)
        result = self._call(configuration, scope, name, arguments,
                            source_session=context.session_id, check_current=check_current)
        try:
            check_current()
        except (MemoryUnavailable, ValueError, OSError) as error:
            return {'status':'unavailable', 'reason':str(error)}
        return result

    def _context_scope(self, configuration, context):
        self._check_audience(configuration, context)
        return MemoryPolicy(configuration).resolve(context)

    def _check_current_context(self, configuration, context, scope):
        current = self.configuration.load()
        if current != configuration or self._context_scope(current, context).signature != scope.signature:
            raise MemoryUnavailable('This memory conversation changes during the request')

    def _check_audience(self, configuration, context):
        from .discord_audience import context_audience_is_current
        if not context_audience_is_current(configuration, context, audience_lookup=self.audience_lookup):
            raise MemoryUnavailable('The Discord channel audience no longer permits private memory')

    def call(self, scope: MemoryScope, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        try:
            configuration = self.configuration.load()
        except (MemoryUnavailable, ValueError, OSError) as error:
            return {"status": "unavailable", "reason": str(error)}
        return self._call(configuration, scope, name, arguments)

    def _call(self, configuration: dict[str, Any], scope: MemoryScope, name: str, arguments: dict[str, Any],
              *, source_session: str = '', check_current=None) -> dict[str, Any]:
        try:
            _validate_arguments(name, arguments)
        except ValueError as error:
            return {"status": "rejected", "reason": str(error)}
        try:
            memory = NativeMemory(Path(configuration["root"]))
            if not scope.read and not scope.write and not scope.proposals:
                return {"status": "rejected", "reason": scope.reason or "This context has no memory grant"}
            if name == "lifeos_memory_propose":
                result = memory.native_add(scope, arguments["proposal"], request_id=arguments["request_id"], project="",
                                           source_session=source_session, check_current=check_current)
                return result.get("receipt", {"status":"rejected", "reason":result.get("message", "Native proposal failed")})
            if name == "lifeos_memory_proposals":
                return {"status":"ok", "results":memory.review_proposals(scope)}
            if name == "lifeos_memory_decide_proposal":
                return memory.decide_proposal(scope, **arguments, check_current=check_current)
            if name == "lifeos_memory_search":
                return {"status": "ok", "results": memory.recall(scope, **arguments)}
            if name == "lifeos_memory_get":
                return memory.get(scope, arguments["reference"])
            if name == "lifeos_memory_remember":
                return memory.remember(scope, **arguments, source={'kind': 'explicit', 'session': source_session},
                                       check_current=check_current)
            if name == "lifeos_memory_correct":
                return memory.correct(scope, **arguments, check_current=check_current)
            if name == "lifeos_memory_forget":
                return memory.forget(scope, **arguments, check_current=check_current)
            memory._boundary()
            with memory._transaction() as connection:
                connection.execute("SELECT id FROM records LIMIT 1").fetchone()
            memory._native("rank", query="memory health", corpus=[], limit=1)
            return {"status": "ok", "owner": "LifeOS", "read": list(scope.read), "write": list(scope.write),
                    "projects": list(scope.projects), "sharing_enabled": configuration.get("sharing_enabled", False)}
        except (MemoryUnavailable, ValueError, OSError, sqlite3.Error, subprocess.TimeoutExpired) as error:
            return {"status": "unavailable", "reason": str(error)}
