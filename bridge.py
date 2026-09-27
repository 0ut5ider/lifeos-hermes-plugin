# ABOUTME: Executes installed LifeOS Claude Code hooks at matching Hermes events.
# ABOUTME: Translates hook input and control results without changing LifeOS files.

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import threading
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
}


def _native_tool_name(tool_name: str) -> str | None:
    if tool_name.startswith("mcp__"):
        return tool_name
    return TOOL_NAMES.get(tool_name)


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


class HookBridge:
    def __init__(self, settings_path: Path, root: Path):
        self.settings_path = Path(settings_path)
        self.root = Path(root)
        settings = json.loads(self.settings_path.read_text())
        self.hooks = settings.get("hooks", {})
        if not isinstance(self.hooks, dict):
            raise ValueError("LifeOS hooks setting must be an object")
        self.environment = dict(os.environ)
        for key, value in settings.get("env", {}).items():
            if isinstance(value, str):
                self.environment[key] = value.replace("${HOME}", str(Path.home())).replace("$HOME", str(Path.home()))
        self.environment.setdefault("LIFEOS_DIR", str(self.root / "LIFEOS"))
        self.environment["PATH"] = (
            f"{Path(__file__).parent / 'bin'}:{Path.home() / '.bun/bin'}:"
            f"{Path.home() / '.local/bin'}:{self.environment.get('PATH', '')}"
        )
        self.started_sessions: set[str] = set()
        self.session_lock = threading.Lock()
        self.pending_tool_context: dict[tuple[str, str], list[str]] = {}
        self.task_ids: dict[str, set[str]] = {}
        self.task_counts: dict[str, int] = {}
        self.transcript_dir = self.root / "LIFEOS/MEMORY/STATE/hermes-transcripts"
        self.transcript_dir.mkdir(parents=True, exist_ok=True, mode=0o700)

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
        outcomes = []
        for group in self.hooks.get(event, []):
            matcher = group.get("matcher", "")
            if matcher and not re.fullmatch(matcher, tool_name):
                continue
            for hook in group.get("hooks", []):
                if hook.get("type") == "http":
                    outcome = self._run_http(hook, payload)
                    if outcome is not None:
                        outcomes.append((outcome, _decode_output(outcome.stdout)))
                        if event == "PreToolUse" and ((outcomes[-1][1] or {}).get("hookSpecificOutput") or {}).get("permissionDecision") == "deny":
                            return outcomes
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
                try:
                    process = subprocess.run(
                        ["/bin/bash", "-c", command],
                        input=json.dumps(payload),
                        text=True,
                        capture_output=True,
                        timeout=timeout,
                        cwd=self.root,
                        env=self.environment,
                        check=False,
                    )
                except (OSError, subprocess.TimeoutExpired) as error:
                    LOG.error("LifeOS %s hook failed to execute: %s", event, error)
                    continue
                if process.returncode not in (0, 2):
                    LOG.warning("LifeOS %s hook exited %s: %s", event, process.returncode, process.stderr[:400])
                outcomes.append((process, _decode_output(process.stdout)))
                if event in {"PreToolUse", "Stop"} and (process.returncode == 2 or (outcomes[-1][1] or {}).get("decision") == "block"):
                    return outcomes
        return outcomes

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
        try:
            process = subprocess.Popen(
                ["/bin/bash", "-c", command],
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                text=True,
                cwd=self.root,
                env=self.environment,
            )
        except OSError as error:
            LOG.error("LifeOS async hook failed to start: %s", error)
            return

        def finish() -> None:
            try:
                process.communicate(json.dumps(payload), timeout=timeout)
            except subprocess.TimeoutExpired:
                process.kill()
                process.communicate()
                LOG.error("LifeOS async hook timed out: %s", command)

        threading.Thread(target=finish, daemon=True).start()

    def _payload(self, event: str, session_id: str, **fields: Any) -> dict[str, Any]:
        return {
            "hook_event_name": event,
            "session_id": session_id,
            "transcript_path": str(self.transcript_path(session_id)),
            "cwd": str(self.root),
            **fields,
        }

    def pre_tool_call(
        self, tool_name: str, args: dict[str, Any], session_id: str = "", tool_call_id: str = "", **_: Any,
    ) -> dict[str, Any] | None:
        if tool_name == "todo_list" and "TaskCreated" in self.hooks:
            task_verdict = self._task_created_verdict(args, session_id)
            if task_verdict:
                return task_verdict
        native_name = _native_tool_name(tool_name)
        if native_name is None:
            return None
        payload = self._payload("PreToolUse", session_id, tool_name=native_name, tool_input=_tool_input(native_name, args))
        updated_args = None
        extra_context = []
        for process, output in self._run("PreToolUse", payload, native_name):
            specific = (output or {}).get("hookSpecificOutput") or {}
            decision = specific.get("permissionDecision") or (output or {}).get("decision")
            if process.returncode == 2 or decision in {"deny", "block"}:
                message = specific.get("permissionDecisionReason") or (output or {}).get("reason") or process.stderr.strip() or "Blocked by a LifeOS hook"
                return {"action": "block", "message": str(message)[:2000]}
            updated = specific.get("updatedInput") or (output or {}).get("updatedInput")
            if isinstance(updated, dict):
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
        return {"action": "modify", "args": updated_args} if updated_args is not None else None

    def _task_created_verdict(self, args: dict[str, Any], session_id: str) -> dict[str, str] | None:
        todos = args.get("todos")
        if not isinstance(todos, list):
            return None
        with self.session_lock:
            known = self.task_ids.setdefault(session_id, set())
            new_items = [item for item in todos if isinstance(item, dict) and str(item.get("id", "")) not in known]
            for item in new_items:
                description = item.get("content", "")
                if not isinstance(description, str) or len(description.strip()) < 10:
                    length = len(description) if isinstance(description, str) else 0
                    return {"action": "block", "message": f"Task creation blocked: description too short ({length} chars). Provide a meaningful task description of at least 10 characters."}
            count = self.task_counts.get(session_id, 0)
            if count + len(new_items) > 50:
                return {"action": "block", "message": "Task creation blocked: session limit of 50 tasks reached."}
            known.update(str(item.get("id", "")) for item in new_items)
            self.task_counts[session_id] = count + len(new_items)
        return None

    def pre_llm_call(self, user_message: Any, session_id: str = "", **_: Any) -> dict[str, str] | None:
        if not isinstance(user_message, str):
            return None
        context = []
        with self.session_lock:
            first_turn = session_id not in self.started_sessions
            self.started_sessions.add(session_id)
        if first_turn:
            start_payload = self._payload("SessionStart", session_id, source="startup")
            context.extend(self._context(self._run("SessionStart", start_payload)))
        self._append_transcript(session_id, "user", user_message)
        payload = self._payload("UserPromptSubmit", session_id, prompt=user_message)
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
        session_id: str = "", tool_call_id: str = "", status: str = "success", error_message: str = "", **_: Any,
    ) -> str | None:
        native_name = _native_tool_name(tool_name)
        if native_name is None:
            return
        event = "PostToolUseFailure" if status in {"error", "blocked"} else "PostToolUse"
        try:
            response = json.loads(result)
        except (json.JSONDecodeError, TypeError):
            response = result
        use_id = tool_call_id or uuid4().hex
        self._append_transcript(session_id, "assistant", [{
            "type": "tool_use", "id": use_id, "name": native_name, "input": _tool_input(native_name, args),
        }])
        self._append_transcript(
            session_id, "user", [{
                "type": "tool_result", "tool_use_id": use_id,
                "content": result if isinstance(result, str) else json.dumps(result),
                "is_error": status in {"error", "blocked"},
            }],
        )
        payload = self._payload(
            event, session_id, tool_name=native_name,
            tool_input=_tool_input(native_name, args),
            **({"error": error_message or str(result)} if event == "PostToolUseFailure" else {"tool_response": response}),
        )
        context = self._context(self._run(event, payload, native_name))
        return "\n\n".join(context) if context else None

    def augment_tool_result(
        self, tool_name: str, args: dict[str, Any], result: str,
        original_result: str, **kwargs: Any,
    ) -> str | None:
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
            self.task_ids.pop(session_id, None)
            self.task_counts.pop(session_id, None)

    def stop(self, response: str, session_id: str = "", stop_hook_active: bool = False, **_: Any) -> dict[str, str] | None:
        self._append_transcript(session_id, "assistant", response)
        payload = self._payload("Stop", session_id, last_assistant_message=response, stop_hook_active=stop_hook_active)
        for process, output in self._run("Stop", payload):
            if (output or {}).get("decision") == "block" or process.returncode == 2:
                message = (output or {}).get("reason") or process.stderr.strip() or "Complete the LifeOS stop gate"
                return {"action": "continue", "message": str(message)[:2000]}
        return None
