# ABOUTME: Runs a trusted project hook inside the backend that owns its workspace.
# ABOUTME: Carries hook input over stdin and separates remote stdout from stderr.

from __future__ import annotations

import base64
import json
import logging
import os
import re
import stat
import subprocess
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any
from uuid import uuid4


LOG = logging.getLogger(__name__)
ENVIRONMENT_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")


@dataclass(frozen=True)
class RemoteProject:
    backend: Any
    root: str
    cwd: str


@dataclass(frozen=True)
class DockerExecBackend:
    executable: str
    container_id: str

    def execute(self, command: str, cwd: str = "", *, stdin_data: str | None = None,
                timeout: int = 60) -> dict[str, Any]:
        try:
            process = subprocess.run(
                [self.executable, "exec", "-i", "--workdir", cwd, self.container_id,
                 "/bin/bash", "-c", command],
                input=stdin_data, capture_output=True, text=True, check=False, timeout=timeout,
            )
            return {"returncode": process.returncode, "output": process.stdout + process.stderr}
        except subprocess.TimeoutExpired as error:
            return {"returncode": 124, "output": str(error)}


def _docker_image_id(executable: str, container_id: str) -> str | None:
    try:
        result = subprocess.run(
            [executable, "inspect", "--format", "{{.Image}}", container_id],
            capture_output=True, text=True, check=False, timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    image_id = result.stdout.strip()
    return image_id if result.returncode == 0 and re.fullmatch(r"sha256:[0-9a-f]{64}", image_id) else None


def trusted_backend_project(backend: Any, cwd: str, trust_path: Path) -> RemoteProject | None:
    """Find a project bound to this SSH or Docker backend and verify its physical path."""
    try:
        from tools.environments.ssh import SSHEnvironment
        from tools.environments.docker import DockerEnvironment
        if not isinstance(backend, (SSHEnvironment, DockerEnvironment)):
            return None
        if isinstance(backend, SSHEnvironment):
            identity = {"type": "ssh", "host": backend.host, "user": backend.user, "port": backend.port}
        else:
            container_id = getattr(backend, "_container_id", None)
            executable = getattr(backend, "_docker_exe", None)
            if not isinstance(container_id, str) or not isinstance(executable, str):
                return None
            image_id = _docker_image_id(executable, container_id)
            if image_id is None:
                return None
            identity = {"type": "docker", "image_id": image_id}
        trust_stat = trust_path.stat()
        if trust_stat.st_uid != os.getuid() or trust_stat.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
            LOG.warning("Remote project trust file has unsafe ownership or permissions")
            return None
        data = json.loads(trust_path.read_text())
        projects = data.get("projects", []) if isinstance(data, dict) else []
        if not isinstance(projects, list):
            return None
        for item in projects:
            if not isinstance(item, dict) or any(item.get(key) != value for key, value in identity.items()):
                continue
            root = item.get("root")
            if not isinstance(root, str) or not root.startswith("/") or ".." in PurePosixPath(root).parts:
                continue
            if not isinstance(cwd, str) or not cwd.startswith("/") or ".." in PurePosixPath(cwd).parts:
                continue
            resolved_root = backend.execute("builtin pwd -P", cwd=root, timeout=10)
            resolved_cwd = backend.execute("builtin pwd -P", cwd=cwd, timeout=10)
            if resolved_root.get("returncode") != 0 or resolved_cwd.get("returncode") != 0:
                continue
            root_path = PurePosixPath(resolved_root.get("output", "").strip())
            cwd_path = PurePosixPath(resolved_cwd.get("output", "").strip())
            if root_path.is_absolute() and cwd_path.is_relative_to(root_path):
                return RemoteProject(backend, str(root_path), str(cwd_path))
    except (ImportError, OSError, ValueError, TypeError, AttributeError) as error:
        LOG.debug("Remote project trust is unavailable: %s", error)
    return None


def _encoded(value: str) -> str:
    return base64.b64encode(value.encode("utf-8")).decode("ascii")


def run_project_hook(
    backend: Any, command: str, payload: dict[str, Any], project_cwd: str,
    timeout: int, environment: dict[str, str],
) -> subprocess.CompletedProcess[str] | None:
    """Run one hook and recover its exit code and streams from Hermes's merged output."""
    if not all(ENVIRONMENT_NAME.fullmatch(key) and isinstance(value, str)
               for key, value in environment.items()):
        LOG.warning("Remote project hook environment has an invalid entry")
        return None
    frame = f"__LIFEOS_HOOK_{uuid4().hex}__"
    input_text = "\n".join([
        _encoded(command), str(len(environment)),
        *(_encoded(f"{key}={value}") for key, value in environment.items()),
        json.dumps(payload, ensure_ascii=False),
    ])
    script = f"""
set +e
IFS= read -r encoded_command || exit 97
IFS= read -r -d '' hook_command < <(printf '%s' "$encoded_command" | base64 -d; printf '\\0')
IFS= read -r assignment_count || exit 97
for ((i=0; i<assignment_count; i++)); do
  IFS= read -r encoded_assignment || exit 97
  IFS= read -r -d '' assignment < <(printf '%s' "$encoded_assignment" | base64 -d; printf '\\0')
  export "$assignment" || exit 97
done
hook_stdout=$(mktemp) || exit 97
hook_stderr=$(mktemp) || exit 97
trap 'rm -f "$hook_stdout" "$hook_stderr"' EXIT
/bin/bash -c "$hook_command" >"$hook_stdout" 2>"$hook_stderr"
hook_status=$?
printf '\\n{frame}\\n%s\\n' "$hook_status"
base64 <"$hook_stdout" | tr -d '\\n'
printf '\\n'
base64 <"$hook_stderr" | tr -d '\\n'
printf '\\n{frame}_END\\n'
"""
    try:
        result = backend.execute(
            script, cwd=project_cwd, stdin_data=input_text,
            timeout=max(1, min(timeout, 300)),
        )
        output = result.get("output", "")
        if result.get("returncode") != 0:
            LOG.warning("Remote project hook transport exited %s", result.get("returncode"))
            return None
        start = output.rfind(f"\n{frame}\n")
        if start < 0:
            LOG.warning("Remote project hook transport did not return a result frame")
            return None
        body = output[start + len(frame) + 2:]
        end = body.find(f"\n{frame}_END")
        if end < 0:
            LOG.warning("Remote project hook transport returned an incomplete result frame")
            return None
        status, stdout, stderr = body[:end].split("\n", 2)
        return subprocess.CompletedProcess(
            args=["remote-project-hook"], returncode=int(status),
            stdout=base64.b64decode(stdout, validate=True).decode("utf-8", "replace"),
            stderr=base64.b64decode(stderr, validate=True).decode("utf-8", "replace"),
        )
    except (OSError, ValueError, TypeError, KeyError, UnicodeError) as error:
        LOG.warning("Remote project hook transport failed: %s", error)
        return None
