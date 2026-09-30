# ABOUTME: Observes hook selection and runtime boundaries in development processes.
# ABOUTME: Loads an external source-pinned overlay without editing installed code.

from __future__ import annotations

import ast
import base64
import contextvars
import functools
import hashlib
import importlib.machinery
import inspect
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import time
import traceback
import urllib.request
import uuid
import weakref
from pathlib import Path

from .store import Recorder, SENSITIVE, safe

CURRENT = contextvars.ContextVar("development_hook_capture", default={})
RECORDER = None
CONFIG = {}
INSTALLED = False
RESULT_CONTEXT = weakref.WeakKeyDictionary()
RESULT_LOCK = threading.Lock()


def emit(stage, data=None, **fields):
    try:
        if RECORDER:
            metadata = {k: v for k, v in CURRENT.get().items() if not k.startswith("_")}
            RECORDER.emit(stage, data=data, **{**metadata, **fields})
    except Exception:
        # Instrumentation must not turn an allowed operation into a failure.
        pass


def optional_observer(fallback):
    def decorate(function):
        @functools.wraps(function)
        def call(*args, **kwargs):
            try:
                return function(*args, **kwargs)
            except Exception as error:
                emit("instrumentation.failed", {"operation": function.__name__, "error_type": type(error).__name__}, status="capture_gap")
                return fallback(*args, **kwargs)
        return call
    return decorate


def identity(arguments):
    result = {}
    for key in ("session_id", "task_id", "turn_id", "tool_call_id", "call_id"):
        if isinstance(arguments.get(key), (str, int)):
            result["tool_call_id" if key == "call_id" else key] = arguments[key]
    agent = arguments.get("agent")
    if agent is not None:
        result["session_id"] = getattr(agent, "session_id", None)
    ref = arguments.get("ref")
    if ref is not None:
        for target, source in (("tool_call_id", "call_id"), ("task_id", "task_id"), ("tool_name", "name")):
            result[target] = getattr(ref, source, None)
    for key in ("payload", "request"):
        value = arguments.get(key)
        if isinstance(value, dict):
            result.update(identity(value))
            if value.get("hook_event_name"):
                result["native_event"] = value["hook_event_name"]
    return result


def arguments_for(function, args, kwargs):
    try:
        values = dict(inspect.signature(function).bind_partial(*args, **kwargs).arguments)
        # Callback adapters accept session identity in **kwargs.
        for name, parameter in inspect.signature(function).parameters.items():
            if parameter.kind == inspect.Parameter.VAR_KEYWORD and isinstance(values.get(name), dict):
                values.update(values.pop(name))
        return values
    except (ValueError, TypeError):
        return {"args": args, **kwargs}


def observed(function, stage, *, hermes_event=None):
    if getattr(function, "_development_stage", None) == stage:
        return function

    def before(args, kwargs):
        try:
            values = arguments_for(function, args, kwargs)
            context = {**CURRENT.get(), **identity(values)}
        except Exception as error:
            values, context = {}, dict(CURRENT.get())
            emit("instrumentation.failed", {"operation": "callback_identity", "error_type": type(error).__name__}, status="capture_gap")
        if stage in {"callback", "bridge_callback"} and not context.get("callback_id"):
            context["callback_id"] = uuid.uuid4().hex
        if stage == "translation":
            context["dispatch_id"] = uuid.uuid4().hex
            context["_groups"] = {}
            context["native_event"] = values.get("event")
        if stage == "bridge_callback":
            context["bridge_method"] = hermes_event
        if hermes_event and (stage != "bridge_callback" or not context.get("hermes_event")):
            context["hermes_event"] = hermes_event
        token = CURRENT.set(context)
        started = time.monotonic_ns()
        emit(stage + ".entered", values)
        if stage == "remote_hook" and context.get("_detached"):
            emit("hook.started", values)
        return values, token, started

    @optional_observer(lambda *args: None)
    def after(values, result, started):
        fields = {}
        if stage == "response.parsed":
            fields["decision"] = decision(result)
            fields["status"] = "parse_failure" if result is None and str(values.get("stdout", "")).strip().startswith("{") else "parsed"
        emit(stage + ".returned", {"result": result, "effective_arguments": values},
             duration_ns=time.monotonic_ns()-started, evidence_level="boundary-observed", **fields)
        if stage == "remote_hook" and CURRENT.get().get("_detached"):
            emit("hook.failed" if result is None else "hook.completed", {"result": result},
                 status="no_result" if result is None else "intervention" if result.returncode == 2 else "completed" if result.returncode == 0 else "exit_failure",
                 exit_code=result.returncode if result else None, duration_ns=time.monotonic_ns()-started)

    if inspect.iscoroutinefunction(function):
        @functools.wraps(function)
        async def wrapper(*args, **kwargs):
            values, token, started = before(args, kwargs)
            try:
                result = await function(*args, **kwargs)
                after(values, result, started)
                return result
            except BaseException as error:
                emit(stage + ".failed", {"error": error, "traceback": traceback.format_exc()}, status="exception")
                if stage == "remote_hook" and CURRENT.get().get("_detached"):
                    emit("hook.failed", {"error": error}, status="exception")
                raise
            finally:
                CURRENT.reset(token)
    else:
        @functools.wraps(function)
        def wrapper(*args, **kwargs):
            values, token, started = before(args, kwargs)
            try:
                result = function(*args, **kwargs)
                after(values, result, started)
                return result
            except BaseException as error:
                emit(stage + ".failed", {"error": error, "traceback": traceback.format_exc()}, status="exception")
                if stage == "remote_hook" and CURRENT.get().get("_detached"):
                    emit("hook.failed", {"error": error}, status="exception")
                raise
            finally:
                CURRENT.reset(token)
    wrapper._development_observed = True
    wrapper._development_stage = stage
    return wrapper


