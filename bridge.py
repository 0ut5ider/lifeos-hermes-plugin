# ABOUTME: Executes installed LifeOS Claude Code hooks at matching Hermes events.
# ABOUTME: Translates hook input and control results without changing LifeOS files.

from __future__ import annotations

import json
import hashlib
import logging
import os
import re
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
V4A_WRITE_HEADER = re.compile(r"^\*\*\*\s*(?:Update|Add|Delete)\s+File:\s*(.+)$")
V4A_MOVE_HEADER = re.compile(r"^\*\*\*\s*Move\s+to:\s*(.+)$")
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


def _tool_input(name: str, args: dict[str, Any]) -> dict[str, Any]:
    translated = dict(args)
    if name in {"Write", "Edit", "Read"} and "path" in translated:
        translated["file_path"] = translated.pop("path")
    if name == "Agent" and isinstance(translated.get("tasks"), list):
        tasks = translated["tasks"]
        if tasks:
            translated["prompt"] = tasks[0].get("goal", "")
    if name == "Skill" and "name" in translated:
        translated["skill"] = translated.pop("name")
    return translated


def _v4a_edit_inputs(patch_text: str) -> list[dict[str, str]]:
    edits = []
    path = None
    added = []

    def finish() -> None:
        if path is not None:
            edits.append({"file_path": path, "new_string": "\n".join(added)})

    for line in patch_text.splitlines():
        header = V4A_WRITE_HEADER.match(line)
        move = V4A_MOVE_HEADER.match(line)
        if header:
            finish()
            path = header.group(1).strip()
            added = []
        elif move:
            edits.append({"file_path": move.group(1).strip(), "new_string": ""})
        elif line.startswith("***"):
            finish()
            path = None
            added = []
        elif path is not None and line.startswith("+"):
            added.append(line[1:])
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
    try:
        from agent.delegation_context import is_delegated_child_context
    except ImportError:
        background = bool(args.get("background"))
    else:
        background = not is_delegated_child_context()
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


