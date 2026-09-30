# ABOUTME: Executes installed LifeOS Claude Code hooks at matching Hermes events.
# ABOUTME: Translates hook input and control results without changing LifeOS files.

from __future__ import annotations

import json
import hashlib
import logging
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from contextvars import copy_context
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import ProxyHandler, Request, build_opener
from uuid import uuid4
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


LOG = logging.getLogger(__name__)
TOOL_NAMES = {
    "terminal": "Bash",
    "write_file": "Write",
    "patch": "Edit",
    "read_file": "Read",
    "delegate_task": "Agent",
    "web_search": "WebSearch",
    "web_fetch": "WebFetch",
    "web_extract": "WebFetch",
    "skill_view": "Skill",
    "tool_search": "ToolSearch",
    "clarify": "AskUserQuestion",
}
WEB_CONTENT_TOOLS = frozenset({
    "browser_navigate", "browser_snapshot", "browser_console", "browser_get_images",
    "browser_vision", "browser_cdp", "browser_exec", "browser_dialog",
})
V4A_WRITE_HEADER = re.compile(r"^\*\*\*\s*(Update|Add|Delete)\s+File:\s*(.+)$")
V4A_MOVE_HEADER = re.compile(r"^\*\*\*\s*Move\s+File:\s*(.+?)\s*->\s*(.+)$")
API_ERROR_NAMES = {
    "rate_limit": "rate_limit",
    "upstream_rate_limit": "rate_limit",
    "overloaded": "overloaded",
    "auth": "authentication_failed",
    "auth_permanent": "authentication_failed",
    "billing": "billing_error",
    "model_not_found": "model_not_found",
    "format_error": "invalid_request",
    "server_error": "server_error",
    "timeout": "server_error",
}
if sys.platform == "darwin":
    POLICY_DIRECTORY = Path("/Library/Application Support/ClaudeCode")
elif os.name == "nt":
    POLICY_DIRECTORY = Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "ClaudeCode"
else:
    POLICY_DIRECTORY = Path("/etc/claude-code")


def _native_tool_name(tool_name: str) -> str | None:
    if tool_name.startswith("mcp__"):
        return tool_name
    return TOOL_NAMES.get(tool_name, tool_name or None)


def _hook_matcher_matches(matcher: str, value: str) -> bool:
    if not matcher or matcher == "*":
        return True
    for expression in matcher.split(", "):
        try:
            if re.search(expression, value):
                return True
        except re.error:
            LOG.warning("Invalid LifeOS hook matcher: %r", expression)
    return False


_SIMPLE_READ_ONLY_ECHO = re.compile(r"echo(?: [A-Za-z0-9_./:=+-]+)*\Z")


def _claude_simple_read_only_bash(command: str) -> bool:
    """Recognize only probed commands that Claude runs without PermissionRequest.

    Compound commands, shell expansion, redirects, and unrecognized forms stay
    in the approval path until their permission behavior has been characterized.
    """
    return command == "pwd" or _SIMPLE_READ_ONLY_ECHO.fullmatch(command) is not None


def _bash_permission_rule_matches(rule: Any, command: str) -> bool | None:
    """Match one Bash command against a Claude Code permission rule."""
    if not isinstance(rule, str):
        return None
    if rule in {"Bash", "Bash(*)"}:
        return True
    if not rule.startswith("Bash("):
        return False
    if not rule.endswith(")"):
        return None
    specifier = rule[5:-1]
    if specifier.startswith("run_in_background:"):
        return None
    if "*" in specifier:
        if specifier.endswith(":*"):
            specifier = specifier[:-2] + " *"
        if specifier.endswith(" *") and specifier.count("*") == 1 and command == specifier[:-2]:
            return True
        return re.fullmatch(re.escape(specifier).replace(r"\*", ".*"), command) is not None
    return specifier == command


def _bash_permission_rule_decision(command: str, sources: list[Any], *, checked_file_targets: bool = False) -> str:
    """Apply deny, ask, allow order without granting through unsupported patterns."""
    from .bash_permissions import bash_command_forms

    forms, parsed, allow_safe = bash_command_forms(command, checked_file_targets=checked_file_targets)
    candidates = [(command,)] if not forms else forms
    matches: dict[str, bool] = {"deny": False, "ask": False}
    uncertain: dict[str, bool] = {"deny": False, "ask": False}
    allowed = [False] * len(candidates)
    for settings in sources:
        if not isinstance(settings, dict):
            uncertain["deny"] = True
            continue
        for action in ("deny", "ask", "allow"):
            rules = settings.get(action, [])
            if not isinstance(rules, list):
                uncertain["deny"] = True
                continue
            for rule in rules:
                if action in {"deny", "ask"}:
                    matches_for_rule = [
                        _bash_permission_rule_matches(rule, form)
                        for aliases in candidates for form in aliases
                    ]
                    if not parsed:
                        matches_for_rule.append(_bash_permission_rule_matches(rule, command))
                    if True in matches_for_rule:
                        matches[action] = True
                    elif None in matches_for_rule or (not parsed and isinstance(rule, str) and rule.startswith("Bash")):
                        uncertain[action] = True
                else:
                    for index, aliases in enumerate(candidates):
                        if any(_bash_permission_rule_matches(rule, form) is True for form in aliases):
                            allowed[index] = True
    if matches["deny"]:
        return "deny"
    if uncertain["deny"]:
        return "unknown"
    if matches["ask"]:
        return "ask"
    if uncertain["ask"]:
        return "unknown"
    return "allow" if allow_safe and allowed and all(allowed) else "none"


def _is_native_version_drift(command: str, root: Path) -> bool:
    try:
        tokens = shlex.split(command)
    except ValueError:
        return False
    if len(tokens) == 2 and Path(tokens[0]).name == "bun":
        tokens = tokens[1:]
    if len(tokens) != 1:
        return False
    if tokens[0] in {"$HOME/.claude/hooks/VersionDrift.hook.ts", "${HOME}/.claude/hooks/VersionDrift.hook.ts"}:
        return True
    return Path(tokens[0]).expanduser().resolve() == (root / "hooks/VersionDrift.hook.ts").resolve()


def _is_native_checkpoint(command: str) -> bool:
    try:
        tokens = shlex.split(command)
    except ValueError:
        return False
    if len(tokens) == 2 and Path(tokens[0]).name == "bun":
        tokens = tokens[1:]
    if len(tokens) != 1:
        return False
    path = tokens[0].replace("${HOME}", "~").replace("$HOME", "~")
    return Path(path).parts[-3:] == (".claude", "hooks", "CheckpointPerISC.hook.ts")


def _is_native_task_governance(command: str, root: Path) -> bool:
    if not isinstance(command, str):
        return False
    try:
        tokens = shlex.split(command)
    except ValueError:
        return False
    if len(tokens) == 2 and Path(tokens[0]).name == "bun":
        tokens = tokens[1:]
    if len(tokens) != 1:
        return False
    path = tokens[0].replace("${HOME}", "~").replace("$HOME", "~")
    return Path(path).expanduser().resolve() == (root / "hooks/TaskGovernance.hook.ts").resolve()


def _managed_permission_sources() -> tuple[list[Any], bool]:
    paths = [POLICY_DIRECTORY / "managed-settings.json"]
    dropins = POLICY_DIRECTORY / "managed-settings.d"
    if dropins.is_dir():
        paths.extend(sorted(dropins.glob("*.json")))
    sources = []
    managed_only = False
    for path in paths:
        if not path.exists():
            continue
        try:
            settings = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, ValueError) as error:
            LOG.warning("LifeOS managed permission policy could not be read: %s", error)
            sources.append((None, str(path.parent)))
            continue
        if not isinstance(settings, dict):
            sources.append((None, str(path.parent)))
            continue
        if "allowManagedPermissionRulesOnly" in settings:
            value = settings["allowManagedPermissionRulesOnly"]
            if isinstance(value, bool):
                managed_only = value
            else:
                sources.append((None, str(path.parent)))
        sources.append((settings.get("permissions", {}), str(path.parent)))
    return sources, managed_only


def _hermes_write_requires_approval(path: str, cwd: str) -> bool:
    """Use Hermes's own path classifier so one guarded write gets one human prompt."""
    try:
        from agent.file_safety import is_write_approval_required
        candidate = Path(path).expanduser()
        if not candidate.is_absolute():
            candidate = Path(cwd) / candidate
        return bool(is_write_approval_required(str(candidate)))
    except ImportError:
        return False
    except Exception as error:
        LOG.warning("Hermes file approval classifier unavailable: %s", error)
        return False


def _hook_file_path(path: str, cwd: str, task_id: str = "default", *, entry: bool = False) -> str:
    candidate = path if os.path.isabs(path) or path.startswith("~") else os.path.join(cwd, path)
    try:
        from tools.file_tools_paths import _resolve_entry_for_task, _resolve_path_for_task
    except ImportError:
        expanded = os.path.expanduser(candidate)
        return os.path.join(os.path.realpath(os.path.dirname(expanded)), os.path.basename(expanded)) if entry else os.path.realpath(expanded)
    try:
        resolver = _resolve_entry_for_task if entry else _resolve_path_for_task
        return str(resolver(path, task_id or "default"))
    except Exception as error:
        LOG.warning("Hermes file path resolver unavailable: %s", error)
        return os.path.normpath(candidate)


def _tool_input(name: str, args: dict[str, Any], cwd: str, task_id: str = "default") -> dict[str, Any]:
    translated = dict(args)
    translated.pop("lifeos_remote_file", None)
    if name in {"Write", "Edit", "Read"} and "path" in translated:
        path = translated.pop("path")
        translated["file_path"] = _hook_file_path(path, cwd, task_id) if isinstance(path, str) and path else path
    if name == "Agent" and isinstance(translated.get("tasks"), list):
        tasks = translated["tasks"]
        if tasks:
            translated["prompt"] = tasks[0].get("goal", "")
    if name == "Skill" and "name" in translated:
        translated["skill"] = translated.pop("name")
    if name == "AskUserQuestion" and isinstance(translated.get("question"), str):
        question = {"question": translated["question"]}
        choices = translated.get("choices")
        if isinstance(choices, list):
            question["options"] = [
                {"label": choice, "description": ""} for choice in choices if isinstance(choice, str)
            ]
        question["multiSelect"] = bool(translated.get("multi_select"))
        return {"questions": [question]}
    return translated


def _native_file_input(name: str, native_input: dict[str, Any], task_id: str) -> dict[str, Any]:
    """Give the ISA guard a digest from the filesystem that owns a remote path."""
    if name not in {"Read", "Write", "Edit"}:
        return native_input
    path = native_input.get("file_path")
    if not isinstance(path, str) or not re.fullmatch(r"(?:isa|[^/]+\.isa)\.md", os.path.basename(path), re.I):
        return native_input
    try:
        from tools.file_tools import _file_ops_uses_host_paths, _get_file_ops, _remote_baseline_key
        file_ops = _get_file_ops(task_id or "default")
        if _file_ops_uses_host_paths(file_ops):
            return native_input
        status, digest = file_ops.file_digest(path)
        owner, _ = _remote_baseline_key(file_ops, path)
        return {**native_input, "lifeos_remote_file": {
            "status": status, "sha256": digest, "identity": owner,
        }}
    except (ImportError, OSError, ValueError) as error:
        LOG.warning("Remote ISA digest unavailable: %s", error)
        return native_input