@optional_observer(lambda bridge, event, values: values)
def groups(bridge, event, values):
    registry = CURRENT.get().get("_groups")
    if registry is not None:
        inventory = [{**{k: v for k, v in group.items() if k != "_remote_project"},
                      **({"capture_workspace": remote_scope(group["_remote_project"])} if group.get("_remote_project") else {})}
                     for group in values]
        raw = json.dumps(safe(inventory, RECORDER.secrets), sort_keys=True, default=lambda v: type(v).__name__)
        digest = hashlib.sha256(raw.encode()).hexdigest()
        for index, group in enumerate(values):
            origin = str(bridge.settings_path) if any(group is item for item in bridge.hooks.get(event, [])) else None
            if origin is None:
                for path, settings in bridge.project_hook_settings.items():
                    if any(group is item for item in settings.get("hooks", {}).get(event, [])):
                        origin = str(path)
                        break
            remote = group.get("_remote_project")
            registry[id(group)] = {"group_index": index, "inventory_id": digest,
                "settings_origin": origin, "origin_observed": origin is not None,
                **remote_scope(remote)}
        entries = [{**registration(bridge, event, group, hook), "hook": hook}
                   for group in values for hook in group.get("hooks", [])]
        emit("inventory.observed", {"event": event, "groups": inventory, "registrations": entries}, inventory_id=digest)
    return values


def remote_scope(project):
    if project is None:
        return {"target_kind": "local"}
    backend = project.backend
    name = type(backend).__name__
    if "SSH" in name:
        identity = {key: getattr(backend, key, None) for key in ("host", "user", "port")}
        kind = "ssh"
    elif "Docker" in name:
        identity = {"container_id": getattr(backend, "_container_id", getattr(backend, "container_id", None))}
        kind = "docker"
    else:
        identity, kind = {"backend_type": name}, "unknown_remote"
    return {"target_kind": kind, "backend_identity": identity, "workspace": project.root, "workspace_cwd": project.cwd}


def registration(bridge, event, group, hook):
    metadata = CURRENT.get().get("_groups", {}).get(id(group), {})
    position = next((i for i, item in enumerate(group.get("hooks", [])) if item is hook), None)
    return {**metadata, "registration_id": f"{metadata.get('inventory_id','unknown')}:{event}:{metadata.get('group_index')}:{position}",
            "hook_index": position, "native_event": event, "hook_kind": hook.get("type"),
            "asynchronous": bool(hook.get("async")), "matcher": group.get("matcher", "")}


@optional_observer(lambda *args: None)
def evaluated(bridge, event, group, hook):
    emit("registration.evaluated", {"hook": hook}, **registration(bridge, event, group, hook))


@optional_observer(lambda *args: None)
def skipped(bridge, event, group, hook, reason):
    for item in ([hook] if hook is not None else group.get("hooks", [])):
        emit("registration.skipped", {"hook": item}, reason=reason, status="skipped",
             **registration(bridge, event, group, item))