class HookBridge:
    def __init__(self, settings_path: Path, root: Path):
        self.settings_path = Path(settings_path)
        self.root = Path(root)
        self.base_environment = dict(os.environ)
        self._apply_settings(json.loads(self.settings_path.read_text()))
        self.started_sessions: set[str] = set()
        self.session_lock = threading.Lock()
        self.pending_tool_context: dict[tuple[str, str], list[str]] = {}
        self.task_ids: dict[str, set[str]] = {}
        self.task_counts: dict[str, int] = {}
        self.pending_tasks: dict[tuple[str, str], tuple[set[str], int]] = {}
        self.api_errors: dict[tuple[str, str], tuple[str, str, str]] = {}
        self.transcript_dir = self.root / "LIFEOS/MEMORY/STATE/hermes-transcripts"
        self.transcript_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.project_dirs = (Path.cwd(),)
        self.session_projects: dict[str, set[Path]] = {}
        self.config_files = self._config_files()
        self.last_config_poll = 0.0
        self.watcher_stop = threading.Event()
        self.watcher: threading.Thread | None = None

    def _start_config_watcher(self) -> None:
        if "ConfigChange" not in self.hooks:
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
        self.native_task_hook_supported = None

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
        project_dir = Path(cwd).resolve()
        with self.session_lock:
            projects = self.session_projects.setdefault(session_id, set())
            if project_dir in projects:
                return
            projects.add(project_dir)
            if project_dir not in self.project_dirs:
                self.project_dirs += (project_dir,)
            for path, fingerprint in self._config_files().items():
                self.config_files.setdefault(path, fingerprint)

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
                if source in {"project_settings", "local_settings"} or (
                    source == "skills" and not path.is_relative_to(self.settings_path.parent / "skills")
                ):
                    if not any(path.is_relative_to(project / ".claude") for project in session_projects.get(session_id, ())):
                        continue
                outcomes = self._run("ConfigChange", self._payload(
                    "ConfigChange", session_id, source=source, file_path=str(path), config_path=str(path),
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

    def transcript_path(self, session_id: str) -> Path:
        name = re.sub(r"[^A-Za-z0-9._-]", "_", session_id or "default")
        return self.transcript_dir / f"{name}.jsonl"

    def _append_transcript(self, session_id: str, kind: str, content: Any) -> None:
        row = {
            "type": kind,
            "sessionId": session_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "message": {"role": kind, "content": content},
        }
        path = self.transcript_path(session_id)
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        with os.fdopen(descriptor, "w") as stream:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")

    def _run(self, event: str, payload: dict[str, Any], tool_name: str = "") -> list[tuple[subprocess.CompletedProcess[str], dict[str, Any] | None]]:
        sync_hooks = []
        for group in self.hooks.get(event, []):
            matcher = group.get("matcher", "")
            if matcher and not re.fullmatch(matcher, tool_name):
                continue
            for hook in group.get("hooks", []):
                if hook.get("type") == "http":
                    sync_hooks.append((self._run_http, (hook, payload)))
                    continue
                if hook.get("type") != "command":
                    LOG.warning("LifeOS %s hook type %r is not executable by this bridge", event, hook.get("type"))
                    continue
                command = hook.get("command")
                if not isinstance(command, str) or not command.strip():
                    continue
                timeout = max(1, min(int(hook.get("timeout", 60)), 300))
                if hook.get("async"):
                    self._run_async(command, payload, timeout)
                    continue
                sync_hooks.append((self._run_command, (event, command, payload, timeout)))
        outcomes = []
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
    ) -> subprocess.CompletedProcess[str] | None:
        try:
            process = subprocess.run(
                ["/bin/bash", "-c", command], input=json.dumps(payload), text=True,
                capture_output=True, timeout=timeout, cwd=payload.get("cwd") or self.root,
                env=self.environment, check=False,
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

    def _run_async(self, command: str, payload: dict[str, Any], timeout: int) -> None:
        spool_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=self.transcript_dir,
                prefix="async-hook-", suffix=".json", delete=False,
            ) as spool:
                spool_path = Path(spool.name)
                json.dump({"command": command, "payload": payload, "timeout": timeout}, spool)
            subprocess.Popen(
                [sys.executable, str(Path(__file__).parent / "bin/hook_runner.py"), str(spool_path)],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                cwd=payload.get("cwd") or self.root,
                env=self.environment,
                start_new_session=True,
                close_fds=True,
            )
        except OSError as error:
            LOG.error("LifeOS async hook failed to start: %s", error)
            if spool_path is not None:
                spool_path.unlink(missing_ok=True)

    def _payload(self, event: str, session_id: str, **fields: Any) -> dict[str, Any]:
        return {
            "hook_event_name": event,
            "session_id": session_id,
            "transcript_path": str(self.transcript_path(session_id)),
            "cwd": _scope_cwd(),
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
        groups = self.hooks.get("PermissionRequest", [])
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
        groups = self.hooks.get("PermissionRequest", [])
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
        if tool_name == "todo_list" and "TaskCreated" in self.hooks:
            task_verdict = self._task_created_verdict(args, session_id, tool_call_id or tool_name)
            if task_verdict:
                return task_verdict
        if tool_name == "kanban_create" and "TaskCreated" in self.hooks:
            task_verdict = self._kanban_task_verdict(args, session_id, tool_call_id or tool_name)
            if task_verdict:
                return task_verdict
        native_name = _native_tool_name(tool_name)
        if native_name is None:
            return None
        cwd = _tool_cwd(tool_name, args, task_id)
        self._remember_project(cwd, session_id)
        v4a = tool_name == "patch" and args.get("mode") == "patch" and isinstance(args.get("patch"), str)
        native_inputs = (
            _v4a_edit_inputs(args["patch"]) if v4a else
            _agent_inputs(args) if native_name == "Agent" else [_tool_input(native_name, args)]
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
            permission_inputs = native_inputs if v4a else [_tool_input(native_name, updated_args or args)]
            verdict = self._file_permission_verdict(native_name, permission_inputs, session_id, cwd)
            if verdict:
                if verdict["action"] == "approve" and updated_args is not None:
                    verdict["args"] = updated_args
                return verdict
        return {"action": "modify", "args": updated_args} if updated_args is not None else None

    def _reserved_task_count(self, session_id: str) -> int:
        return sum(count for (owner, _), (_, count) in self.pending_tasks.items() if owner == session_id)

    def _supports_native_task_hook(self) -> bool:
        if self.native_task_hook_supported is None:
            payload = self._payload("TaskCreated", "probe", hermes_bridge_probe=True)
            self.native_task_hook_supported = any(
                process.returncode == 0 and (output or {}).get("hermes_bridge_task_governance") == 1
                for process, output in self._run("TaskCreated", payload)
            )
        return self.native_task_hook_supported

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
        native = self._supports_native_task_hook()
        with self.session_lock:
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
        native = self._supports_native_task_hook()
        with self.session_lock:
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

    def pre_llm_call(self, user_message: Any, session_id: str = "", **_: Any) -> dict[str, str] | None:
        prompt = _prompt_text(user_message)
        self._remember_project(_scope_cwd(), session_id)
        context = []
        with self.session_lock:
            first_turn = session_id not in self.started_sessions
            self.started_sessions.add(session_id)
        self.poll_config_changes()
        self._start_config_watcher()
        if first_turn:
            start_payload = self._payload("SessionStart", session_id, source="startup")
            context.extend(self._context(self._run("SessionStart", start_payload)))
        self._append_transcript(session_id, "user", user_message)
        payload = self._payload("UserPromptSubmit", session_id, prompt=prompt)
        context.extend(self._context(self._run("UserPromptSubmit", payload)))
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
        use_id = tool_call_id or uuid4().hex
        v4a = tool_name == "patch" and args.get("mode") == "patch" and isinstance(args.get("patch"), str)
        native_inputs = (
            _v4a_edit_inputs(args["patch"]) if v4a and event == "PostToolUse" else
            _agent_inputs(args) if native_name == "Agent" else [_tool_input(native_name, args)]
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
                **({"error": error_message or str(result)} if event == "PostToolUseFailure" else {"tool_response": response}),
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
        with self.session_lock:
            self.started_sessions.discard(session_id)
            self.session_projects.pop(session_id, None)
            active_projects = {project for projects in self.session_projects.values() for project in projects}
            self.project_dirs = tuple(sorted(active_projects)) or (Path.cwd(),)
            watched = self._config_sources()
            self.config_files = {path: fingerprint for path, fingerprint in self.config_files.items() if path in watched}
            self.task_ids.pop(session_id, None)
            self.task_counts.pop(session_id, None)
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

    def stop(self, response: str, session_id: str = "", stop_hook_active: bool = False, **_: Any) -> dict[str, str] | None:
        self._append_transcript(session_id, "assistant", response)
        payload = self._payload("Stop", session_id, last_assistant_message=response, stop_hook_active=stop_hook_active)
        for process, output in self._run("Stop", payload):
            if (output or {}).get("decision") == "block" or process.returncode == 2:
                message = (output or {}).get("reason") or process.stderr.strip() or "Complete the LifeOS stop gate"
                return {"action": "continue", "message": str(message)[:2000]}
        return None