def _web_cache_read(tool_input: dict[str, Any], cwd: str, task_id: str) -> bool:
    path = tool_input.get("file_path")
    if not isinstance(path, str) or not path:
        return False
    try:
        from hermes_constants import get_hermes_dir
        from tools.credential_files import to_agent_visible_cache_path

        host_cache = get_hermes_dir("cache/web", "web_cache")
        visible_cache = to_agent_visible_cache_path(str(host_cache))
        cache_root = _hook_file_path(visible_cache, cwd, task_id)
        return Path(path).is_relative_to(Path(cache_root))
    except (ImportError, OSError, ValueError) as error:
        LOG.debug("Hermes web cache path is unavailable: %s", error)
        return False


def _v4a_edit_inputs(
    patch_text: str, cwd: str, task_id: str = "default",
    applied: dict[str, list[str]] | None = None,
) -> list[dict[str, str]]:
    operations: list[tuple[str, str, list[dict[str, str]]]] = []
    path = None
    operation = None
    path_entry = False
    added = []
    removed = []

    def finish() -> None:
        if path is not None and operation is not None:
            operations.append((operation, path, [{
                "file_path": _hook_file_path(path, cwd, task_id, entry=path_entry),
                "old_string": "\n".join(removed), "new_string": "\n".join(added),
            }]))

    for line in patch_text.splitlines():
        header = V4A_WRITE_HEADER.match(line)
        move = V4A_MOVE_HEADER.match(line)
        if header:
            finish()
            path = header.group(2).strip()
            operation = header.group(1)
            path_entry = header.group(1) == "Delete"
            added = []
            removed = []
        elif move:
            finish()
            path = None
            source, destination = move.group(1).strip(), move.group(2).strip()
            operations.append(("Move", f"{source} -> {destination}", [{
                "file_path": _hook_file_path(move.group(1).strip(), cwd, task_id, entry=True),
                "old_string": "", "new_string": "",
            }, {
                "file_path": _hook_file_path(move.group(2).strip(), cwd, task_id, entry=True),
                "old_string": "", "new_string": "",
            }]))
        elif line.startswith("***"):
            finish()
            path = None
            operation = None
            path_entry = False
            added = []
            removed = []
        elif path is not None and line.startswith("+"):
            added.append(line[1:])
        elif path is not None and line.startswith("-"):
            removed.append(line[1:])
    finish()
    if applied is None:
        return [edit for _, _, edits in operations for edit in edits]
    buckets = {
        "Update": "files_modified", "Move": "files_modified",
        "Add": "files_created", "Delete": "files_deleted",
    }
    applied_counts = {bucket: Counter(paths) for bucket, paths in applied.items()}
    remaining = {bucket: counts.copy() for bucket, counts in applied_counts.items()}
    occurrences = Counter((buckets[kind], label) for kind, label, _ in operations)
    uncertain = set()
    edits = []
    for kind, label, inputs in operations:
        bucket = buckets[kind]
        key = (bucket, label)
        applied_count = applied_counts.get(bucket, Counter())[label]
        if 0 < applied_count < occurrences[key]:
            if key not in uncertain:
                edits.extend({**item, "old_string": "", "new_string": ""} for item in inputs)
                uncertain.add(key)
            continue
        if remaining.get(bucket, Counter())[label] > 0:
            edits.extend(inputs)
            remaining[bucket][label] -= 1
    return edits


def _agent_inputs(args: dict[str, Any]) -> list[dict[str, str]]:
    if args.get("action"):
        return []
    tasks = args.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        tasks = [args]
    inputs = []
    descriptions = set()
    background = args.get("background")
    if not isinstance(background, bool):
        try:
            from agent.delegation_context import is_delegated_child_context
            background = not is_delegated_child_context()
        except ImportError:
            background = True
    for index, task in enumerate(tasks):
        if not isinstance(task, dict) or not isinstance(task.get("goal"), str) or not task["goal"].strip():
            continue
        goal = task["goal"].strip()
        context = task.get("context")
        description = goal[:80]
        if description in descriptions:
            description = f"{goal[:72]} ({index + 1})"
        descriptions.add(description)
        native_input = {
            "subagent_type": "general-purpose",
            "description": description,
            "prompt": goal + (f"\n\n{context}" if isinstance(context, str) and context.strip() else ""),
            "run_in_background": background,
        }
        model = task.get("model") or args.get("model")
        if isinstance(model, str) and model.strip():
            native_input["model"] = model
        inputs.append(native_input)
    return inputs


def _hermes_input(name: str, args: dict[str, Any]) -> dict[str, Any]:
    translated = dict(args)
    if name in {"Write", "Edit", "Read"} and "file_path" in translated:
        translated["path"] = translated.pop("file_path")
    return translated


def _decode_output(stdout: str) -> dict[str, Any] | None:
    text = stdout.strip()
    if not text:
        return None
    try:
        value = json.loads(text)
        return value if isinstance(value, dict) else None
    except json.JSONDecodeError:
        return None


def _specific_output(output: dict[str, Any] | None, event: str) -> dict[str, Any]:
    specific = (output or {}).get("hookSpecificOutput")
    if isinstance(specific, dict) and specific.get("hookEventName") == event:
        return specific
    return {}


def _scope_cwd() -> str:
    try:
        from agent.runtime_cwd import resolve_agent_cwd
    except ImportError:
        return str(Path.cwd())
    return str(resolve_agent_cwd())


def _tool_cwd(tool_name: str, args: dict[str, Any], task_id: str) -> str:
    if tool_name == "terminal" and isinstance(args.get("workdir"), str) and args["workdir"].strip():
        return args["workdir"]
    try:
        from tools.file_tools_paths import _authoritative_workspace_root
    except ImportError:
        workspace = None
    else:
        workspace = _authoritative_workspace_root(task_id or "default")
    if workspace:
        return workspace
    try:
        from tools.terminal_tool import _active_environments, _env_lock, _resolve_container_task_id
        with _env_lock:
            backend = _active_environments.get(_resolve_container_task_id(task_id or "default"))
        backend_cwd = getattr(backend, "cwd", None)
        if isinstance(backend_cwd, str) and os.path.isabs(backend_cwd):
            return backend_cwd
    except (ImportError, AttributeError, OSError, ValueError):
        pass
    return _scope_cwd()


def _hook_process_cwd(payload: dict[str, Any], root: Path) -> str:
    """Run local hook commands from an existing directory while preserving payload cwd."""
    cwd = payload.get("cwd")
    return cwd if isinstance(cwd, str) and Path(cwd).is_dir() else str(root)


def _task_uses_host_paths(task_id: str = "") -> bool:
    """Use the active Hermes backend, or its configured type before it starts."""
    try:
        from tools.terminal_tool import (
            _active_environments, _env_lock, _get_env_config, _resolve_container_task_id,
        )
        with _env_lock:
            environment = _active_environments.get(_resolve_container_task_id(task_id or "default"))
        if environment is not None:
            try:
                from tools.environments.local import LocalEnvironment
            except ImportError:
                pass
            else:
                return isinstance(environment, LocalEnvironment)
        return _get_env_config().get("env_type") == "local"
    except (ImportError, OSError, ValueError) as error:
        LOG.debug("Hermes backend type unavailable: %s", error)
        return True


def _backend_file_path(target: str, cwd: str, task_id: str) -> str | None:
    from .file_permissions import resolve_backend_path

    try:
        from tools.file_tools import _get_file_ops
        file_ops = _get_file_ops(task_id or "default")
        return resolve_backend_path(target, cwd, file_ops.env)
    except Exception as error:
        LOG.warning("Remote file path could not be resolved: %s", error)
        return None


def _prompt_text(message: Any) -> str:
    if isinstance(message, str):
        return message
    if isinstance(message, list):
        return "\n".join(part for item in message if (part := _prompt_text(item)))
    if isinstance(message, dict):
        if message.get("type") not in (None, "text", "input_text"):
            return ""
        content = message.get("text", message.get("content", ""))
        return _prompt_text(content)
    return ""


def _trusted_project(project_dir: Path) -> bool:
    try:
        from agent.skill_utils import is_project_root_trusted
    except ImportError:
        return False
    return is_project_root_trusted(project_dir)


def _project_root_for_cwd(cwd: str) -> Path:
    directory = Path(cwd).resolve()
    try:
        from agent.skill_utils import find_project_root
    except ImportError:
        repository = next(
            (path for path in (directory, *directory.parents)
             if (path / ".git").exists() and path != Path.home()),
            None,
        )
    else:
        repository = find_project_root(directory)
    if repository is not None:
        return repository
    home = Path.home().resolve()
    for path in (directory, *directory.parents):
        if path == home or path.parent == path:
            break
        if (path / ".claude/settings.json").is_file() or (path / ".claude/settings.local.json").is_file():
            return path
    return directory