def decision(result):
    if not isinstance(result, dict):
        return None
    specific = result.get("hookSpecificOutput") or {}
    return (specific.get("permissionDecision") if isinstance(specific, dict) else None) or result.get("decision") or result.get("action")


@optional_observer(lambda bridge, event, group, hook, value: value)
def job(bridge, event, group, hook, value):
    callback, arguments, asynchronous = value
    context = {**CURRENT.get(), **registration(bridge, event, group, hook), "invocation_id": uuid.uuid4().hex}

    @functools.wraps(callback)
    def call(*args, **kwargs):
        token = CURRENT.set(dict(context))
        started = time.monotonic_ns()
        try:
            if not asynchronous:
                emit("hook.started", {"hook": hook, "arguments": args, "kwargs": kwargs})
            result = callback(*args, **kwargs)
            if result is not None:
                with RESULT_LOCK:
                    RESULT_CONTEXT[result] = dict(context)
            if not asynchronous:
                # The real dispatcher records parsing separately. Do not call its parser twice.
                status = "no_result" if result is None else "intervention" if result.returncode == 2 else "completed" if result.returncode == 0 else "exit_failure"
                emit("hook.failed" if result is None else "hook.completed", {"result": result},
                     status=status, exit_code=result.returncode if result else None,
                     duration_ns=time.monotonic_ns()-started, evidence_level="hook-result")
            return result
        except BaseException as error:
            emit("hook.failed", {"error": error, "traceback": traceback.format_exc()}, status="exception",
                 duration_ns=time.monotonic_ns()-started)
            raise
        finally:
            CURRENT.reset(token)
    return call, arguments, asynchronous


def bridge_module(bridge):
    return sys.modules[type(bridge).__module__]


def decode_result(process, decoder):
    with RESULT_LOCK:
        context = RESULT_CONTEXT.pop(process, None)
    token = CURRENT.set({**CURRENT.get(), **(context or {})})
    try:
        return decoder(process.stdout)
    finally:
        CURRENT.reset(token)


def backend_execute(backend, *args, **kwargs):
    options = dict(kwargs)
    if "stdin_data" in options:
        options["stdin_data"] = transport_input(options["stdin_data"], RECORDER.secrets)
    emit("transport.started", {"args": args, "kwargs": options, "backend_type": type(backend).__name__,
                               "representation": "credential-redacted-wire"})
    started = time.monotonic_ns()
    try:
        result = backend.execute(*args, **kwargs)
        evidence = dict(result)
        evidence["output"] = transport_output(result.get("output", ""), RECORDER.secrets)
        emit("transport.completed", evidence, duration_ns=time.monotonic_ns()-started,
             exit_code=result.get("returncode"), evidence_level="transport-result")
        return result
    except BaseException as error:
        emit("transport.failed", {"error": error, "traceback": traceback.format_exc()}, status="transport_failure")
        raise


def transport_input(text, secrets):
    try:
        lines = text.split("\n")
        count = int(lines[1])
        if count < 0 or count > len(lines) - 3:
            raise ValueError("Invalid transport environment count")
        def encoded(clean):
            return base64.b64encode(clean.encode()).decode()
        lines[0] = encoded(safe(base64.b64decode(lines[0], validate=True).decode(), secrets))
        for index in range(2, count + 2):
            assignment = base64.b64decode(lines[index], validate=True).decode()
            key, value = assignment.split("=", 1)
            clean = safe({key: value}, secrets)[key]
            lines[index] = encoded(key + "=" + clean)
        return safe("\n".join(lines), secrets)
    except (ValueError, UnicodeError, TypeError, IndexError):
        emit("instrumentation.failed", {"operation": "transport_input_redaction"}, status="capture_gap")
        return {"omitted": "Unrecognized transport input cannot be redacted safely"}


def transport_output(text, secrets):
    lines = text.split("\n")
    for index, line in enumerate(lines):
        if re.fullmatch(r"__LIFEOS_HOOK_[a-f0-9]{32}__", line):
            for position in (index + 2, index + 3):
                if position >= len(lines):
                    continue
                try:
                    value = base64.b64decode(lines[position], validate=True)
                    lines[position] = safe(value, secrets)["bytes"]
                except (ValueError, TypeError):
                    # Invalid frames must remain visible without storing undecodable bytes.
                    lines[position] = "[UNDECODABLE-FRAME]"
                    emit("instrumentation.failed", {"operation": "transport_output_redaction"}, status="capture_gap")
    return safe("\n".join(lines), secrets)


