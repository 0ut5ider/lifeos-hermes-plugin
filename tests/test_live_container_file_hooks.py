# ABOUTME: Checks LifeOS file hook paths around real Docker read, write, edit, delete, and move tools.
# ABOUTME: Uses a disposable project and removes its container after the test.

import json
import os
import shlex
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from lifeos_hook_bridge.bridge import HookBridge


class LiveContainerFileHookTests(unittest.TestCase):
    def test_docker_file_tools_and_hooks_use_the_same_path(self):
        image = os.environ.get("LIFEOS_DOCKER_PROBE_IMAGE")
        if not image:
            self.skipTest("disposable Docker image is required")

        from tools.environments.docker import DockerEnvironment
        from tools.file_tools import clear_file_ops_cache, patch_tool, read_file_tool, write_file_tool
        from tools.terminal_tool import _active_environments, _env_lock

        project = "/tmp/lifeos-container-file-probe"
        path = f"{project}/notes.txt"
        session = "container-file-hook-probe"
        env = DockerEnvironment(image=image, cwd=project, task_id=session,
                                network=False, persistent_filesystem=False)
        with _env_lock:
            _active_environments["default"] = env
        try:
            prepared = env.execute("mkdir -p .", cwd=project, timeout=20)
            self.assertEqual(prepared["returncode"], 0, prepared["output"])
            with TemporaryDirectory(prefix="container-file-hooks-") as directory:
                root = Path(directory)
                marker = root / "events.jsonl"
                recorder = root / "record.py"
                recorder.write_text(
                    "# ABOUTME: Records file hook payloads from a disposable Docker workspace.\n"
                    "# ABOUTME: Writes one JSON payload per received event.\n"
                    "import json,sys\nfrom pathlib import Path\n"
                    f"with Path({str(marker)!r}).open('a') as out: "
                    "out.write(json.dumps(json.load(sys.stdin))+'\\n')\n"
                )
                command = f"{shlex.quote(sys.executable)} {shlex.quote(str(recorder))}"
                settings = root / "settings.json"
                settings.write_text(json.dumps({"hooks": {
                    "PreToolUse": [{"hooks": [{"type": "command", "command": command}]}],
                    "PostToolUse": [{"hooks": [{"type": "command", "command": command}]}],
                }}))
                bridge = HookBridge(settings, root)
                try:
                    write_args = {"path": path, "content": "first\n"}
                    self.assertIsNone(bridge.pre_tool_call("write_file", write_args, session_id=session, task_id="default"))
                    written = write_file_tool(path, "first\n", task_id="default", session_id=session)
                    bridge.post_tool_call("write_file", write_args, written, session_id=session, task_id="default")
                    self.assertEqual(env.execute("cat notes.txt", cwd=project, timeout=20)["output"], "first\n")

                    read_args = {"path": path}
                    self.assertIsNone(bridge.pre_tool_call("read_file", read_args, session_id=session, task_id="default"))
                    read = read_file_tool(path, task_id="default")
                    self.assertIn("first", read)
                    bridge.post_tool_call("read_file", read_args, read, session_id=session, task_id="default")

                    edit_args = {"mode": "replace", "path": path, "old_string": "first", "new_string": "second"}
                    self.assertIsNone(bridge.pre_tool_call("patch", edit_args, session_id=session, task_id="default"))
                    edited = patch_tool(task_id="default", session_id=session, **edit_args)
                    bridge.post_tool_call("patch", edit_args, edited, session_id=session, task_id="default")
                    self.assertEqual(env.execute("cat notes.txt", cwd=project, timeout=20)["output"], "second\n")

                    delete_path = f"{project}/delete.txt"
                    moved_path = f"{project}/moved.txt"
                    prepared = env.execute("printf remove > delete.txt", cwd=project, timeout=20)
                    self.assertEqual(prepared["returncode"], 0, prepared["output"])
                    patch_args = {"mode": "patch", "patch": (
                        "*** Begin Patch\n"
                        f"*** Delete File: {delete_path}\n"
                        f"*** Move File: {path} -> {moved_path}\n"
                        "*** End Patch"
                    )}
                    self.assertIsNone(bridge.pre_tool_call("patch", patch_args, session_id=session, task_id="default"))
                    patched = patch_tool(task_id="default", session_id=session, **patch_args)
                    bridge.post_tool_call("patch", patch_args, patched, session_id=session, task_id="default")
                    check = env.execute("test ! -e delete.txt && test ! -e notes.txt && cat moved.txt",
                                        cwd=project, timeout=20)
                    self.assertEqual(check["returncode"], 0, patched)
                    self.assertEqual(check["output"], "second\n")

                    events = [json.loads(line) for line in marker.read_text().splitlines()]
                    file_events = [event for event in events if event.get("tool_name") in {"Write", "Read", "Edit"}]
                    self.assertEqual(
                        [(event["hook_event_name"], event["tool_name"], event["tool_input"]["file_path"])
                         for event in file_events[:6]],
                        [(phase, tool, path) for tool in ("Write", "Read", "Edit")
                         for phase in ("PreToolUse", "PostToolUse")],
                    )
                    for phase in ("PreToolUse", "PostToolUse"):
                        paths = [event["tool_input"]["file_path"] for event in file_events[6:]
                                 if event["hook_event_name"] == phase and event["tool_name"] == "Edit"]
                        self.assertCountEqual(paths, (delete_path, path, moved_path))
                finally:
                    bridge.close()
        finally:
            clear_file_ops_cache("default")
            with _env_lock:
                _active_environments.pop("default", None)
            env.cleanup(force_remove=True)
            self.assertTrue(env.wait_for_cleanup(timeout=30))

    def test_docker_web_cache_read_reaches_webfetch_hook(self):
        image = os.environ.get("LIFEOS_DOCKER_PROBE_IMAGE")
        if not image:
            self.skipTest("disposable Docker image is required")

        from hermes_constants import get_hermes_dir
        from tools.credential_files import to_agent_visible_cache_path
        from tools.environments.docker import DockerEnvironment
        from tools.file_tools import clear_file_ops_cache, read_file_tool
        from tools.terminal_scope import reset_terminal_scope, set_terminal_scope
        from tools.terminal_tool import _active_environments, _env_lock

        project = "/tmp/lifeos-container-cache-probe"
        session = "container-cache-hook-probe"
        env = DockerEnvironment(image=image, cwd=project, task_id=session,
                                network=False, persistent_filesystem=False)
        with _env_lock:
            _active_environments["default"] = env
        cache_file = None
        token = set_terminal_scope({"TERMINAL_ENV": "docker"})
        try:
            cache_dir = get_hermes_dir("cache/web", "web_cache")
            cache_dir.mkdir(parents=True, exist_ok=True)
            cache_file = cache_dir / f"lifeos-cache-probe-{uuid4().hex}.md"
            cache_file.write_text("CACHE_PROBE_CONTENT\n")
            visible_path = to_agent_visible_cache_path(str(cache_file))
            self.assertTrue(visible_path.startswith("/root/.hermes/cache/web/"), visible_path)
            with TemporaryDirectory(prefix="container-cache-hook-") as directory:
                root = Path(directory)
                marker = root / "webfetch.json"
                recorder = root / "record.py"
                recorder.write_text(
                    "# ABOUTME: Records a cached web read routed to the LifeOS WebFetch matcher.\n"
                    "# ABOUTME: Writes the hook payload for a disposable Docker test.\n"
                    "import json,sys\nfrom pathlib import Path\n"
                    f"Path({str(marker)!r}).write_text(json.dumps(json.load(sys.stdin)))\n"
                )
                settings = root / "settings.json"
                settings.write_text(json.dumps({"hooks": {"PostToolUse": [{
                    "matcher": "WebFetch", "hooks": [{
                        "type": "command", "command": f"{shlex.quote(sys.executable)} {shlex.quote(str(recorder))}",
                    }],
                }]}}))
                bridge = HookBridge(settings, root)
                try:
                    result = read_file_tool(visible_path, task_id="default")
                    self.assertIn("CACHE_PROBE_CONTENT", result)
                    bridge.post_tool_call("read_file", {"path": visible_path}, result,
                                          session_id=session, task_id="default")
                    payload = json.loads(marker.read_text())
                    self.assertEqual(payload["tool_name"], "WebFetch")
                    self.assertEqual(payload["tool_input"]["file_path"], visible_path)
                    self.assertIn("CACHE_PROBE_CONTENT", payload["tool_response"]["content"])
                finally:
                    bridge.close()
        finally:
            reset_terminal_scope(token)
            if cache_file is not None:
                cache_file.unlink(missing_ok=True)
            clear_file_ops_cache("default")
            with _env_lock:
                _active_environments.pop("default", None)
            env.cleanup(force_remove=True)
            self.assertTrue(env.wait_for_cleanup(timeout=30))