class HookBridge:
    def __init__(
        self, settings_path: Path, root: Path,
        model_tiers_provider: Callable[[], dict[str, Any]] | None = None,
    ):
        self.settings_path = Path(settings_path)
        self.root = Path(root)
        self.model_tiers_provider = model_tiers_provider
        self.base_environment = dict(os.environ)
        self._apply_settings(json.loads(self.settings_path.read_text()))
        self.started_sessions: set[str] = set()
        self.session_lock = threading.RLock()
        self.session_platforms: dict[str, str] = {}
        self.pending_tool_context: dict[tuple[str, str], list[str]] = {}
        self.task_ids: dict[str, set[str]] = {}
        self.task_counts: dict[str, int] = {}
        self.task_state_loaded: set[str] = set()
        self.task_state_dir = self.root / "LIFEOS/MEMORY/STATE/hermes-task-counts"
        self.task_state_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.pending_tasks: dict[tuple[str, str], tuple[set[str], int]] = {}
        self.api_errors: dict[tuple[str, str], tuple[str, str, str]] = {}
        self.transcript_dir = self.root / "LIFEOS/MEMORY/STATE/hermes-transcripts"
        self.transcript_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.project_dirs = (Path.cwd(),)
        self.session_projects: dict[str, set[Path]] = {}
        self.project_hook_settings: dict[Path, dict[str, Any]] = {}
        self.remote_project_states: dict[tuple[str, str], dict[str, Any]] = {}
        self.remote_session_projects: dict[str, set[tuple[str, str]]] = {}
        self.config_files = self._config_files()
        self.last_config_poll = 0.0
        self.watcher_stop = threading.Event()
        self.watcher: threading.Thread | None = None
        self.watchdog_dir = self.root / "LIFEOS/MEMORY/STATE/hermes-watchdogs"
        self.watchdog_processes: dict[str, str] = {}
        self.watchdog_last_active: dict[str, float] = {}
        self.watchdog_log_offsets: dict[str, int] = {}
        self.watchdog_stop = threading.Event()
        self.watchdog_thread: threading.Thread | None = None

    def _start_config_watcher(self) -> None:
        if "ConfigChange" not in self.hooks and not self.remote_project_states and not any(
            _trusted_project(path.parent.parent) and "ConfigChange" in settings.get("hooks", {})
            for path, settings in self.project_hook_settings.items()
        ):
            return
        with self.session_lock:
            if self.watcher is not None and self.watcher.is_alive() and not self.watcher_stop.is_set():
                return
            self.watcher_stop = threading.Event()
            context = copy_context()
            self.watcher = threading.Thread(
                target=context.run, args=(self._watch_config_changes, self.watcher_stop), daemon=True,
                name="lifeos-config-change",
            )
            self.watcher.start()

    def _watch_config_changes(self, stop: threading.Event) -> None:
        while not stop.wait(1.0):
            try:
                self.poll_config_changes(force=True)
                self.poll_remote_config_changes()
            except Exception as error:
                LOG.error("LifeOS config watcher failed: %s", error)

    def close(self) -> None:
        self.watcher_stop.set()
        if self.watcher is not None and self.watcher is not threading.current_thread():
            self.watcher.join(timeout=2)
        self.watchdog_stop.set()
        if self.watchdog_thread is not None and self.watchdog_thread is not threading.current_thread():
            self.watchdog_thread.join(timeout=3)
        for session_id in tuple(self.watchdog_processes):
            self._stop_agent_watchdog(session_id)

    def _watchdog_paths(self, session_id: str) -> tuple[Path, Path]:
        name = hashlib.sha256(session_id.encode()).hexdigest()[:24]
        return self.watchdog_dir / f"{name}-starts.json", self.watchdog_dir / f"{name}-activity.jsonl"

    def _ensure_agent_watchdog(self, session_id: str) -> bool:
        if not session_id:
            return False
        try:
            from gateway.session_context import async_delivery_supported, get_session_env
            from tools.process_registry import process_registry
            from tools.terminal_tool_background import _stamp_gateway_routing
            if not async_delivery_supported():
                return False
        except ImportError:
            return False
        script = self.root / "LIFEOS/TOOLS/AgentWatchdog.ts"
        bun = shutil.which("bun", path=self.environment.get("PATH"))
        if not script.is_file() or not bun:
            return False
        with self.session_lock:
            existing = self.watchdog_processes.get(session_id)
            if existing:
                process = process_registry.get(existing)
                if process is not None and not process.exited:
                    return True
                self.watchdog_processes.pop(session_id, None)
            owner = f"lifeos-watchdog:{session_id}"
            for old in process_registry.list_sessions(task_id=owner):
                if old.get("status") == "running" and old.get("owner_task_id") == owner:
                    process_registry.kill_process(old["session_id"], source="lifeos-watchdog-replace")
            self.watchdog_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
            starts, activity = self._watchdog_paths(session_id)
            starts.write_text("{}")
            activity.touch()
            starts.chmod(0o600)
            activity.chmod(0o600)
            environment = dict(self.environment)
            environment.update(
                LIFEOS_WATCHDOG_STARTS_FILE=str(starts),
                LIFEOS_WATCHDOG_ACTIVITY_FILE=str(activity),
            )
            command = f"exec {shlex.quote(bun)} {shlex.quote(str(script))}"
            try:
                process = process_registry.spawn_local(
                    command, cwd=str(self.root), task_id=owner, owner_task_id=owner,
                    session_key=get_session_env("HERMES_SESSION_KEY", ""),
                    env_vars=environment, persist_on_release=True,
                )
                process.watch_patterns = ["WATCHDOG:"]
                _stamp_gateway_routing(process, get_session_env)
            except Exception as error:
                LOG.warning("LifeOS agent watchdog could not start: %s", error)
                return False
            self.watchdog_processes[session_id] = process.id
            self.watchdog_last_active[session_id] = time.monotonic()
            if self.watchdog_thread is None or not self.watchdog_thread.is_alive():
                self.watchdog_stop.clear()
                context = copy_context()
                self.watchdog_thread = threading.Thread(
                    target=context.run, args=(self._watch_agent_watchdogs,), daemon=True,
                    name="lifeos-agent-watchdogs",
                )
                self.watchdog_thread.start()
        return True

    def _stop_agent_watchdog(self, session_id: str) -> None:
        with self.session_lock:
            process_id = self.watchdog_processes.pop(session_id, None)
            self.watchdog_last_active.pop(session_id, None)
        if process_id:
            try:
                from tools.process_registry import process_registry
                process_registry.kill_process(process_id, source="lifeos-watchdog", consume_output=True)
            except Exception as error:
                LOG.warning("LifeOS agent watchdog could not stop: %s", error)
        for path in self._watchdog_paths(session_id):
            path.unlink(missing_ok=True)

    def _sync_agent_watchdogs(self, delegations: list[dict[str, Any]]) -> None:
        with self.session_lock:
            sessions = tuple(self.watchdog_processes)
        active_logs: set[str] = set()
        for session_id in sessions:
            active = [
                item for item in delegations
                if item.get("parent_session_id") == session_id and item.get("status") in {"running", "stalling"}
            ]
            starts, activity = self._watchdog_paths(session_id)
            records = {
                str(item["delegation_id"]): {"subagent_type": item.get("role") or "general-purpose"}
                for item in active if item.get("delegation_id")
            }
            temp = starts.with_name(f"{starts.name}.{uuid4().hex}.tmp")
            try:
                with temp.open("w") as stream:
                    json.dump(records, stream)
                temp.chmod(0o600)
                os.replace(temp, starts)
                if active:
                    tool_result = False
                    for item in active:
                        transcripts = item.get("task_transcripts") or {}
                        if isinstance(transcripts, dict):
                            for path in transcripts.values():
                                if isinstance(path, str):
                                    active_logs.add(path)
                                    tool_result = self._watchdog_new_tool_result(path) or tool_result
                    if tool_result:
                        activity.touch()
                    with self.session_lock:
                        self.watchdog_last_active[session_id] = time.monotonic()
                elif time.monotonic() - self.watchdog_last_active.get(session_id, 0) > 30:
                    self._stop_agent_watchdog(session_id)
            finally:
                temp.unlink(missing_ok=True)
        for path in tuple(self.watchdog_log_offsets):
            if path not in active_logs:
                self.watchdog_log_offsets.pop(path, None)

    def _watchdog_new_tool_result(self, path: str) -> bool:
        try:
            with open(path, "rb") as stream:
                stream.seek(self.watchdog_log_offsets.get(path, 0))
                added = stream.read()
                self.watchdog_log_offsets[path] = stream.tell()
        except OSError:
            return False
        return re.search(rb"(?m)^\d{2}:\d{2}:\d{2} result\s+\|", added) is not None

    def _watch_agent_watchdogs(self) -> None:
        while not self.watchdog_stop.wait(2.0):
            with self.session_lock:
                if not self.watchdog_processes:
                    return
            try:
                from tools.async_delegation import list_async_delegations
                self._sync_agent_watchdogs(list_async_delegations())
            except Exception as error:
                LOG.warning("LifeOS agent watchdog sync failed: %s", error)

    def _apply_settings(self, settings: dict[str, Any]) -> None:
        hooks = settings.get("hooks", {})
        if not isinstance(hooks, dict):
            raise ValueError("LifeOS hooks setting must be an object")
        environment = dict(self.base_environment)
        for key, value in settings.get("env", {}).items():
            if isinstance(value, str):
                environment[key] = value.replace("${HOME}", str(Path.home())).replace("$HOME", str(Path.home()))
        environment.setdefault("LIFEOS_DIR", str(self.root / "LIFEOS"))
        environment["PATH"] = (
            f"{Path(__file__).parent / 'bin'}:{Path.home() / '.bun/bin'}:"
            f"{Path.home() / '.local/bin'}:{environment.get('PATH', '')}"
        )
        self.hooks = hooks
        self.user_permission_rules = settings.get("permissions") or {}
        self.environment = environment

    def _config_sources(self) -> dict[Path, str]:
        sources = {
            self.settings_path: "user_settings",
            POLICY_DIRECTORY / "managed-settings.json": "policy_settings",
        }
        for project_dir in self.project_dirs:
            project_settings = project_dir / ".claude"
            sources[project_settings / "settings.json"] = "project_settings"
            sources[project_settings / "settings.local.json"] = "local_settings"
            skills = project_settings / "skills"
            if skills.is_dir():
                sources.update((path, "skills") for path in skills.rglob("*") if path.is_file())
        dropins = POLICY_DIRECTORY / "managed-settings.d"
        if dropins.is_dir():
            sources.update((path, "policy_settings") for path in dropins.glob("*.json") if path.is_file())
        user_skills = self.settings_path.parent / "skills"
        if user_skills.is_dir():
            sources.update((path, "skills") for path in user_skills.rglob("*") if path.is_file())
        return sources

    def _remember_project(self, cwd: str, session_id: str, task_id: str = "") -> None:
        if not _task_uses_host_paths(task_id):
            return
        project_dir = _project_root_for_cwd(cwd)
        with self.session_lock:
            projects = self.session_projects.setdefault(session_id, set())
            if project_dir in projects:
                return
            projects.add(project_dir)
            if project_dir not in self.project_dirs:
                self.project_dirs += (project_dir,)
            for name in ("settings.json", "settings.local.json"):
                path = project_dir / ".claude" / name
                self.project_hook_settings[path] = self._read_project_settings(path)
            for path, fingerprint in self._config_files().items():
                self.config_files.setdefault(path, fingerprint)

    @staticmethod
    def _read_project_settings(path: Path) -> dict[str, Any]:
        try:
            settings = json.loads(path.read_text())
        except (OSError, ValueError) as error:
            if path.exists():
                LOG.warning("LifeOS project settings cannot be loaded from %s: %s", path, error)
            return {}
        return settings if isinstance(settings, dict) and isinstance(settings.get("hooks", {}), dict) else {}

    def _matching_project(self, payload: dict[str, Any], host_paths: bool = True) -> Path | None:
        if not host_paths:
            return None
        cwd = Path(payload.get("cwd") or _scope_cwd()).resolve()
        session_id = payload.get("session_id", "")
        with self.session_lock:
            projects = self.session_projects.get(session_id, set())
            project = next((path for path in sorted(projects, key=lambda value: len(value.parts), reverse=True)
                            if cwd.is_relative_to(path)), None)
            if project is None and "tool_name" not in payload and len(projects) == 1:
                project = next(iter(projects))
        return project if project is not None and _trusted_project(project) else None

    @staticmethod
    def _read_remote_settings(file_ops: Any, path: str) -> tuple[tuple[str, str | None], dict[str, Any]]:
        fingerprint = file_ops.file_digest(path)
        if fingerprint[0] != "file":
            return fingerprint, {}
        result = file_ops.read_file_raw(path)
        if result.error or not isinstance(result.content, str):
            return fingerprint, {}
        if result.file_size is not None and result.file_size > 1024 * 1024:
            LOG.warning("Remote project settings exceed the size limit: %s", path)
            return fingerprint, {}
        try:
            parsed = json.loads(result.content)
        except ValueError as error:
            LOG.warning("Remote project settings cannot be parsed at %s: %s", path, error)
            return fingerprint, {}
        return fingerprint, parsed if isinstance(parsed, dict) and isinstance(parsed.get("hooks", {}), dict) else {}

    @staticmethod
    def _remote_skill_fingerprints(project: Any) -> dict[str, str]:
        skills_root = f"{project.root}/.claude/skills"
        quoted = shlex.quote(skills_root)
        command = (
            f"if [ -d {quoted} ]; then "
            f"while IFS= read -r -d '' path; do "
            "printf '%s\\0' \"$path\"; "
            "if command -v sha256sum >/dev/null 2>&1; then "
            "sha256sum < \"$path\" 2>/dev/null | cut -c1-64 | tr -d '\\n'; "
            "elif command -v shasum >/dev/null 2>&1; then "
            "shasum -a 256 < \"$path\" 2>/dev/null | cut -c1-64 | tr -d '\\n'; "
            "else printf UNAVAILABLE; fi; "
            "printf '\\0'; "
            f"done < <(find {quoted} -type f -print0 2>/dev/null); fi"
        )
        result = project.backend.execute(command, cwd=project.root, timeout=30)
        output = result.get("output", "")
        if result.get("returncode") != 0 or len(output) > 4 * 1024 * 1024:
            raise OSError("remote skill scan failed or exceeded the size limit")
        if not output:
            return {}
        parts = output.split("\0")
        if parts[-1] != "" or len(parts) % 2 != 1:
            raise ValueError("remote skill scan returned incomplete entries")
        paths = {}
        for path, digest in zip(parts[0:-1:2], parts[1:-1:2]):
            if not path.startswith(f"{skills_root}/") or not re.fullmatch(r"[0-9a-f]{64}|UNAVAILABLE", digest):
                raise ValueError("remote skill scan returned an invalid entry")
            paths[path] = digest
        return paths

    def _remote_project_settings(self, payload: dict[str, Any], task_id: str) -> tuple[Any, list[dict[str, Any]]] | None:
        from .remote_hooks import trusted_backend_project
        try:
            from tools.file_tools import _get_file_ops
            file_ops = _get_file_ops(task_id or "default")
            trust_path = Path(self.base_environment.get(
                "LIFEOS_REMOTE_PROJECT_TRUST",
                str(Path.home() / ".config/lifeos-hook-bridge/remote-projects.json"),
            ))
            project = trusted_backend_project(file_ops.env, payload.get("cwd", ""), trust_path)
            if project is None:
                return None
            owner = str(getattr(file_ops.env, "_session_id", id(file_ops.env)))
            key = (owner, project.root)
            with self.session_lock:
                state = self.remote_project_states.get(key)
            if state is None:
                files = {}
                for name in ("settings.json", "settings.local.json"):
                    path = f"{project.root}/.claude/{name}"
                    files[path] = self._read_remote_settings(file_ops, path)
                with self.session_lock:
                    state = self.remote_project_states.setdefault(key, {
                        "project": project, "task_id": task_id, "files": files,
                        "skills": self._remote_skill_fingerprints(project),
                    })
            session_id = payload.get("session_id")
            if isinstance(session_id, str) and session_id:
                with self.session_lock:
                    self.remote_session_projects.setdefault(session_id, set()).add(key)
                self._start_config_watcher()
            return project, [settings for _, settings in state["files"].values()]
        except (ImportError, OSError, ValueError) as error:
            LOG.warning("Remote project settings are unavailable: %s", error)
            return None

    def poll_remote_config_changes(self) -> None:
        try:
            from tools.file_tools import _get_file_ops
        except ImportError:
            return
        with self.session_lock:
            states = tuple(self.remote_project_states.items())
        for key, state in states:
            task_id = state["task_id"]
            try:
                file_ops = _get_file_ops(task_id or "default")
                if file_ops.env is not state["project"].backend:
                    continue
                for path, old in tuple(state["files"].items()):
                    fingerprint = file_ops.file_digest(path)
                    if fingerprint == old[0]:
                        continue
                    new = self._read_remote_settings(file_ops, path)
                    with self.session_lock:
                        sessions = tuple(session_id for session_id, projects in self.remote_session_projects.items()
                                         if key in projects and session_id in self.started_sessions)
                    blocked = False
                    for session_id in sessions:
                        source = "local_settings" if path.endswith("settings.local.json") else "project_settings"
                        payload = self._payload("ConfigChange", session_id, source=source,
                                                file_path=path, config_path=path, cwd=state["project"].root)
                        outcomes = self._run("ConfigChange", payload, source, task_id=task_id)
                        blocked = blocked or any(
                            process.returncode == 2 or (output or {}).get("decision") == "block"
                            for process, output in outcomes
                        )
                    if not blocked:
                        with self.session_lock:
                            state["files"][path] = new
                current_skills = self._remote_skill_fingerprints(state["project"])
                with self.session_lock:
                    old_skills = dict(state["skills"])
                    sessions = tuple(session_id for session_id, projects in self.remote_session_projects.items()
                                     if key in projects and session_id in self.started_sessions)
                changed_skills = sorted(path for path in old_skills.keys() | current_skills.keys()
                                        if old_skills.get(path) != current_skills.get(path))
                for path in changed_skills:
                    blocked = False
                    for session_id in sessions:
                        payload = self._payload("ConfigChange", session_id, source="skills",
                                                file_path=path, config_path=path, cwd=state["project"].root)
                        outcomes = self._run("ConfigChange", payload, "skills", task_id=task_id)
                        blocked = blocked or any(
                            process.returncode == 2 or (output or {}).get("decision") == "block"
                            for process, output in outcomes
                        )
                    if not blocked:
                        with self.session_lock:
                            if path in current_skills:
                                state["skills"][path] = current_skills[path]
                            else:
                                state["skills"].pop(path, None)
            except (OSError, ValueError) as error:
                LOG.warning("Remote project config poll failed: %s", error)

    def _hook_groups(
        self, event: str, payload: dict[str, Any], host_paths: bool = True, task_id: str = "",
    ) -> list[dict[str, Any]]:
        groups = list(self.hooks.get(event, []))
        project = self._matching_project(payload, host_paths)
        if project is not None:
            with self.session_lock:
                for name in ("settings.json", "settings.local.json"):
                    settings = self.project_hook_settings.get(project / ".claude" / name, {})
                    groups.extend(settings.get("hooks", {}).get(event, []))
        if not host_paths:
            remote = self._remote_project_settings(payload, task_id)
            if remote is not None:
                remote_project, settings_files = remote
                for settings in settings_files:
                    project_env = settings.get("env", {})
                    for group in settings.get("hooks", {}).get(event, []):
                        if isinstance(group, dict):
                            groups.append({**group, "_remote_project": remote_project,
                                           "_project_env": project_env if isinstance(project_env, dict) else {}})
        return groups

    def _event_environment(self, payload: dict[str, Any], host_paths: bool = True) -> dict[str, str]:
        environment = dict(self.environment)
        with self.session_lock:
            platform = self.session_platforms.get(payload.get("session_id", ""), "")
        project = self._matching_project(payload, host_paths)
        if project is not None:
            with self.session_lock:
                for name in ("settings.json", "settings.local.json"):
                    settings = self.project_hook_settings.get(project / ".claude" / name, {})
                    for key, value in settings.get("env", {}).items():
                        if isinstance(value, str):
                            environment[key] = value.replace("${HOME}", str(Path.home())).replace("$HOME", str(Path.home()))
        if platform and platform not in {"cli", "tui", "desktop"}:
            environment["LIFEOS_NOTIFICATION_CHANNEL"] = platform
        environment.pop("LIFEOS_CARRIER_OBSERVATION", None)
        if self.model_tiers_provider is not None:
            from .model_tiers import carrier_observation

            mapping = self.model_tiers_provider()
            environment["LIFEOS_MODEL_TIER_MAP"] = json.dumps(mapping)
            if payload.get("hook_event_name") == "UserPromptSubmit":
                observed = self._latest_carrier(payload.get("session_id", ""))
                environment["LIFEOS_CARRIER_OBSERVATION"] = json.dumps(carrier_observation(
                    observed.get("model", ""), observed.get("reasoning_effort", ""),
                    observed.get("provider", ""), mapping,
                ))
            environment["LIFEOS_HERMES_CARRIER_PROBE"] = str(Path(__file__).with_name("carrier_probe.py"))
        from .memory_runtime import MemoryRuntime
        environment.pop("LIFEOS_MEMORY_CONTEXT", None)
        environment.pop("LIFEOS_MEMORY_INTERNAL", None)
        try:
            from hermes_constants import get_hermes_home
        except ImportError:
            pass
        else:
            MemoryRuntime(get_hermes_home() / "lifeos-memory.json").bind_environment(environment, session_id=payload.get("session_id", ""))
        return environment

    def _config_files(self) -> dict[Path, tuple[int, int, int, int, int]]:
        result = {}
        for path in self._config_sources():
            try:
                stat = path.stat()
                result[path] = (
                    stat.st_mtime_ns, stat.st_size, stat.st_ctime_ns, stat.st_dev, stat.st_ino,
                )
            except OSError:
                continue
        return result

    def poll_config_changes(self, force: bool = False) -> None:
        now = time.monotonic()
        with self.session_lock:
            if not force and now - self.last_config_poll < 1.0:
                return
            self.last_config_poll = now
            current = self._config_files()
            changed = set(current) ^ set(self.config_files)
            changed.update(path for path in current.keys() & self.config_files.keys() if current[path] != self.config_files[path])
            self.config_files = current
            sessions = tuple(self.started_sessions)
            session_projects = {key: set(value) for key, value in self.session_projects.items()}
        for path in sorted(changed):
            source = self._config_sources().get(path, "skills")
            blocked = False
            for session_id in sessions:
                project = next(
                    (candidate for candidate in sorted(
                        session_projects.get(session_id, ()), key=lambda value: len(value.parts), reverse=True,
                    ) if path.is_relative_to(candidate / ".claude")),
                    None,
                )
                if source in {"project_settings", "local_settings"} or (
                    source == "skills" and not path.is_relative_to(self.settings_path.parent / "skills")
                ):
                    if project is None:
                        continue
                outcomes = self._run("ConfigChange", self._payload(
                    "ConfigChange", session_id, source=source, file_path=str(path), config_path=str(path),
                    **({"cwd": str(project)} if project is not None else {}),
                ), source)
                blocked = blocked or any(
                    process.returncode == 2 or (output or {}).get("decision") == "block"
                    for process, output in outcomes
                )
            if path == self.settings_path and not blocked:
                try:
                    self._apply_settings(json.loads(self.settings_path.read_text()))
                except (OSError, ValueError, TypeError) as error:
                    LOG.warning("LifeOS settings change cannot be loaded: %s", error)
            elif source in {"project_settings", "local_settings"} and not blocked:
                with self.session_lock:
                    self.project_hook_settings[path] = self._read_project_settings(path)
                self._start_config_watcher()

    def transcript_path(self, session_id: str) -> Path:
        name = re.sub(r"[^A-Za-z0-9._-]", "_", session_id or "default")
        return self.transcript_dir / f"{name}.jsonl"

    def _append_transcript(
        self, session_id: str, kind: str, content: Any, model: str = "", reasoning_effort: str = "", provider: str = "",
    ) -> None:
        row = {
            "type": kind,
            "sessionId": session_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "message": {"role": kind, "content": content},
        }
        if kind == "assistant" and model:
            row["message"]["model"] = model
        if kind == "assistant" and reasoning_effort:
            row["message"]["reasoning_effort"] = reasoning_effort
        if kind == "assistant" and provider:
            row["message"]["provider"] = provider
        path = self.transcript_path(session_id)
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        with os.fdopen(descriptor, "w") as stream:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")

    def _latest_carrier(self, session_id: str) -> dict[str, str]:
        try:
            with self.transcript_path(session_id).open("rb") as stream:
                stream.seek(0, os.SEEK_END)
                stream.seek(max(0, stream.tell() - 256 * 1024))
                lines = stream.read().decode("utf-8", errors="replace").splitlines()
            for line in reversed(lines):
                try:
                    row = json.loads(line)
                    message = row.get("message", {})
                    if row.get("type") == "assistant" and row.get("isSidechain") is not True and message.get("model"):
                        return {key: message[key] for key in ("model", "reasoning_effort", "provider")
                                if isinstance(message.get(key), str)}
                except (ValueError, AttributeError, TypeError):
                    continue
        except OSError:
            pass
        return {}

    def _run(
        self, event: str, payload: dict[str, Any], tool_name: str = "", matcher_alias: str = "",
        alias_input: dict[str, Any] | None = None, task_id: str = "", skip_checkpoint: bool = False,
    ) -> list[tuple[subprocess.CompletedProcess[str], dict[str, Any] | None]]:
        jobs = []
        host_paths = _task_uses_host_paths(task_id)
        environment = self._event_environment(payload, host_paths)
        process_cwd = _hook_process_cwd(payload, self.root) if host_paths else str(self.root)
        for group in self._hook_groups(event, payload, host_paths, task_id):
            matcher = group.get("matcher", "")
            native_match = _hook_matcher_matches(matcher, tool_name)
            alias_match = bool(matcher and matcher_alias and _hook_matcher_matches(matcher, matcher_alias))
            if not native_match and not alias_match:
                continue
            group_payload = payload if native_match else {
                **payload, "tool_name": matcher_alias,
                **({"tool_input": alias_input} if alias_input is not None else {}),
            }
            remote_project = group.get("_remote_project")
            project_env = group.get("_project_env", {})
            values = {key: value for key, value in project_env.items()
                      if isinstance(key, str) and isinstance(value, str)}
            if "LIFEOS_NOTIFICATION_CHANNEL" in environment:
                values["LIFEOS_NOTIFICATION_CHANNEL"] = environment["LIFEOS_NOTIFICATION_CHANNEL"]
            for hook in group.get("hooks", []):
                if hook.get("type") == "http":
                    if remote_project is not None:
                        url = hook.get("url", "")
                        parsed = urlparse(url)
                        if parsed.scheme != "http" or parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
                            LOG.warning("LifeOS remote HTTP hook must use backend loopback: %s", url)
                            continue
                        from .remote_hooks import run_project_hook
                        timeout = max(1, min(int(hook.get("timeout", 5)), 30))
                        command = (
                            f"curl --noproxy '*' --silent --show-error --fail --max-time {timeout} "
                            f"--header 'Content-Type: application/json' --data-binary @- {shlex.quote(url)}"
                        )
                        if hook.get("async"):
                            jobs.append((self._run_remote_async, (
                                remote_project, command, group_payload, timeout, values,
                            ), True))
                        else:
                            jobs.append((run_project_hook, (
                                remote_project.backend, command, group_payload,
                                remote_project.cwd, timeout, values,
                            ), False))
                        continue
                    jobs.append((self._run_http, (hook, group_payload), False))
                    continue
                if hook.get("type") != "command":
                    LOG.warning("LifeOS %s hook type %r is not executable by this bridge", event, hook.get("type"))
                    continue
                command = hook.get("command")
                if not isinstance(command, str) or not command.strip():
                    continue
                if skip_checkpoint and _is_native_checkpoint(command):
                    continue
                hook_environment = environment
                if event == "UserPromptSubmit" and remote_project is None and _is_native_version_drift(command, self.root):
                    from .version_drift import default_baseline_path
                    hook_environment = dict(environment)
                    hook_environment["LIFEOS_VERSION_DRIFT_ROOT"] = str(self.root)
                    hook_environment.setdefault("LIFEOS_VERSION_DRIFT_BASELINE", str(default_baseline_path()))
                    system_path = os.pathsep.join(
                        path for path in environment.get("PATH", "").split(os.pathsep)
                        if Path(path).resolve() != (Path(__file__).parent / "bin").resolve()
                    )
                    system_git = shutil.which("git", path=system_path)
                    if system_git:
                        hook_environment["LIFEOS_VERSION_DRIFT_SYSTEM_GIT"] = system_git
                if remote_project is not None:
                    from .remote_hooks import run_project_hook
                    timeout = max(1, min(int(hook.get("timeout", 60)), 300))
                    if hook.get("async"):
                        jobs.append((self._run_remote_async, (
                            remote_project, command, group_payload, timeout, values,
                        ), True))
                        continue
                    jobs.append((run_project_hook, (
                        remote_project.backend, command, group_payload,
                        remote_project.cwd, timeout, values,
                    ), False))
                    continue
                if hook.get("async"):
                    jobs.append((self._run_async, (command, group_payload, hook_environment, process_cwd), True))
                    continue
                timeout = max(1, min(int(hook.get("timeout", 60)), 300))
                jobs.append((self._run_command, (event, command, group_payload, timeout, hook_environment, process_cwd), False))
        outcomes = []
        if not jobs:
            return outcomes
        sync_hooks = []
        for callback, arguments, asynchronous in jobs:
            if asynchronous:
                callback(*arguments)
            else:
                sync_hooks.append((callback, arguments))
        if not sync_hooks:
            return outcomes
        with ThreadPoolExecutor(max_workers=min(len(sync_hooks), 32)) as executor:
            futures = [executor.submit(callback, *arguments) for callback, arguments in sync_hooks]
            for future in futures:
                try:
                    process = future.result()
                except Exception as error:
                    LOG.error("LifeOS %s hook failed: %s", event, error)
                    continue
                if process is not None:
                    outcomes.append((process, _decode_output(process.stdout)))
        return outcomes

    def _run_command(
        self, event: str, command: str, payload: dict[str, Any], timeout: int,
        environment: dict[str, str], process_cwd: str,
    ) -> subprocess.CompletedProcess[str] | None:
        try:
            process = subprocess.run(
                ["/bin/bash", "-c", command], input=json.dumps(payload), text=True,
                capture_output=True, timeout=timeout, cwd=process_cwd,
                env=environment, check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            LOG.error("LifeOS %s hook failed to execute: %s", event, error)
            return None
        if process.returncode not in (0, 2):
            LOG.warning("LifeOS %s hook exited %s: %s", event, process.returncode, process.stderr[:400])
        return process

    @staticmethod
    def _run_http(hook: dict[str, Any], payload: dict[str, Any]) -> subprocess.CompletedProcess[str] | None:
        url = hook.get("url", "")
        parsed = urlparse(url)
        if parsed.scheme != "http" or parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
            LOG.warning("LifeOS HTTP hook must use local HTTP: %s", url)
            return None
        request = Request(url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"}, method="POST")
        try:
            with build_opener(ProxyHandler({})).open(request, timeout=max(1, min(int(hook.get("timeout", 5)), 30))) as response:
                body = response.read(65536).decode("utf-8", errors="replace")
            return subprocess.CompletedProcess(args=[url], returncode=0, stdout=body, stderr="")
        except (HTTPError, URLError, OSError) as error:
            LOG.warning("LifeOS HTTP hook unavailable: %s", error)
            return None

    def _run_async(
        self, command: str, payload: dict[str, Any], environment: dict[str, str], process_cwd: str,
    ) -> None:
        spool_path = None
        try:
            session_id = payload.get("session_id", "")
            result_path = None
            if session_id:
                result_dir = self._async_result_dir(session_id)
                result_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
                result_path = result_dir / f"{uuid4().hex}.json"
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=self.transcript_dir,
                prefix="async-hook-", suffix=".json", delete=False,
            ) as spool:
                spool_path = Path(spool.name)
                json.dump({"command": command, "payload": payload,
                           "cwd": process_cwd, "environment": environment,
                           "result_path": str(result_path) if result_path else None}, spool)
            self._start_async_runner(spool_path, process_cwd, environment)
        except (OSError, subprocess.TimeoutExpired) as error:
            LOG.error("LifeOS async hook failed to start: %s", error)
            if spool_path is not None:
                spool_path.unlink(missing_ok=True)

    def _run_remote_async(
        self, project: Any, command: str, payload: dict[str, Any], timeout: int,
        environment: dict[str, str],
    ) -> None:
        spool_path = None
        try:
            import inspect

            session_id = payload.get("session_id", "")
            result_path = None
            if session_id:
                result_dir = self._async_result_dir(session_id)
                result_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
                result_path = result_dir / f"{uuid4().hex}.json"
            backend = project.backend
            from tools.environments.ssh import SSHEnvironment
            if isinstance(backend, SSHEnvironment):
                remote = {"type": "ssh", "host": backend.host, "user": backend.user,
                          "port": backend.port, "key_path": backend.key_path}
            else:
                remote = {"type": "docker", "executable": backend._docker_exe,
                          "container_id": backend._container_id}
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=self.transcript_dir,
                prefix="async-remote-hook-", suffix=".json", delete=False,
            ) as spool:
                spool_path = Path(spool.name)
                json.dump({
                    "command": command, "payload": payload, "cwd": project.cwd,
                    "environment": environment, "timeout": timeout,
                    "result_path": str(result_path) if result_path else None,
                    "remote": remote,
                    "source_root": str(Path(inspect.getfile(type(backend))).resolve().parents[2]),
                    "plugin_root": str(Path(__file__).parent),
                    "python_paths": [path for path in sys.path if path and os.path.isabs(path)],
                }, spool)
            self._start_async_runner(spool_path, str(self.root), self.environment)
        except (OSError, subprocess.TimeoutExpired, AttributeError, TypeError) as error:
            LOG.error("LifeOS remote async hook failed to start: %s", error)
            if spool_path is not None:
                spool_path.unlink(missing_ok=True)

    @staticmethod
    def _start_async_runner(spool_path: Path, process_cwd: str, environment: dict[str, str]) -> None:
        runner = [sys.executable, str(Path(__file__).parent / "bin/hook_runner.py"), str(spool_path)]
        if shutil.which("systemd-run") and os.environ.get("XDG_RUNTIME_DIR"):
            unit = f"lifeos-hook-{uuid4().hex}"
            service = subprocess.run(
                ["systemd-run", "--user", "--collect", "--service-type=exec", f"--unit={unit}", *runner],
                capture_output=True, text=True, timeout=10, check=False,
            )
            if service.returncode == 0:
                return
            LOG.warning("LifeOS async hook service unavailable: %s", service.stderr.strip()[:400])
        process = subprocess.Popen(
            runner,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=process_cwd,
            env=environment,
            start_new_session=True,
            close_fds=True,
        )
        threading.Thread(target=process.wait, daemon=True, name="lifeos-async-hook-reap").start()

    def _async_result_dir(self, session_id: str) -> Path:
        name = hashlib.sha256(session_id.encode()).hexdigest()[:24]
        return self.transcript_dir / "async-results" / name

    def _drain_async_context(self, session_id: str) -> list[str]:
        result_dir = self._async_result_dir(session_id)
        if not result_dir.is_dir():
            return []
        context = []
        def modified(path: Path) -> int:
            try:
                return path.stat().st_mtime_ns
            except OSError:
                return 0

        for path in sorted(result_dir.glob("*.json"), key=modified):
            claimed = path.with_suffix(f".{uuid4().hex}.claim")
            try:
                os.replace(path, claimed)
                result = json.loads(claimed.read_text())
                if not isinstance(result, dict):
                    continue
                if result.get("session_id") != session_id:
                    continue
                for key in ("additionalContext", "systemMessage"):
                    value = result.get(key)
                    if isinstance(value, str) and value.strip():
                        context.append(value.strip())
            except (OSError, ValueError, TypeError) as error:
                LOG.warning("LifeOS async hook result could not be read: %s", error)
            finally:
                claimed.unlink(missing_ok=True)
        return context

    def _payload(self, event: str, session_id: str, **fields: Any) -> dict[str, Any]:
        child_fields = {}
        if event in {"PreToolUse", "PostToolUse", "PostToolUseFailure", "PermissionRequest", "TaskCreated"}:
            try:
                from agent.delegation_context import is_delegated_child_process_context
            except ImportError:
                pass
            else:
                if is_delegated_child_process_context():
                    child_fields = {"agent_id": session_id or "hermes-child", "agent_type": "general-purpose"}
        return {
            "hook_event_name": event,
            "session_id": session_id,
            "transcript_path": str(self.transcript_path(session_id)),
            "cwd": _scope_cwd(),
            **child_fields,
            **fields,
        }

    def _permission_sources(
        self, payload: dict[str, Any], task_id: str, host_paths: bool,
    ) -> list[tuple[Any, str]]:
        project = self._matching_project(payload, host_paths)
        project_permissions = [
            (self.project_hook_settings.get(project / ".claude" / name, {}).get("permissions", {}), str(project))
            for name in ("settings.json", "settings.local.json")
        ] if project is not None else []
        if not host_paths:
            remote = self._remote_project_settings(payload, task_id)
            if remote is not None:
                project_permissions.extend(
                    (settings.get("permissions", {}), str(remote[0].root)) for settings in remote[1]
                )
        managed_permissions, managed_only = _managed_permission_sources()
        local_permissions = [] if managed_only else [
            (self.user_permission_rules, str(self.settings_path.parent)), *project_permissions,
        ]
        return [*local_permissions, *managed_permissions]

    def command_approval(
        self, command: str, session_key: str = "", cwd: str = "", task_id: str = "",
        approval_bypass: bool = False, **_: Any,
    ) -> dict[str, str] | None:
        cwd = cwd or _tool_cwd("terminal", {}, task_id)
        self._remember_project(cwd, session_key, task_id)
        self.poll_config_changes(force=True)
        payload = self._payload(
            "PermissionRequest", session_key, tool_name="Bash", tool_input={"command": command}, cwd=cwd,
        )
        host_paths = _task_uses_host_paths(task_id)
        permission_sources = self._permission_sources(payload, task_id, host_paths)
        from .bash_permissions import bash_file_targets
        from .file_permissions import file_target_decision

        targets, targets_certain = bash_file_targets(command)
        file_decision = "unknown" if not targets_certain else "allow"
        for operation, target in targets:
            resolved = None if host_paths else _backend_file_path(target, cwd, task_id)
            decision = file_target_decision(
                target, operation, cwd, permission_sources,
                host_paths=host_paths, resolved_path=resolved,
            )
            if decision == "deny":
                return {"action": "deny"}
            if decision in {"ask", "unknown", "invalid_policy"} or (
                operation == "write" and host_paths and _hermes_write_requires_approval(target, cwd)
            ):
                file_decision = "unknown"
        rule_decision = _bash_permission_rule_decision(
            command, [settings for settings, _ in permission_sources],
            checked_file_targets=file_decision == "allow",
        )
        if rule_decision == "deny":
            return {"action": "deny"}
        if approval_bypass:
            return None
        if file_decision == "unknown":
            rule_decision = "unknown"
        if host_paths and rule_decision == "allow":
            return None
        if host_paths and rule_decision == "none" and _claude_simple_read_only_bash(command):
            return None
        groups = self._hook_groups("PermissionRequest", payload, host_paths, task_id)
        if not any(group.get("hooks") and _hook_matcher_matches(group.get("matcher", ""), "Bash")
                   for group in groups):
            return {"action": "review"} if rule_decision in {"ask", "unknown"} else None
        granted = False
        denied = False
        invalid_replacement = False
        replacement = None
        for process, output in self._run("PermissionRequest", payload, "Bash", task_id=task_id):
            specific = _specific_output(output, "PermissionRequest")
            decision = specific.get("decision") or {}
            if decision.get("behavior") == "deny" or process.returncode == 2:
                denied = True
            if specific.get("hookEventName") == "PermissionRequest" and decision.get("behavior") == "allow":
                granted = True
                updated = decision.get("updatedInput")
                if updated is not None:
                    if not isinstance(updated, dict) or not isinstance(updated.get("command"), str):
                        invalid_replacement = True
                    elif replacement is not None and replacement != updated["command"]:
                        invalid_replacement = True
                    else:
                        replacement = updated["command"]
        if denied:
            return {"action": "deny"}
        if granted:
            if invalid_replacement:
                return {"action": "review"}
            if replacement is not None and replacement != command:
                return {"action": "rewrite", "command": replacement}
            return {"action": "review"} if rule_decision in {"ask", "unknown"} else {"action": "allow"}
        return {"action": "review"}

    def _mcp_permission_verdict(
        self, tool_name: str, args: dict[str, Any], session_id: str, cwd: str, task_id: str = "",
    ) -> dict[str, Any] | None:
        groups = self._hook_groups(
            "PermissionRequest", self._payload("PermissionRequest", session_id, cwd=cwd, tool_name=tool_name),
            _task_uses_host_paths(task_id), task_id,
        )
        if not any(_hook_matcher_matches(group.get("matcher", ""), tool_name) for group in groups):
            return None
        payload = self._payload("PermissionRequest", session_id, tool_name=tool_name, tool_input=args, cwd=cwd)
        outcomes = self._run("PermissionRequest", payload, tool_name, task_id=task_id)
        granted = False
        replacement = None
        for process, output in outcomes:
            specific = _specific_output(output, "PermissionRequest")
            decision = specific.get("decision") or {}
            if decision.get("behavior") == "deny" or process.returncode == 2:
                message = decision.get("reason") or process.stderr.strip() or "LifeOS denied the MCP call"
                return {"action": "block", "message": str(message)[:2000]}
            if specific.get("hookEventName") == "PermissionRequest" and decision.get("behavior") == "allow":
                granted = True
                updated = decision.get("updatedInput")
                if updated is not None:
                    if not isinstance(updated, dict):
                        return {"action": "block", "message": "LifeOS supplied an invalid MCP replacement"}
                    if replacement is not None and replacement != updated:
                        return {"action": "block", "message": "LifeOS supplied conflicting MCP replacements"}
                    replacement = updated
        if granted:
            if replacement is not None and replacement != args:
                return {"action": "modify", "args": replacement}
            return None
        fingerprint = hashlib.sha256(json.dumps(args, sort_keys=True).encode()).hexdigest()[:16]
        return {
            "action": "approve",
            "message": f"LifeOS requests review of MCP call {tool_name}",
            "rule_key": f"lifeos-mcp:{tool_name}:{fingerprint}",
        }

    def _file_permission_verdict(
        self, native_name: str, native_inputs: list[dict[str, Any]], session_id: str, cwd: str,
        task_id: str = "",
    ) -> dict[str, Any] | None:
        groups = self._hook_groups(
            "PermissionRequest", self._payload("PermissionRequest", session_id, cwd=cwd, tool_name=native_name),
            _task_uses_host_paths(task_id), task_id,
        )
        if not any(_hook_matcher_matches(group.get("matcher", ""), native_name) for group in groups):
            return None
        review_paths = []
        replacement = None
        for native_input in native_inputs:
            payload = self._payload(
                "PermissionRequest", session_id, tool_name=native_name, tool_input=native_input, cwd=cwd,
            )
            outcomes = self._run("PermissionRequest", payload, native_name, task_id=task_id)
            granted = False
            for process, output in outcomes:
                specific = _specific_output(output, "PermissionRequest")
                decision = specific.get("decision") or {}
                if decision.get("behavior") == "deny" or process.returncode == 2:
                    message = decision.get("reason") or process.stderr.strip() or "LifeOS denied the file change"
                    return {"action": "block", "message": str(message)[:2000]}
                if specific.get("hookEventName") == "PermissionRequest" and decision.get("behavior") == "allow":
                    granted = True
                    updated = decision.get("updatedInput")
                    if updated is not None:
                        if not isinstance(updated, dict) or not isinstance(updated.get("file_path"), str) or not updated["file_path"]:
                            return {"action": "block", "message": "LifeOS supplied an invalid file replacement"}
                        if native_name == "Write" and not isinstance(updated.get("content"), str):
                            return {"action": "block", "message": "LifeOS supplied an invalid Write replacement"}
                        if replacement is not None and replacement != updated:
                            return {"action": "block", "message": "LifeOS supplied conflicting file replacements"}
                        replacement = updated
            if not granted:
                review_paths.append(str(native_input.get("file_path", "unknown path")))
        if replacement is not None:
            if len(native_inputs) != 1:
                return {"action": "block", "message": "LifeOS cannot replace a multi-file patch input"}
            return {"action": "modify", "args": _hermes_input(native_name, replacement)}
        if not review_paths:
            return None
        if any(_hermes_write_requires_approval(path, cwd) for path in review_paths):
            return None
        fingerprint = hashlib.sha256(json.dumps(native_inputs, sort_keys=True).encode()).hexdigest()[:16]
        return {
            "action": "approve",
            "message": f"LifeOS requests review of {native_name} for {', '.join(review_paths)}",
            "rule_key": f"lifeos-file:{native_name}:{fingerprint}",
        }

    def pre_tool_call(
        self, tool_name: str, args: dict[str, Any], session_id: str = "", tool_call_id: str = "",
        task_id: str = "", **_: Any,
    ) -> dict[str, Any] | None:
        cwd = _tool_cwd(tool_name, args, task_id)
        self._remember_project(cwd, session_id, task_id)
        if tool_name == "todo_list" and self._hook_groups(
            "TaskCreated", self._payload("TaskCreated", session_id, cwd=cwd, tool_name=tool_name),
            _task_uses_host_paths(task_id), task_id,
        ):
            task_verdict = self._task_created_verdict(args, session_id, tool_call_id or tool_name, task_id)
            if task_verdict:
                return task_verdict
        if tool_name == "kanban_create" and self._hook_groups(
            "TaskCreated", self._payload("TaskCreated", session_id, cwd=cwd, tool_name=tool_name),
            _task_uses_host_paths(task_id), task_id,
        ):
            task_verdict = self._kanban_task_verdict(args, session_id, tool_call_id or tool_name, task_id)
            if task_verdict:
                return task_verdict
        native_name = _native_tool_name(tool_name)
        if native_name is None:
            return None
        v4a = tool_name == "patch" and args.get("mode") == "patch" and isinstance(args.get("patch"), str)
        native_inputs = (
            _v4a_edit_inputs(args["patch"], cwd, task_id) if v4a else
            _agent_inputs(args) if native_name == "Agent" else [_tool_input(native_name, args, cwd, task_id)]
        )
        updated_args = None
        extra_context = []
        review_requests = []
        for native_input in native_inputs:
            hook_input = _native_file_input(native_name, native_input, task_id)
            payload = self._payload("PreToolUse", session_id, tool_name=native_name, tool_input=hook_input, cwd=cwd)
            code = args.get("code") if tool_name == "execute_code" else None
            for process, output in self._run(
                "PreToolUse", payload, native_name,
                matcher_alias="Bash" if isinstance(code, str) and code else "",
                alias_input={"command": code} if isinstance(code, str) and code else None,
                task_id=task_id,
            ):
                specific = _specific_output(output, "PreToolUse")
                decision = specific.get("permissionDecision")
                if process.returncode == 2 or decision in {"deny", "block"}:
                    message = specific.get("permissionDecisionReason") or process.stderr.strip() or "Blocked by a LifeOS hook"
                    return {"action": "block", "message": str(message)[:2000]}
                if decision == "ask":
                    reason = specific.get("permissionDecisionReason") or "LifeOS hook requests review"
                    review_requests.append(str(reason)[:2000])
                updated = specific.get("updatedInput")
                if isinstance(updated, dict) and not v4a and not (
                    tool_name == "execute_code" and "command" in updated
                ):
                    updated_args = _hermes_input(native_name, updated)
                context = specific.get("additionalContext")
                if isinstance(context, str) and context.strip():
                    if native_name == "Agent" and "WATCHDOG:" in context and "Monitor(" in context:
                        watching = self._ensure_agent_watchdog(session_id)
                        context = (
                            "LifeOS watchdog is monitoring this Hermes background agent. "
                            "Alerts will reach this session through Hermes process notifications."
                            if watching else
                            "LifeOS watchdog is unavailable here. Hermes delegation stall monitoring still applies."
                        )
                    extra_context.append(context.strip())
        if extra_context:
            with self.session_lock:
                key = (session_id, tool_call_id or tool_name)
                self.pending_tool_context[key] = extra_context
                if len(self.pending_tool_context) > 1024:
                    self.pending_tool_context.pop(next(iter(self.pending_tool_context)))

        def pretool_review() -> dict[str, Any] | None:
            if not review_requests:
                return None
            reviewed_args = updated_args or args
            fingerprint = hashlib.sha256(json.dumps({
                "tool": tool_name, "args": reviewed_args, "cwd": cwd, "task_id": task_id,
            }, sort_keys=True).encode()).hexdigest()[:16]
            verdict = {
                "action": "approve",
                "message": "\n".join(dict.fromkeys(review_requests))[:2000],
                "rule_key": f"lifeos-pretool:{native_name}:{fingerprint}",
            }
            if updated_args is not None:
                verdict["args"] = updated_args
            return verdict

        if tool_name.startswith("mcp__"):
            verdict = self._mcp_permission_verdict(tool_name, updated_args or args, session_id, cwd, task_id)
            if verdict:
                if verdict["action"] == "block":
                    return verdict
                if verdict["action"] == "modify":
                    updated_args = verdict["args"]
                    return pretool_review() if review_requests else verdict
                if review_requests:
                    return pretool_review()
                if verdict["action"] == "approve" and updated_args is not None:
                    verdict["args"] = updated_args
                return verdict
        file_rule_review_paths = []
        if native_name in {"Read", "Write", "Edit"}:
            permission_inputs = native_inputs if v4a else [_tool_input(native_name, updated_args or args, cwd, task_id)]
            self.poll_config_changes(force=True)
            host_paths = _task_uses_host_paths(task_id)
            permission_payload = self._payload(
                "PermissionRequest", session_id, cwd=cwd, tool_name=native_name,
            )
            permission_sources = self._permission_sources(permission_payload, task_id, host_paths)
            from .file_permissions import file_target_decision

            for native_input in permission_inputs:
                path = native_input.get("file_path")
                if not isinstance(path, str) or not path:
                    continue
                operation = "read" if native_name == "Read" else "write"
                resolved = None if host_paths else _backend_file_path(path, cwd, task_id)
                decision = file_target_decision(
                    path, operation, cwd, permission_sources,
                    host_paths=host_paths, resolved_path=resolved,
                )
                if decision == "deny":
                    return {"action": "block", "message": f"LifeOS file permission rule denied {native_name}: {path}"}
                if decision in {"ask", "invalid_policy"} or (decision == "unknown" and not host_paths):
                    file_rule_review_paths.append(path)
        if native_name in {"Write", "Edit"}:
            verdict = self._file_permission_verdict(native_name, permission_inputs, session_id, cwd, task_id)
            if verdict:
                if verdict["action"] == "block":
                    return verdict
                if verdict["action"] == "modify":
                    updated_args = verdict["args"]
                    file_rule_review_paths = []
                    final_input = _tool_input(native_name, updated_args, cwd, task_id)
                    path = final_input.get("file_path")
                    if not isinstance(path, str) or not path:
                        return {"action": "block", "message": "LifeOS supplied an invalid file path"}
                    resolved = None if host_paths else _backend_file_path(path, cwd, task_id)
                    decision = file_target_decision(
                        path, "write", cwd, permission_sources,
                        host_paths=host_paths, resolved_path=resolved,
                    )
                    if decision == "deny":
                        return {"action": "block", "message": f"LifeOS file permission rule denied {native_name}: {path}"}
                    if decision in {"ask", "unknown", "invalid_policy"}:
                        file_rule_review_paths.append(path)
                    if review_requests:
                        return pretool_review()
                    if file_rule_review_paths:
                        fingerprint = hashlib.sha256(json.dumps(updated_args, sort_keys=True).encode()).hexdigest()[:16]
                        return {
                            "action": "approve", "args": updated_args,
                            "message": f"LifeOS file rule requests review of {native_name} for {path}",
                            "rule_key": f"lifeos-file-rule:{native_name}:{fingerprint}",
                        }
                    return verdict
                if review_requests:
                    return pretool_review()
                if verdict["action"] == "approve" and updated_args is not None:
                    verdict["args"] = updated_args
                return verdict
        if file_rule_review_paths:
            if review_requests:
                return pretool_review()
            if native_name in {"Write", "Edit"} and any(
                _hermes_write_requires_approval(path, cwd) for path in file_rule_review_paths
            ):
                return {"action": "modify", "args": updated_args} if updated_args is not None else None
            fingerprint = hashlib.sha256(json.dumps(permission_inputs, sort_keys=True).encode()).hexdigest()[:16]
            verdict = {
                "action": "approve",
                "message": f"LifeOS file rule requests review of {native_name} for {', '.join(file_rule_review_paths)}",
                "rule_key": f"lifeos-file-rule:{native_name}:{fingerprint}",
            }
            if updated_args is not None:
                verdict["args"] = updated_args
            return verdict
        if tool_name == "delegate_task" and self.model_tiers_provider is not None:
            from .model_tiers import route_delegate_args
            current = updated_args or args
            try:
                routed = route_delegate_args(current, self.model_tiers_provider())
            except ValueError as error:
                return {"action": "block", "message": str(error)}
            if routed != current:
                updated_args = routed
        if review_requests:
            return pretool_review()
        return {"action": "modify", "args": updated_args} if updated_args is not None else None

    def _reserved_task_count(self, session_id: str) -> int:
        return sum(count for (owner, _), (_, count) in self.pending_tasks.items() if owner == session_id)

    def _task_state_path(self, session_id: str) -> Path:
        name = hashlib.sha256(session_id.encode()).hexdigest()
        return self.task_state_dir / f"{name}.json"

    def _load_task_state(self, session_id: str) -> None:
        if session_id in self.task_state_loaded:
            return
        self.task_state_loaded.add(session_id)
        path = self._task_state_path(session_id)
        if not path.exists():
            return
        try:
            state = json.loads(path.read_text())
            count = state["count"]
            ids = state["ids"]
            if not isinstance(count, int) or count < 0 or not isinstance(ids, list) or not all(isinstance(item, str) for item in ids):
                raise ValueError("invalid task state")
            self.task_counts[session_id] = count
            self.task_ids[session_id] = set(ids)
        except (OSError, ValueError, TypeError, KeyError) as error:
            LOG.error("LifeOS task state cannot be loaded for session %s: %s", session_id, error)
            self.task_counts[session_id] = 50

    def _save_task_state(self, session_id: str) -> None:
        path = self._task_state_path(session_id)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=self.task_state_dir, delete=False) as stream:
                temporary = Path(stream.name)
                json.dump({"count": self.task_counts.get(session_id, 0), "ids": sorted(self.task_ids.get(session_id, set()))}, stream)
            os.replace(temporary, path)
        except OSError as error:
            LOG.error("LifeOS task state cannot be saved for session %s: %s", session_id, error)
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    def _supports_native_task_hook(self, session_id: str, cwd: str, backend_task_id: str = "") -> bool:
        from .native_capabilities import supports_task_count

        return supports_task_count(self.root) and self._has_native_task_hook(session_id, cwd, backend_task_id)

    def _has_native_task_hook(self, session_id: str, cwd: str, backend_task_id: str = "") -> bool:
        payload = self._payload("TaskCreated", session_id, cwd=cwd)
        groups = self._hook_groups("TaskCreated", payload, _task_uses_host_paths(backend_task_id), backend_task_id)
        return any(
            hook.get("type") == "command" and _is_native_task_governance(hook.get("command", ""), self.root)
            for group in groups if "_remote_project" not in group for hook in group.get("hooks", [])
            if _hook_matcher_matches(group.get("matcher", ""), "")
        )

    def _native_task_verdict(
        self, session_id: str, task_id: str, subject: str, description: str, count: int,
        backend_task_id: str = "",
    ) -> dict[str, str] | None:
        payload = self._payload(
            "TaskCreated", session_id, task_id=task_id, task_subject=subject,
            task_description=description, hermes_task_count=count,
        )
        for process, output in self._run("TaskCreated", payload, task_id=backend_task_id):
            if process.returncode == 2 or (output or {}).get("decision") == "block":
                message = (output or {}).get("reason") or process.stderr.strip() or "LifeOS blocked task creation"
                return {"action": "block", "message": str(message)[:2000]}
        return None

    def _task_created_verdict(
        self, args: dict[str, Any], session_id: str, call_id: str, backend_task_id: str = "",
    ) -> dict[str, str] | None:
        todos = args.get("todos")
        if not isinstance(todos, list):
            return None
        native = self._supports_native_task_hook(session_id, _scope_cwd(), backend_task_id)
        if self._has_native_task_hook(session_id, _scope_cwd(), backend_task_id) and not native:
            return {"action": "block", "message": "LifeOS task hook files do not match the verified installation. Repair or update LifeOS before creating tasks."}
        with self.session_lock:
            self._load_task_state(session_id)
            key = (session_id, call_id)
            self.pending_tasks.pop(key, None)
            known = self.task_ids.setdefault(session_id, set())
            new_items = [item for item in todos if isinstance(item, dict) and str(item.get("id", "")) not in known]
            count = self.task_counts.get(session_id, 0)
            reserved = self._reserved_task_count(session_id)
            for index, item in enumerate(new_items):
                description = item.get("content", "")
                if native:
                    verdict = self._native_task_verdict(
                        session_id, str(item.get("id", "")), str(description),
                        description if isinstance(description, str) else "", count + reserved + index,
                        backend_task_id,
                    )
                    if verdict:
                        return verdict
                if not isinstance(description, str) or len(description.strip()) < 10:
                    length = len(description) if isinstance(description, str) else 0
                    return {"action": "block", "message": f"Task creation blocked: description too short ({length} chars). Provide a meaningful task description of at least 10 characters."}
            new_ids = {str(item.get("id", "")) for item in new_items}
            if count + reserved + len(new_ids) > 50:
                return {"action": "block", "message": "Task creation blocked: session limit of 50 tasks reached."}
            if new_ids:
                self.pending_tasks[key] = (new_ids, len(new_ids))
        return None

    def _kanban_task_verdict(
        self, args: dict[str, Any], session_id: str, call_id: str, backend_task_id: str = "",
    ) -> dict[str, str] | None:
        description = args.get("body") or args.get("title", "")
        native = self._supports_native_task_hook(session_id, _scope_cwd(), backend_task_id)
        if self._has_native_task_hook(session_id, _scope_cwd(), backend_task_id) and not native:
            return {"action": "block", "message": "LifeOS task hook files do not match the verified installation. Repair or update LifeOS before creating tasks."}
        with self.session_lock:
            self._load_task_state(session_id)
            key = (session_id, call_id)
            self.pending_tasks.pop(key, None)
            count = self.task_counts.get(session_id, 0)
            reserved = self._reserved_task_count(session_id)
            if native:
                verdict = self._native_task_verdict(
                    session_id, call_id, str(args.get("title", "")),
                    description if isinstance(description, str) else "", count + reserved,
                    backend_task_id,
                )
                if verdict:
                    return verdict
            if not isinstance(description, str) or len(description.strip()) < 10:
                length = len(description) if isinstance(description, str) else 0
                return {"action": "block", "message": f"Task creation blocked: description too short ({length} chars). Provide a meaningful task description of at least 10 characters."}
            if count + reserved >= 50:
                return {"action": "block", "message": "Task creation blocked: session limit of 50 tasks reached."}
            self.pending_tasks[key] = (set(), 1)
        return None

    def task_result(
        self, tool_name: str, args: dict[str, Any], result: str,
        session_id: str = "", tool_call_id: str = "", status: str = "", **_: Any,
    ) -> None:
        if tool_name not in {"todo_list", "kanban_create"}:
            return
        with self.session_lock:
            reserved = self.pending_tasks.pop((session_id, tool_call_id or tool_name), None)
            if reserved is None or status not in {"ok", "success"}:
                return
            ids, count = reserved
            known = self.task_ids.setdefault(session_id, set())
            new_ids = ids - known
            known.update(new_ids)
            self.task_counts[session_id] = self.task_counts.get(session_id, 0) + (len(new_ids) if ids else count)
            self._save_task_state(session_id)

    def pre_llm_call(
        self, user_message: Any, session_id: str = "", is_first_turn: bool | None = None,
        platform: str = "", **_: Any,
    ) -> dict[str, str] | None:
        prompt = _prompt_text(user_message)
        if platform:
            with self.session_lock:
                self.session_platforms[session_id] = platform.lower()
        self._remember_project(_scope_cwd(), session_id)
        context = self._drain_async_context(session_id)
        with self.session_lock:
            first_turn = session_id not in self.started_sessions
            self.started_sessions.add(session_id)
        self.poll_config_changes()
        self._start_config_watcher()
        if first_turn:
            transcript = self.transcript_path(session_id)
            resumed = (not is_first_turn) if is_first_turn is not None else (
                transcript.exists() and transcript.stat().st_size > 0
            )
            source = "resume" if resumed else "startup"
            start_payload = self._payload("SessionStart", session_id, source=source)
            context.extend(self._context(self._run("SessionStart", start_payload, source), "SessionStart", allow_plain=True))
        payload = self._payload("UserPromptSubmit", session_id, prompt=prompt)
        outcomes = self._run("UserPromptSubmit", payload)
        for process, output in outcomes:
            if process.returncode == 2 or (output or {}).get("decision") == "block":
                reason = (output or {}).get("reason") or process.stderr.strip() or "Prompt blocked by a hook"
                return {"action": "block", "message": str(reason)}
        self._append_transcript(session_id, "user", user_message)
        context.extend(self._context(outcomes, "UserPromptSubmit", allow_plain=True))
        return {"context": "\n\n".join(context)} if context else None

    @staticmethod
    def _context(
        outcomes: list[tuple[subprocess.CompletedProcess[str], dict[str, Any] | None]],
        event: str,
        allow_plain: bool = False,
    ) -> list[str]:
        context = []
        for process, output in outcomes:
            specific = _specific_output(output, event)
            value = specific.get("additionalContext")
            if (
                allow_plain and not value and not output and process.returncode == 0
                and isinstance(process.args, list) and process.args[:1] == ["/bin/bash"]
                and not (process.stdout.strip().startswith("{") and process.stdout.strip().endswith("}"))
            ):
                value = process.stdout.strip()
            if isinstance(value, str) and value.strip():
                context.append(value.strip())
        return context

    def post_tool_call(
        self, tool_name: str, args: dict[str, Any], result: str,
        session_id: str = "", tool_call_id: str = "", task_id: str = "",
        status: str = "success", error_message: str = "", **_: Any,
    ) -> str | None:
        native_name = _native_tool_name(tool_name)
        if native_name is None:
            return
        cwd = _tool_cwd(tool_name, args, task_id)
        self._remember_project(cwd, session_id, task_id)
        event = "PostToolUseFailure" if status in {"error", "blocked"} else "PostToolUse"
        try:
            response = json.loads(result)
        except (json.JSONDecodeError, TypeError):
            response = result
        hook_response = response
        if (
            native_name == "Agent" and event == "PostToolUse" and isinstance(response, dict)
            and response.get("status") == "dispatched" and response.get("mode") == "background"
        ):
            hook_response = f"Spawned successfully: {json.dumps(response)}"
        use_id = tool_call_id or uuid4().hex
        v4a = tool_name == "patch" and args.get("mode") == "patch" and isinstance(args.get("patch"), str)
        native_inputs = (
            _v4a_edit_inputs(args["patch"], cwd, task_id) if v4a and event == "PostToolUse" else
            _agent_inputs(args) if native_name == "Agent" else [_tool_input(native_name, args, cwd, task_id)]
        )
        native_events = [(event, native_input, hook_response, result) for native_input in native_inputs]
        if v4a and event == "PostToolUseFailure" and isinstance(response, dict) and response.get("success") is False:
            applied = {
                bucket: [path for path in response.get(bucket, []) if isinstance(path, str)]
                for bucket in ("files_modified", "files_created", "files_deleted")
                if isinstance(response.get(bucket), list)
            }
            applied_events = []
            for native_input in _v4a_edit_inputs(args["patch"], cwd, task_id, applied):
                applied_response = {
                    "success": True, "partial_patch": True, "file_path": native_input["file_path"],
                }
                applied_events.append((
                    "PostToolUse", native_input, applied_response, json.dumps(applied_response),
                ))
            native_events = applied_events + native_events
        if not native_events:
            return None
        use_ids = [f"{use_id}:{index}" for index in range(len(native_events))] if len(native_events) > 1 else [use_id]
        self._append_transcript(session_id, "assistant", [
            {"type": "tool_use", "id": item_id, "name": native_name, "input": native_input}
            for item_id, (_, native_input, _, _) in zip(use_ids, native_events)
        ])
        self._append_transcript(
            session_id, "user", [{
                "type": "tool_result", "tool_use_id": item_id,
                "content": transcript_result if isinstance(transcript_result, str) else json.dumps(transcript_result),
                "is_error": item_event == "PostToolUseFailure",
            } for item_id, (item_event, _, _, transcript_result) in zip(use_ids, native_events)],
        )
        context = []
        for item_event, native_input, item_response, _ in native_events:
            hook_input = _native_file_input(native_name, native_input, task_id) if item_event == "PostToolUse" else native_input
            payload = self._payload(
                item_event, session_id, tool_name=native_name,
                tool_input=hook_input,
                cwd=cwd,
                **({"error": error_message or str(result)} if item_event == "PostToolUseFailure" else {"tool_response": item_response}),
            )
            external_content = tool_name in WEB_CONTENT_TOOLS or (
                native_name == "Read" and _web_cache_read(native_input, cwd, task_id)
            )
            outcomes = self._run(
                item_event, payload, native_name,
                matcher_alias="WebFetch" if item_event == "PostToolUse" and external_content else "",
                task_id=task_id,
                skip_checkpoint=v4a and event == "PostToolUseFailure" and item_event == "PostToolUse",
            )
            context.extend(self._context(outcomes, item_event))
            context.extend(
                process.stderr.strip() for process, _ in outcomes
                if process.returncode == 2 and process.stderr.strip()
            )
        return "\n\n".join(context) if context else None

    def augment_tool_result(
        self, tool_name: str, args: dict[str, Any], result: str,
        original_result: str, **kwargs: Any,
    ) -> str | None:
        self.poll_config_changes()
        context = self.post_tool_call(tool_name, args, original_result, **kwargs)
        key = (kwargs.get("session_id", ""), kwargs.get("tool_call_id") or tool_name)
        with self.session_lock:
            pending = self.pending_tool_context.pop(key, [])
        parts = pending + ([context] if context else [])
        return "\n\n".join(parts) if parts else None

    def session_end(self, session_id: str = "", reason: str = "", **_: Any) -> None:
        native_reason = {
            "new_session": "clear",
            "clear": "clear",
            "resume": "resume",
            "logout": "logout",
            "prompt_input_exit": "prompt_input_exit",
        }.get(reason, "other")
        self._run("SessionEnd", self._payload("SessionEnd", session_id, reason=native_reason), native_reason)
        shutil.rmtree(self._async_result_dir(session_id), ignore_errors=True)
        self._stop_agent_watchdog(session_id)
        with self.session_lock:
            self.started_sessions.discard(session_id)
            self.session_platforms.pop(session_id, None)
            self.session_projects.pop(session_id, None)
            self.remote_session_projects.pop(session_id, None)
            used_remote_projects = set().union(*self.remote_session_projects.values()) if self.remote_session_projects else set()
            self.remote_project_states = {
                key: state for key, state in self.remote_project_states.items() if key in used_remote_projects
            }
            active_projects = {project for projects in self.session_projects.values() for project in projects}
            self.project_dirs = tuple(sorted(active_projects)) or (Path.cwd(),)
            self.project_hook_settings = {
                path: settings for path, settings in self.project_hook_settings.items()
                if path.parent.parent in active_projects
            }
            watched = self._config_sources()
            self.config_files = {path: fingerprint for path, fingerprint in self.config_files.items() if path in watched}
            self.task_ids.pop(session_id, None)
            self.task_counts.pop(session_id, None)
            self.task_state_loaded.discard(session_id)
            self._task_state_path(session_id).unlink(missing_ok=True)
            for key in tuple(self.pending_tasks):
                if key[0] == session_id:
                    self.pending_tasks.pop(key, None)
            if not self.started_sessions:
                self.watcher_stop.set()

    def api_request_error(
        self, session_id: str = "", turn_id: str = "", reason: str = "", error: Any = None, **_: Any,
    ) -> None:
        detail = error.get("message", "") if isinstance(error, dict) else ""
        with self.session_lock:
            self.api_errors[(session_id, turn_id)] = (API_ERROR_NAMES.get(reason, "unknown"), str(detail), reason)
            if len(self.api_errors) > 1024:
                self.api_errors.pop(next(iter(self.api_errors)))

    def turn_end(
        self, session_id: str = "", turn_id: str = "", failed: bool = False,
        turn_exit_reason: str = "", failure_reason: str = "", final_response: str = "",
        interrupted: bool = False, **_: Any,
    ) -> None:
        with self.session_lock:
            error = self.api_errors.pop((session_id, turn_id), None)
        if not failed or interrupted or error is None:
            return
        error_name, detail, raw_reason = error
        if turn_exit_reason != "all_retries_exhausted_no_response" and failure_reason != raw_reason:
            return
        payload = self._payload(
            "StopFailure", session_id, error=error_name,
            **({"error_details": detail} if detail else {}),
            **({"last_assistant_message": final_response} if final_response else {}),
        )
        self._run("StopFailure", payload, error_name)

    def stop(self, response: str, session_id: str = "", stop_hook_active: bool = False,
             model: str = "", platform: str = "", reasoning_effort: str = "",
             provider: str = "",
             **_: Any) -> dict[str, str] | None:
        if platform:
            with self.session_lock:
                self.session_platforms[session_id] = platform.lower()
        payload = self._payload("Stop", session_id, last_assistant_message=response, stop_hook_active=stop_hook_active)
        try:
            for process, output in self._run("Stop", payload):
                if (output or {}).get("decision") == "block" or process.returncode == 2:
                    message = (output or {}).get("reason") or process.stderr.strip() or "Complete the LifeOS stop gate"
                    return {"action": "continue", "message": str(message)[:2000]}
            return None
        finally:
            self._append_transcript(session_id, "assistant", response, model=model,
                                    reasoning_effort=reasoning_effort, provider=provider)