class SelectionObserver(ast.NodeTransformer):
    def __init__(self):
        self.active = False
        self.parents = []

    def visit_FunctionDef(self, node):
        previous = self.active
        self.active = node.name in {"_run", "run_project_hook"}
        node = self.generic_visit(node)
        self.active = previous
        return node

    def visit_If(self, node):
        if self.active:
            self.parents.append(node)
            node = self.generic_visit(node)
            self.parents.pop()
            return node
        return self.generic_visit(node)

    def visit_For(self, node):
        node = self.generic_visit(node)
        if self.active and isinstance(node.target, ast.Name) and node.target.id == "hook":
            node.body.insert(0, ast.parse("_development_capture.evaluated(self,event,group,hook)").body[0])
        return node

    def visit_Continue(self, node):
        if not self.active:
            return node
        reason = None
        group_skip = False
        for parent in reversed(self.parents):
            expression = ast.unparse(parent.test)
            if "not native_match" in expression:
                reason, group_skip = "matcher_mismatch", True
                break
            if "parsed.scheme" in expression:
                reason = "unsafe_http_destination"
                break
            if "hook.get('type') != 'command'" in expression:
                reason = "unsupported_type"
                break
            if "not isinstance(command" in expression:
                reason = "invalid_command"
                break
            if "skip_checkpoint" in expression:
                reason = "checkpoint_exclusion"
                break
        if reason:
            extra = ast.parse(f"_development_capture.skipped(self,event,group,{'None' if group_skip else 'hook'},{reason!r})").body[0]
            return [extra, node]
        return node

    def visit_Call(self, node):
        node = self.generic_visit(node)
        if not self.active:
            return node
        if isinstance(node.func, ast.Name) and node.func.id == "_decode_output" and len(node.args) == 1 and ast.unparse(node.args[0]) == "process.stdout":
            return ast.Call(func=ast.Attribute(value=ast.Name(id="_development_capture", ctx=ast.Load()), attr="decode_result", ctx=ast.Load()),
                            args=[ast.Name(id="process", ctx=ast.Load()), node.func], keywords=[])
        if not isinstance(node.func, ast.Attribute):
            return node
        if isinstance(node.func.value, ast.Name) and node.func.value.id == "jobs" and node.func.attr == "append":
            node.args[0] = ast.Call(func=ast.Attribute(value=ast.Name(id="_development_capture", ctx=ast.Load()), attr="job", ctx=ast.Load()),
                                   args=[ast.Name(id=name,ctx=ast.Load()) for name in ("self","event","group","hook")] + node.args,
                                   keywords=[])
        if isinstance(node.func.value, ast.Name) and node.func.value.id == "backend" and node.func.attr == "execute":
            node.func = ast.Attribute(value=ast.Name(id="_development_capture",ctx=ast.Load()), attr="backend_execute",ctx=ast.Load())
            node.args.insert(0, ast.Name(id="backend",ctx=ast.Load()))
        return node


