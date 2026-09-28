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
from concurrent.futures import ThreadPoolExecutor
from contextvars import copy_context
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import ProxyHandler, Request, build_opener
from uuid import uuid4
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


LOG = logging.getLogger(__name__)
TOOL_NAMES = {
    "terminal": "Bash",
    "write_file": "Write",
    "patch": "Edit",
    "read_file": "Read",
    "delegate_task": "Agent",
    "web_search": "WebSearch",
    "web_fetch": "WebFetch",
    "skill_view": "Skill",
    "tool_search": "ToolSearch",
    "clarify": "AskUserQuestion",
}
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
    return TOOL_NAMES.get(tool_name)


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


def _v4a_edit_inputs(patch_text: str, cwd: str, task_id: str = "default") -> list[dict[str, str]]:
    edits = []
    path = None
    path_entry = False
    added = []
    removed = []

    def finish() -> None:
        if path is not None:
            edits.append({
                "file_path": _hook_file_path(path, cwd, task_id, entry=path_entry),
                "old_string": "\n".join(removed), "new_string": "\n".join(added),
            })

    for line in patch_text.splitlines():
        header = V4A_WRITE_HEADER.match(line)
        move = V4A_MOVE_HEADER.match(line)
        if header:
            finish()
            path = header.group(2).strip()
            path_entry = header.group(1) == "Delete"
            added = []
            removed = []
        elif move:
            finish()
            path = None
            edits.append({
                "file_path": _hook_file_path(move.group(1).strip(), cwd, task_id, entry=True),
                "old_string": "", "new_string": "",
            })
            edits.append({
                "file_path": _hook_file_path(move.group(2).strip(), cwd, task_id, entry=True),
                "old_string": "", "new_string": "",
            })
        elif line.startswith("***"):
            finish()
            path = None
            path_entry = False
            added = []
            removed = []
        elif path is not None and line.startswith("+"):
            added.append(line[1:])
        elif path is not None and line.startswith("-"):
            removed.append(line[1:])
    finish()
    return edits


def _agent_inputs(args: dict[str, Any]) -> list[dict[str, str]]:
    if args.get("action"):
        return []
    tasks = args.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        tasks = [args]
    inputs = []
    descriptions = set()
    background = bool(args.get("background"))
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
        return _scope_cwd()
    return _authoritative_workspace_root(task_id or "default") or _scope_cwd()


