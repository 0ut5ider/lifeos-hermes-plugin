# ABOUTME: Verifies development capture with real disposable SSH and Docker targets.
# ABOUTME: Checks detached outcomes and keeps synthetic raw evidence private.

import gzip
import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path

HOST = Path.home() / "workspace/hermes-agent"
sys.path.insert(0, str(HOST))
import hermes_bootstrap

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from lifeos_hook_bridge.bridge import HookBridge
from lifeos_hook_bridge.remote_hooks import DockerExecBackend, RemoteProject
from tools.environments.ssh import SSHEnvironment
from hook_capture.instrument import CURRENT


class CaptureDockerBackend:
    def __init__(self, container):
        self._docker_exe = "/usr/bin/docker"
        self._container_id = container

    def execute(self, *args, **kwargs):
        return DockerExecBackend(self._docker_exe, self._container_id).execute(*args, **kwargs)


def main():
    capture = Path.home() / ".local/state/lifeos-development-capture"
    fixture = Path(os.environ["CAPTURE_REMOTE_FIXTURE"])
    root = capture / "probes" / ("remote-" + uuid.uuid4().hex)
    root.mkdir(parents=True, mode=0o700)
    settings = root / "settings.json"
    settings.write_text('{"hooks":{}}')
    bridge = HookBridge(settings, root)
    backends = {
        "ssh": SSHEnvironment(host="127.0.0.1", user="lifeos-install-probe",
                              cwd=os.environ["CAPTURE_REMOTE_PROJECT"],
                              key_path=str(fixture / "key"), probe_only=True),
        "docker": CaptureDockerBackend(os.environ["CAPTURE_REMOTE_CONTAINER"]),
    }
    reports = []
    secret = "REMOTE-PROBE-API-SECRET-731492"
    try:
        for kind, backend in backends.items():
            cwd = os.environ["CAPTURE_REMOTE_PROJECT"] if kind == "ssh" else "/tmp"
            for succeeds in (True, False):
                session = f"capture-remote-{kind}-{'success' if succeeds else 'failure'}-{uuid.uuid4().hex}"
                invocation = uuid.uuid4().hex
                CURRENT.set({"session_id": session, "native_event": "UserPromptSubmit",
                             "invocation_id": invocation, "registration_id": "development-probe:" + kind,
                             "target_kind": kind, "workspace": cwd, "evidence_level": "development-probe"})
                marker = "CAPTURE-" + kind.upper() + "-CONTEXT"
                command = ("python3 -c \"import json,os,sys;print(json.dumps({'hookSpecificOutput':"
                           "{'hookEventName':'UserPromptSubmit','additionalContext':'" + marker + "'}}));"
                           "print(os.environ['API_KEY'],file=sys.stderr)\"")
                project = RemoteProject(backend, cwd, cwd if succeeds else cwd + "/missing-capture-workdir")
                bridge._run_remote_async(project, command,
                    {"hook_event_name": "UserPromptSubmit", "session_id": session, "prompt": "remote capture probe"},
                    10, {"API_KEY": secret})
                terminal = None
                for _ in range(300):
                    for path in capture.glob("runs/*/events/*/*.jsonl"):
                        for line in path.read_text().splitlines():
                            try:
                                event = json.loads(line)
                            except ValueError:
                                continue
                            if event.get("invocation_id") == invocation and event["stage"] in {"hook.completed", "hook.failed"}:
                                terminal = event
                    if terminal:
                        break
                    time.sleep(.05)
                assert terminal, (kind, "missing terminal capture")
                if succeeds:
                    assert terminal["stage"] == "hook.completed", terminal
                    assert terminal["exit_code"] == 0, terminal
                    contexts = []
                    for _ in range(50):
                        contexts = bridge._drain_async_context(session)
                        if contexts:
                            break
                        time.sleep(.02)
                    assert marker in contexts, contexts
                    raw = gzip.decompress((capture / terminal["data_ref"]["path"]).read_bytes()).decode()
                    assert secret not in raw, "Unredacted declared credential in detached output"
                    assert "[REDACTED]" in raw, "Missing redacted stderr evidence"
                else:
                    assert terminal["stage"] == "hook.failed", terminal
                reports.append({"backend": kind, "succeeds": succeeds, "stage": terminal["stage"],
                                "invocation_id": invocation, "process_id": terminal["process_id"]})
    finally:
        backends["ssh"].cleanup()
        bridge.close()
    print(json.dumps({"cases": reports, "passed": True}))


if __name__ == "__main__":
    main()