def patch_bridge(module):
    cls = module.HookBridge
    for name in ("command_approval", "pre_tool_call", "pre_llm_call", "post_tool_call",
                 "augment_tool_result", "session_end", "api_request_error", "turn_end",
                 "stop", "task_result"):
        setattr(cls, name, observed(getattr(cls, name), "bridge_callback", hermes_event=name))
    original_groups = cls._hook_groups
    @functools.wraps(original_groups)
    def selected(self, event, *args, **kwargs):
        return groups(self, event, original_groups(self, event, *args, **kwargs))
    cls._hook_groups = selected
    for name in ("_run", "_run_command", "_run_http", "_run_async", "_run_remote_async", "_drain_async_context"):
        original = inspect.getattr_static(cls, name)
        if isinstance(original, staticmethod):
            setattr(cls, name, staticmethod(observed(original.__func__, "translation" if name == "_run" else name.lstrip("_"))))
        else:
            setattr(cls, name, observed(original, "translation" if name == "_run" else name.lstrip("_")))
    original_start = cls._start_async_runner
    @functools.wraps(original_start)
    def handoff(spool_path, process_cwd, environment):
        try:
            path = Path(spool_path)
            request = json.loads(path.read_text())
            request["_development_capture"] = {k:v for k,v in CURRENT.get().items() if not k.startswith("_")}
            request["_development_capture"]["parent_process_id"] = RECORDER.process_id
            # The production runner ignores this field; startup reads it before spool deletion.
            temporary = path.with_name(path.name + ".capture-" + uuid.uuid4().hex)
            try:
                fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(fd, "w") as stream:
                    json.dump(request, stream)
                os.replace(temporary, path)
            finally:
                temporary.unlink(missing_ok=True)
            emit("async.handoff", request)
        except Exception as error:
            emit("instrumentation.failed", {"operation": "async_handoff", "error_type": type(error).__name__}, status="capture_gap")
        return original_start(spool_path, process_cwd, environment)
    cls._start_async_runner = staticmethod(handoff)
    module._decode_output = observed(module._decode_output, "response.parsed")
    original_init = cls.__init__
    @functools.wraps(original_init)
    def initialize(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        emit("bridge.initialized", {"settings_path": self.settings_path, "hooks": self.hooks,
                                    "environment": self.environment, "root": self.root})
        for event, values in self.hooks.items():
            token = CURRENT.set({**CURRENT.get(), "_groups": {}, "inventory_scope": "configured_user_hooks"})
            try:
                groups(self, event, values)
            finally:
                CURRENT.reset(token)
    cls.__init__ = initialize


def patch_module(module, path):
    plugin = Path(CONFIG["plugin_root"])
    if path == plugin / "bridge.py":
        patch_bridge(module)
    elif path == plugin / "remote_hooks.py":
        module.run_project_hook = observed(module.run_project_hook, "remote_hook")
    elif path == plugin / "__init__.py":
        original = module.register
        @functools.wraps(original)
        def register(ctx):
            class Context:
                def __getattr__(self, name):
                    return getattr(ctx, name)
                def register_hook(self, name, callback):
                    return ctx.register_hook(name, observed(callback,"callback",hermes_event=name))
            return original(Context())
        module.register = register
    else:
        names = {
            "plugins.py": ("invoke_hook", "ainvoke_hook", "_dispatch_pre_tool_call_hooks", "get_pre_tool_call_directive", "get_pre_turn_stop_continue_message"),
            "tool_executor.py": ("_pre_tool_block", "_dispatch_authorized_once", "_begin_tool_execution", "_blocked_tool_result", "_commit_tool_result"),
            "turn_context.py": ("build_api_messages",),
            "turn_stop_gates.py": ("_pre_turn_stop_nudge", "apply_stop_gates"),
        }.get(path.name, ())
        for name in names:
            if hasattr(module, name):
                setattr(module, name, observed(getattr(module, name), "host."+name.lstrip("_")))
        if path.name == "adapter.py" and "discord" in path.parts:
            cls = module.DiscordAdapter
            for name in ("_dispatch_discord_message", "_handle_message", "send"):
                if hasattr(cls, name):
                    setattr(cls, name, discord_observed(getattr(cls,name), name))
            if hasattr(cls, "_discord_message_admission"):
                original = cls._discord_message_admission
                @functools.wraps(original)
                def admission(*args, **kwargs):
                    values = arguments_for(original, args, kwargs)
                    message = values.get("message")
                    token = CURRENT.set({**CURRENT.get(), "discord_message_id": str(getattr(message, "id", ""))})
                    try:
                        emit("discord.admission.entered", {"message": discord_snapshot(values), "claim": values.get("claim")})
                        result = original(*args, **kwargs)
                        emit("discord.admission.returned", result, status="accepted" if result[0] else "ignored", evidence_level="admission-observed")
                        return result
                    finally:
                        CURRENT.reset(token)
                cls._discord_message_admission = admission


@optional_observer(lambda values: {"capture_gap": "message_snapshot"})
def discord_snapshot(values):
    message, adapter = values.get("message"), values.get("self")
    if message is None:
        return {k:v for k,v in values.items() if k != "self"}
    return {"id": str(message.id), "content": message.content,
            "channel_id": str(message.channel.id), "author_id": str(message.author.id),
            "mentions": [str(item.id) for item in message.mentions],
            "role_mentions": [str(item.id) for item in message.role_mentions],
            "attachments": [{"id": str(item.id), "filename": item.filename, "size": item.size, "url": item.url} for item in message.attachments],
            "bot_id": str(adapter._client.user.id) if adapter._client and adapter._client.user else None}


def discord_observed(function, name):
    @functools.wraps(function)
    async def call(*args, **kwargs):
        values = arguments_for(function,args,kwargs)
        message = values.get("message")
        # Read attributes only; never repeat admission or deduplication checks.
        snapshot = discord_snapshot(values)
        context = {**CURRENT.get(),"callback_id": uuid.uuid4().hex,"hermes_event":"discord."+name}
        if message is not None:
            context["discord_message_id"] = str(message.id)
        token = CURRENT.set(context)
        started = time.monotonic_ns()
        emit("discord."+name+".entered",snapshot)
        try:
            result = await function(*args,**kwargs)
            status = ("accepted" if result else "ignored") if name != "send" else ("delivered" if getattr(result,"success",False) else "delivery_failed")
            emit("discord."+name+".returned", result, status=status, duration_ns=time.monotonic_ns()-started,evidence_level="adapter-observed")
            return result
        except BaseException as error:
            emit("discord."+name+".failed",{"error":error,"traceback":traceback.format_exc()},status="exception")
            raise
        finally:
            CURRENT.reset(token)
    return call


def patch_processes():
    original = subprocess.run
    @functools.wraps(original)
    def run(*args, **kwargs):
        context = CURRENT.get()
        if not context.get("invocation_id"):
            return original(*args, **kwargs)
        data = kwargs.get("input")
        try:
            payload = json.loads(data) if isinstance(data,(str,bytes)) else {}
        except (ValueError,TypeError):
            payload = {}
        native = isinstance(payload,dict) and payload.get("hook_event_name")
        if not native:
            return original(*args,**kwargs)
        asynchronous = context.get("_detached",False)
        started = time.monotonic_ns()
        emit("hook.started" if asynchronous else "process.started", {"argv": args, "options":kwargs})
        stderr_file = None
        if asynchronous and kwargs.get("stderr") == subprocess.DEVNULL:
            try:
                stderr_file = tempfile.TemporaryFile(mode="w+b")
            except OSError as error:
                emit("instrumentation.failed", {"operation": "stderr_capture", "error_type": type(error).__name__}, status="capture_gap")
        effective = dict(kwargs)
        if stderr_file:
            effective["stderr"] = stderr_file
        try:
            result = original(*args,**effective)
            captured = {"result":result}
            if asynchronous:
                capture_streams(captured, kwargs.get("stdout"), stderr_file)
            status = "intervention" if result.returncode == 2 else "completed" if result.returncode == 0 else "exit_failure"
            emit("hook.completed" if asynchronous else "process.completed",captured,status=status,
                 exit_code=result.returncode,duration_ns=time.monotonic_ns()-started,evidence_level="hook-result")
            return result
        except BaseException as error:
            captured = {"error":error,"traceback":traceback.format_exc()}
            capture_streams(captured, kwargs.get("stdout"), stderr_file)
            emit("hook.failed" if asynchronous else "process.failed",captured,status="timeout" if isinstance(error,subprocess.TimeoutExpired) else "exception",duration_ns=time.monotonic_ns()-started)
            raise
        finally:
            if stderr_file:
                stderr_file.close()
    subprocess.run = run


@optional_observer(lambda *args: None)
def capture_streams(captured, stdout, stderr):
    for name, stream in (("stdout", stdout), ("stderr", stderr)):
        if stream is not None and hasattr(stream, "seek"):
            position = stream.tell()
            try:
                stream.seek(0)
                captured[name] = stream.read()
            finally:
                stream.seek(position)


def patch_http():
    original = urllib.request.OpenerDirector.open
    @functools.wraps(original)
    def open_url(*args, **kwargs):
        if not CURRENT.get().get("invocation_id"):
            return original(*args, **kwargs)
        request = args[1] if len(args) > 1 else kwargs.get("fullurl")
        emit("http.request", {"url": getattr(request, "full_url", request),
                              "headers": getattr(request, "headers", {}),
                              "body": getattr(request, "data", None), "options": kwargs})
        try:
            response = original(*args, **kwargs)
        except Exception as error:
            emit("http.failed", {"error": error}, status="http_failure")
            raise
        class Response:
            def __getattr__(self, key):
                return getattr(response, key)
            def __enter__(self):
                response.__enter__()
                return self
            def __exit__(self, *values):
                return response.__exit__(*values)
            def read(self, *values, **options):
                try:
                    data = response.read(*values, **options)
                except Exception as error:
                    emit("http.failed", {"error": error}, status="http_failure")
                    raise
                limit = values[0] if values else options.get("amt", -1)
                emit("http.response_read", {"body": data, "headers": dict(response.headers)},
                     observed_bytes=len(data), read_limit=limit,
                     completeness="unknown_at_limit" if isinstance(limit, int) and limit >= 0 and len(data) >= limit else "end_of_read")
                return data
        return Response()
    urllib.request.OpenerDirector.open = open_url


def install(configuration):
    global INSTALLED, RECORDER, CONFIG
    if INSTALLED:
        return
    path = Path(configuration)
    config = json.loads(path.read_text())
    if not config.get("enabled"):
        return
    CONFIG = config
    secrets = [value for key,value in os.environ.items() if SENSITIVE.search(key) and len(value)>=4]
    # Account credentials can be loaded by Hermes after Python startup.
    for filename in config.get("credential_files",[]):
        p=Path(filename)
        if p.is_file():
            for line in p.read_text().splitlines():
                if "=" in line and not line.lstrip().startswith("#"):
                    key,value=line.split("=",1)
                    value=value.strip().strip("\"'")
                    if SENSITIVE.search(key) and len(value)>=4:
                        secrets.append(value)
    RECORDER=Recorder(Path(config["root"]),config["run_id"],secrets)
    INSTALLED=True
    emit("process.initialized",{"config":config,"python":sys.version,"argv":sys.argv,"prefix":sys.prefix})
    if len(sys.argv)>1 and Path(sys.argv[0]).resolve()==Path(config["plugin_root"])/"bin/hook_runner.py":
        runner = Path(sys.argv[0]).resolve()
        if hashlib.sha256(runner.read_bytes()).hexdigest() == config["fingerprints"].get(str(runner)):
            request=json.loads(Path(sys.argv[1]).read_text())
            CURRENT.set({**request.get("_development_capture",{}),"_detached":True})
            emit("async.runner_started",request)
            original_replace = os.replace
            def replace(source, destination, *args, **kwargs):
                result = original_replace(source, destination, *args, **kwargs)
                if str(destination) == request.get("result_path"):
                    try:
                        emit("async.context_persisted", json.loads(Path(destination).read_text()), evidence_level="file-observed")
                    except Exception as error:
                        emit("instrumentation.failed", {"operation": "async_context_read", "error_type": type(error).__name__}, status="capture_gap")
                return result
            os.replace = replace
        else:
            emit("instrumentation.incompatible", {"path": str(runner)}, status="capture_gap")
    patch_processes()
    patch_http()
    original_exec=importlib.machinery.SourceFileLoader.exec_module
    def exec_module(loader,module):
        file=Path(loader.path).resolve()
        expected=CONFIG.get("fingerprints",{}).get(str(file))
        if expected:
            source=file.read_bytes()
            actual=hashlib.sha256(source).hexdigest()
            if actual!=expected:
                emit("instrumentation.incompatible",{"path":str(file),"expected":expected,"actual":actual},status="capture_gap")
                return original_exec(loader,module)
            if file.name in {"bridge.py","remote_hooks.py"} and file.parent==Path(CONFIG["plugin_root"]):
                tree=SelectionObserver().visit(ast.parse(source,filename=str(file)))
                ast.fix_missing_locations(tree)
                module._development_capture=sys.modules[__name__]
                exec(compile(tree,str(file),"exec"),module.__dict__)
            else:
                original_exec(loader,module)
            try:
                patch_module(module,file)
            except Exception as error:
                emit("instrumentation.failed", {"path": str(file), "error_type": type(error).__name__}, status="capture_gap")
            emit("instrumentation.loaded",{"path":str(file),"sha256":actual})
            return
        return original_exec(loader,module)
    importlib.machinery.SourceFileLoader.exec_module=exec_module
    # Modules already imported before explicit test installation also need wrappers.
    for module in tuple(sys.modules.values()):
        name=getattr(module,"__file__",None)
        if name and str(Path(name).resolve()) in CONFIG.get("fingerprints",{}):
            emit("instrumentation.late_import",{"path":name},status="capture_gap")