def _prompt_text(message: Any) -> str:
    if isinstance(message, str):
        return message
    if isinstance(message, list):
        return "\n".join(part for item in message if (part := _prompt_text(item)))
    if isinstance(message, dict):
        if message.get("type") == "image_url":
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
    def __init__(self, settings_path: Path, root: Path):
        self.settings_path = Path(settings_path)
        self.root = Path(root)
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
        self.config_files = self._config_files()
        self.last_config_poll = 0.0
        self.watcher_stop = threading.Event()
        self.watcher: threading.Thread | None = None
        self.watchdog_dir = self.root / "LIFEOS/MEMORY/STATE/hermes-watchdogs"
        self.watchdog_processes: dict[str, str] = {}
        self.watchdog_last_active: dict[str, float] = {}
        self.watchdog_stop = threading.Event()
        self.watchdog_thread: threading.Thread | None = None

    def _start_config_watcher(self) -> None:
        if "ConfigChange" not in self.hooks and not any(
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
        now = time.time()
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
                    progress = []
                    for item in active:
                        children = item.get("children_activity") or []
                        progress.extend(
                            now - child["seconds_since_activity"] for child in children
                            if isinstance(child, dict) and isinstance(child.get("seconds_since_activity"), (int, float))
                        )
                        if isinstance(item.get("seconds_since_progress"), (int, float)):
                            progress.append(now - item["seconds_since_progress"])
                    latest = max(progress, default=activity.stat().st_mtime)
                    if latest > activity.stat().st_mtime + 0.5:
                        os.utime(activity, (latest, latest))
                    with self.session_lock:
                        self.watchdog_last_active[session_id] = time.monotonic()
                elif time.monotonic() - self.watchdog_last_active.get(session_id, 0) > 30:
                    self._stop_agent_watchdog(session_id)
            finally:
                temp.unlink(missing_ok=True)

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
        self.environment = environment
        self.native_task_hook_supported: dict[tuple[str, str], bool] = {}

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

    def _remember_project(self, cwd: str, session_id: str) -> None:
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

    def _matching_project(self, payload: dict[str, Any]) -> Path | None:
        cwd = Path(payload.get("cwd") or _scope_cwd()).resolve()
        session_id = payload.get("session_id", "")
        with self.session_lock:
            projects = self.session_projects.get(session_id, set())
            project = next((path for path in sorted(projects, key=lambda value: len(value.parts), reverse=True)
                            if cwd.is_relative_to(path)), None)
            if project is None and "tool_name" not in payload and len(projects) == 1:
                project = next(iter(projects))
        return project if project is not None and _trusted_project(project) else None

    def _hook_groups(self, event: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
        groups = list(self.hooks.get(event, []))
        project = self._matching_project(payload)
        if project is not None:
            with self.session_lock:
                for name in ("settings.json", "settings.local.json"):
                    settings = self.project_hook_settings.get(project / ".claude" / name, {})
                    groups.extend(settings.get("hooks", {}).get(event, []))
        return groups

    def _event_environment(self, payload: dict[str, Any]) -> dict[str, str]:
        environment = dict(self.environment)
        with self.session_lock:
            platform = self.session_platforms.get(payload.get("session_id", ""), "")
        project = self._matching_project(payload)
        if project is not None:
            with self.session_lock:
                for name in ("settings.json", "settings.local.json"):
                    settings = self.project_hook_settings.get(project / ".claude" / name, {})
                    for key, value in settings.get("env", {}).items():
                        if isinstance(value, str):
                            environment[key] = value.replace("${HOME}", str(Path.home())).replace("$HOME", str(Path.home()))
        if platform and platform not in {"cli", "tui", "desktop"}:
            environment["LIFEOS_NOTIFICATION_CHANNEL"] = platform
        return environment

    def _config_files(self) -> dict[Path, tuple[int, int]]:
        result = {}
        for path in self._config_sources():
            try:
                stat = path.stat()
                result[path] = (stat.st_mtime_ns, stat.st_size)
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
                    self.native_task_hook_supported.clear()
                self._start_config_watcher()

    def transcript_path(self, session_id: str) -> Path:
        name = re.sub(r"[^A-Za-z0-9._-]", "_", session_id or "default")
        return self.transcript_dir / f"{name}.jsonl"

    def _append_transcript(self, session_id: str, kind: str, content: Any, model: str = "") -> None:
        row = {
            "type": kind,
            "sessionId": session_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "message": {"role": kind, "content": content},
        }
        if kind == "assistant" and model:
            row["message"]["model"] = model
        path = self.transcript_path(session_id)
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        with os.fdopen(descriptor, "w") as stream:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")

    def _run(self, event: str, payload: dict[str, Any], tool_name: str = "") -> list[tuple[subprocess.CompletedProcess[str], dict[str, Any] | None]]:
        jobs = []
        environment = self._event_environment(payload)
        for group in self._hook_groups(event, payload):
            matcher = group.get("matcher", "")
            if matcher and not re.fullmatch(matcher, tool_name):
                continue
            for hook in group.get("hooks", []):
                if hook.get("type") == "http":
                    jobs.append((self._run_http, (hook, payload), False))
                    continue
                if hook.get("type") != "command":
                    LOG.warning("LifeOS %s hook type %r is not executable by this bridge", event, hook.get("type"))
                    continue
                command = hook.get("command")
                if not isinstance(command, str) or not command.strip():
                    continue
                if hook.get("async"):
                    jobs.append((self._run_async, (command, payload, environment), True))
                    continue
                timeout = max(1, min(int(hook.get("timeout", 60)), 300))
                jobs.append((self._run_command, (event, command, payload, timeout, environment), False))
        outcomes = []
        if not jobs:
            return outcomes
        if event == "SessionEnd":
            for callback, arguments, asynchronous in jobs:
                try:
                    process = callback(*arguments)
                except Exception as error:
                    LOG.error("LifeOS %s hook failed: %s", event, error)
                    continue
                if not asynchronous and process is not None:
                    outcomes.append((process, _decode_output(process.stdout)))
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
        environment: dict[str, str],
    ) -> subprocess.CompletedProcess[str] | None:
        try:
            process = subprocess.run(
                ["/bin/bash", "-c", command], input=json.dumps(payload), text=True,
                capture_output=True, timeout=timeout, cwd=payload.get("cwd") or self.root,
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
        self, command: str, payload: dict[str, Any], environment: dict[str, str],
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
                           "cwd": payload.get("cwd") or str(self.root), "environment": environment,
                           "result_path": str(result_path) if result_path else None}, spool)
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
                cwd=payload.get("cwd") or self.root,
                env=environment,
                start_new_session=True,
                close_fds=True,
            )
            threading.Thread(target=process.wait, daemon=True, name="lifeos-async-hook-reap").start()
        except (OSError, subprocess.TimeoutExpired) as error:
            LOG.error("LifeOS async hook failed to start: %s", error)
            if spool_path is not None:
                spool_path.unlink(missing_ok=True)

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

    def command_approval(self, command: str, session_key: str = "", **_: Any) -> dict[str, str] | None:
        payload = self._payload(
            "PermissionRequest", session_key, tool_name="Bash", tool_input={"command": command},
        )
        for _, output in self._run("PermissionRequest", payload, "Bash"):
            specific = (output or {}).get("hookSpecificOutput") or {}
            decision = specific.get("decision") or {}
            if specific.get("hookEventName") == "PermissionRequest" and decision.get("behavior") == "allow":
                return {"action": "allow"}
        return None

    def _mcp_permission_verdict(
        self, tool_name: str, args: dict[str, Any], session_id: str, cwd: str,
    ) -> dict[str, Any] | None:
        groups = self._hook_groups(
            "PermissionRequest", self._payload("PermissionRequest", session_id, cwd=cwd, tool_name=tool_name),
        )
        if not any(re.fullmatch(group.get("matcher", "") or ".*", tool_name) for group in groups):
            return None
        payload = self._payload("PermissionRequest", session_id, tool_name=tool_name, tool_input=args, cwd=cwd)
        outcomes = self._run("PermissionRequest", payload, tool_name)
        granted = False
        for process, output in outcomes:
            specific = (output or {}).get("hookSpecificOutput") or {}
            decision = specific.get("decision") or {}
            if decision.get("behavior") == "deny" or process.returncode == 2:
                message = decision.get("reason") or process.stderr.strip() or "LifeOS denied the MCP call"
                return {"action": "block", "message": str(message)[:2000]}
            if specific.get("hookEventName") == "PermissionRequest" and decision.get("behavior") == "allow":
                granted = True
        if granted:
            return None
        fingerprint = hashlib.sha256(json.dumps(args, sort_keys=True).encode()).hexdigest()[:16]
        return {
            "action": "approve",
            "message": f"LifeOS requests review of MCP call {tool_name}",
            "rule_key": f"lifeos-mcp:{tool_name}:{fingerprint}",
        }

    def _file_permission_verdict(
        self, native_name: str, native_inputs: list[dict[str, Any]], session_id: str, cwd: str,
    ) -> dict[str, Any] | None:
        groups = self._hook_groups(
            "PermissionRequest", self._payload("PermissionRequest", session_id, cwd=cwd, tool_name=native_name),
        )
        if not any(re.fullmatch(group.get("matcher", "") or ".*", native_name) for group in groups):
            return None
        review_paths = []
        for native_input in native_inputs:
            payload = self._payload(
                "PermissionRequest", session_id, tool_name=native_name, tool_input=native_input, cwd=cwd,
            )
            outcomes = self._run("PermissionRequest", payload, native_name)
            granted = False
            for process, output in outcomes:
                specific = (output or {}).get("hookSpecificOutput") or {}
                decision = specific.get("decision") or {}
                if decision.get("behavior") == "deny" or process.returncode == 2:
                    message = decision.get("reason") or process.stderr.strip() or "LifeOS denied the file change"
                    return {"action": "block", "message": str(message)[:2000]}
                if specific.get("hookEventName") == "PermissionRequest" and decision.get("behavior") == "allow":
                    granted = True
            if not granted:
                review_paths.append(str(native_input.get("file_path", "unknown path")))
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
        self._remember_project(cwd, session_id)
        if tool_name == "todo_list" and self._hook_groups(
            "TaskCreated", self._payload("TaskCreated", session_id, cwd=cwd, tool_name=tool_name),
        ):
            task_verdict = self._task_created_verdict(args, session_id, tool_call_id or tool_name)
            if task_verdict:
                return task_verdict
        if tool_name == "kanban_create" and self._hook_groups(
            "TaskCreated", self._payload("TaskCreated", session_id, cwd=cwd, tool_name=tool_name),
        ):
            task_verdict = self._kanban_task_verdict(args, session_id, tool_call_id or tool_name)
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
        for native_input in native_inputs:
            payload = self._payload("PreToolUse", session_id, tool_name=native_name, tool_input=native_input, cwd=cwd)
            for process, output in self._run("PreToolUse", payload, native_name):
                specific = (output or {}).get("hookSpecificOutput") or {}
                decision = specific.get("permissionDecision") or (output or {}).get("decision")
                if process.returncode == 2 or decision in {"deny", "block"}:
                    message = specific.get("permissionDecisionReason") or (output or {}).get("reason") or process.stderr.strip() or "Blocked by a LifeOS hook"
                    return {"action": "block", "message": str(message)[:2000]}
                updated = specific.get("updatedInput") or (output or {}).get("updatedInput")
                if isinstance(updated, dict) and not v4a:
                    updated_args = _hermes_input(native_name, updated)
                context = specific.get("additionalContext") or (output or {}).get("additionalContext")
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
        if tool_name.startswith("mcp__"):
            verdict = self._mcp_permission_verdict(tool_name, updated_args or args, session_id, cwd)
            if verdict:
                if verdict["action"] == "approve" and updated_args is not None:
                    verdict["args"] = updated_args
                return verdict
        if native_name in {"Write", "Edit"}:
            permission_inputs = native_inputs if v4a else [_tool_input(native_name, updated_args or args, cwd, task_id)]
            verdict = self._file_permission_verdict(native_name, permission_inputs, session_id, cwd)
            if verdict:
                if verdict["action"] == "approve" and updated_args is not None:
                    verdict["args"] = updated_args
                return verdict
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

    def _supports_native_task_hook(self, session_id: str, cwd: str) -> bool:
        key = (session_id, cwd)
        if key not in self.native_task_hook_supported:
            payload = self._payload("TaskCreated", session_id, cwd=cwd, hermes_bridge_probe=True)
            self.native_task_hook_supported[key] = any(
                process.returncode == 0 and (output or {}).get("hermes_bridge_task_governance") == 1
                for process, output in self._run("TaskCreated", payload)
            )
        return self.native_task_hook_supported[key]

    def _native_task_verdict(
        self, session_id: str, task_id: str, subject: str, description: str, count: int,
    ) -> dict[str, str] | None:
        payload = self._payload(
            "TaskCreated", session_id, task_id=task_id, task_subject=subject,
            task_description=description, hermes_task_count=count,
        )
        for process, output in self._run("TaskCreated", payload):
            if process.returncode == 2 or (output or {}).get("decision") == "block":
                message = (output or {}).get("reason") or process.stderr.strip() or "LifeOS blocked task creation"
                return {"action": "block", "message": str(message)[:2000]}
        return None

    def _task_created_verdict(self, args: dict[str, Any], session_id: str, call_id: str) -> dict[str, str] | None:
        todos = args.get("todos")
        if not isinstance(todos, list):
            return None
        native = self._supports_native_task_hook(session_id, _scope_cwd())
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

    def _kanban_task_verdict(self, args: dict[str, Any], session_id: str, call_id: str) -> dict[str, str] | None:
        description = args.get("body") or args.get("title", "")
        native = self._supports_native_task_hook(session_id, _scope_cwd())
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
            context.extend(self._context(self._run("SessionStart", start_payload)))
        payload = self._payload("UserPromptSubmit", session_id, prompt=prompt)
        outcomes = self._run("UserPromptSubmit", payload)
        for process, output in outcomes:
            if process.returncode == 2 or (output or {}).get("decision") == "block":
                reason = (output or {}).get("reason") or process.stderr.strip() or "Prompt blocked by a hook"
                return {"action": "block", "message": str(reason)}
        self._append_transcript(session_id, "user", user_message)
        context.extend(self._context(outcomes))
        return {"context": "\n\n".join(context)} if context else None

    @staticmethod
    def _context(outcomes: list[tuple[subprocess.CompletedProcess[str], dict[str, Any] | None]]) -> list[str]:
        context = []
        for process, output in outcomes:
            specific = (output or {}).get("hookSpecificOutput") or {}
            value = specific.get("additionalContext") or (output or {}).get("additionalContext")
            if not value and not output:
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
        self._remember_project(cwd, session_id)
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
        if not native_inputs:
            return None
        use_ids = [f"{use_id}:{index}" for index in range(len(native_inputs))] if len(native_inputs) > 1 else [use_id]
        self._append_transcript(session_id, "assistant", [
            {"type": "tool_use", "id": item_id, "name": native_name, "input": native_input}
            for item_id, native_input in zip(use_ids, native_inputs)
        ])
        self._append_transcript(
            session_id, "user", [{
                "type": "tool_result", "tool_use_id": item_id,
                "content": result if isinstance(result, str) else json.dumps(result),
                "is_error": status in {"error", "blocked"},
            } for item_id in use_ids],
        )
        context = []
        for native_input in native_inputs:
            payload = self._payload(
                event, session_id, tool_name=native_name,
                tool_input=native_input,
                cwd=cwd,
                **({"error": error_message or str(result)} if event == "PostToolUseFailure" else {"tool_response": hook_response}),
            )
            context.extend(self._context(self._run(event, payload, native_name)))
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

    def session_end(self, session_id: str = "", **_: Any) -> None:
        self._run("SessionEnd", self._payload("SessionEnd", session_id, reason="other"))
        shutil.rmtree(self._async_result_dir(session_id), ignore_errors=True)
        self._stop_agent_watchdog(session_id)
        with self.session_lock:
            self.started_sessions.discard(session_id)
            self.session_platforms.pop(session_id, None)
            self.session_projects.pop(session_id, None)
            active_projects = {project for projects in self.session_projects.values() for project in projects}
            self.project_dirs = tuple(sorted(active_projects)) or (Path.cwd(),)
            self.project_hook_settings = {
                path: settings for path, settings in self.project_hook_settings.items()
                if path.parent.parent in active_projects
            }
            for key in tuple(self.native_task_hook_supported):
                if key[0] == session_id:
                    self.native_task_hook_supported.pop(key, None)
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
             model: str = "", platform: str = "", **_: Any) -> dict[str, str] | None:
        if platform:
            with self.session_lock:
                self.session_platforms[session_id] = platform.lower()
        self._append_transcript(session_id, "assistant", response, model=model)
        payload = self._payload("Stop", session_id, last_assistant_message=response, stop_hook_active=stop_hook_active)
        for process, output in self._run("Stop", payload):
            if (output or {}).get("decision") == "block" or process.returncode == 2:
                message = (output or {}).get("reason") or process.stderr.strip() or "Complete the LifeOS stop gate"
                return {"action": "continue", "message": str(message)[:2000]}
        return None
