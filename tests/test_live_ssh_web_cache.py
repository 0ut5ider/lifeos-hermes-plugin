# ABOUTME: Checks LifeOS WebFetch safety routing for a real SSH web-cache read.
# ABOUTME: Uses a disposable loopback SSH session and removes its cache file afterward.

import json
import os
import shlex
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from lifeos_hook_bridge.bridge import HookBridge


SSH_HOST = os.environ.get("LIFEOS_SSH_PROBE_HOST")
SSH_USER = os.environ.get("LIFEOS_SSH_PROBE_USER")
SSH_KEY = os.environ.get("LIFEOS_SSH_PROBE_KEY")


@unittest.skipUnless(all((SSH_HOST, SSH_USER, SSH_KEY)), "disposable SSH endpoint is required")
class LiveSshWebCacheTests(unittest.TestCase):
    def test_ssh_web_cache_read_reaches_webfetch_hook(self):
        from hermes_constants import get_hermes_dir
        from tools.credential_files import to_agent_visible_cache_path
        from tools.environments.ssh import SSHEnvironment
        from tools.file_tools import clear_file_ops_cache, read_file_tool
        from tools.terminal_scope import reset_terminal_scope, set_terminal_scope
        from tools.terminal_tool import _active_environments, _env_lock

        session = f"ssh-web-cache-{uuid4().hex}"
        env = SSHEnvironment(host=SSH_HOST, user=SSH_USER, key_path=SSH_KEY,
                             cwd="/tmp/lifeos-ssh-cache-probe-20260928", probe_only=True)
        with _env_lock:
            self.assertNotIn("default", _active_environments)
            _active_environments["default"] = env
        token = set_terminal_scope({"TERMINAL_ENV": "ssh"})
        cache_file = None
        try:
            cache_dir = get_hermes_dir("cache/web", "web_cache")
            cache_dir.mkdir(parents=True, exist_ok=True)
            cache_file = cache_dir / f"lifeos-ssh-cache-{uuid4().hex}.md"
            cache_file.write_text("SSH_CACHE_CONTENT\n")
            visible_path = to_agent_visible_cache_path(str(cache_file))
            self.assertTrue(visible_path.startswith("~/.hermes/cache/web/"), visible_path)

            with TemporaryDirectory(prefix="ssh-web-cache-hook-") as directory:
                root = Path(directory)
                marker = root / "webfetch.json"
                recorder = root / "record.py"
                recorder.write_text(
                    "# ABOUTME: Records a cached SSH web read for the native matcher.\n"
                    "# ABOUTME: Writes its hook payload to a disposable local file.\n"
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
                    self.assertIn("SSH_CACHE_CONTENT", result)
                    bridge.post_tool_call("read_file", {"path": visible_path}, result,
                                          session_id=session, task_id="default")
                    self.assertTrue(marker.exists(), "WebFetch safety matcher did not run")
                    payload = json.loads(marker.read_text())
                    self.assertEqual(payload["tool_name"], "WebFetch")
                    self.assertIn("SSH_CACHE_CONTENT", payload["tool_response"]["content"])
                finally:
                    bridge.close()
        finally:
            reset_terminal_scope(token)
            if cache_file is not None:
                cache_file.unlink(missing_ok=True)
            clear_file_ops_cache("default")
            with _env_lock:
                _active_environments.pop("default", None)
            env.cleanup()


if __name__ == "__main__":
    unittest.main()
