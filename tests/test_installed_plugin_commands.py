# ABOUTME: Exercises LifeOS commands through the stock Hermes launcher and plugin discovery.
# ABOUTME: Uses real HTTP requests and separate profiles with a managed dependency generation.

import base64
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


SOURCE = os.environ.get("LIFEOS_COMMAND_HERMES_SOURCE")
DEPENDENCIES = os.environ.get("LIFEOS_COMMAND_DEPENDENCIES")
ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(SOURCE and DEPENDENCIES, "Prepared Hermes and a dependency generation are required")
class InstalledPluginCommandTests(unittest.TestCase):
    def test_commands_preserve_profiles_inputs_images_and_selected_provider_failures(self):
        requests = []

        class Endpoint(BaseHTTPRequestHandler):
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                requests.append((self.path, body, self.headers.get("Authorization")))
                if self.path == "/api/show":
                    self.send_response(404)
                    self.end_headers()
                    return
                failed = body.get("model") == "unavailable"
                answer = {"error": {"message": "selected route unavailable"}} if failed else {
                    "id": "local-response", "object": "chat.completion", "model": body["model"],
                    "choices": [{"index": 0, "message": {"role": "assistant", "content": "READY"},
                                 "finish_reason": "stop"}],
                    "usage": {"prompt_tokens": 5, "completion_tokens": 1, "total_tokens": 6},
                }
                encoded = json.dumps(answer).encode()
                if body.get("stream") and not failed:
                    chunk = {"id": "local-response", "object": "chat.completion.chunk", "model": body["model"],
                             "choices": [{"index": 0, "delta": {"role": "assistant", "content": "READY"},
                                          "finish_reason": "stop"}]}
                    encoded = ("data: " + json.dumps(chunk) + "\n\ndata: [DONE]\n\n").encode()
                self.send_response(503 if failed else 200)
                self.send_header("Content-Type", "text/event-stream" if body.get("stream") and not failed else "application/json")
                self.send_header("Content-Length", str(len(encoded)))
                self.end_headers()
                self.wfile.write(encoded)

            def log_message(self, *_):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Endpoint)
        thread = threading.Thread(target=lambda: server.serve_forever(poll_interval=0.05), daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        with tempfile.TemporaryDirectory(prefix="lifeos installed commands ") as directory:
            root = Path(directory)
            source = root / "Hermes source 'café"
            shutil.copytree(SOURCE, source, ignore=shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache", ".hermes"))
            executable = root / "commands/hermes"
            executable.parent.mkdir()
            # The upstream launcher selects the recorded dependency generation at each start.
            code = (
                "import sys\nfrom pathlib import Path\n"
                f"sys.path.insert(0, {str(source)!r})\n"
                "from hermes_cli._launchers import _mint_shell_launcher, _launcher_script\n"
                f"assert _mint_shell_launcher('hermes', Path({str(executable.parent)!r}), "
                f"Path({sys._base_executable!r}), _launcher_script('hermes', Path({str(source)!r}), None))\n"
            )
            subprocess.run([sys.executable, "-c", code], check=True, capture_output=True, text=True)
            image = root / "image with spaces.png"
            image.write_bytes(base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Y9Wj9sAAAAASUVORK5CYII="))
            system = root / "system prompt.txt"
            system.write_text("Answer briefly from the file.")
            clean = {key: value for key, value in os.environ.items()
                     if not any(word in key for word in ("TOKEN", "KEY", "BASE_URL", "ANTHROPIC", "LIFEOS", "HERMES"))}
            clean["PATH"] = str(executable.parent) + os.pathsep + clean.get("PATH", "")
            profiles = []
            for name in ("A", "B"):
                home = root / name
                hermes = home / ".hermes"
                plugin = hermes / "plugins/lifeos-hook-bridge"
                plugin.parent.mkdir(parents=True)
                shutil.copytree(ROOT / "lifeos_hook_bridge", plugin, ignore=shutil.ignore_patterns("__pycache__"))
                (hermes / "config.yaml").write_text(
                    f"model:\n  provider: custom\n  default: model-{name}\n"
                    f"  base_url: http://127.0.0.1:{server.server_port}/v1\n"
                    f"  api_key: fixture-{name}\n"
                    "agent:\n  reasoning_effort: xhigh\nplugins:\n  enabled:\n    - lifeos-hook-bridge\n"
                    f"fallback_providers:\n  - provider: custom\n    model: fallback-{name}\n"
                    f"    base_url: http://127.0.0.1:{server.server_port}/v1\n    api_key: fixture-fallback\n"
                )
                install_key = hashlib.sha256(str(source.resolve()).encode()).hexdigest()[:16]
                state = hermes / "installs" / install_key
                state.mkdir(parents=True)
                generation = state / "environments/commands/venv"
                shutil.copytree(DEPENDENCIES, generation, symlinks=True)
                (state / "facts.json").write_text(json.dumps({"packages": {"venv": {"environment": str(generation)}}}))
                env = {**clean, "HOME": str(home), "HERMES_HOME": str(hermes),
                       "LIFEOS_CHILD_PROVIDER": "custom", "OPENAI_API_KEY": f"fixture-{name}",
                       "OPENAI_BASE_URL": f"http://127.0.0.1:{server.server_port}/v1"}
                profiles.append(env)
            for env, name in ((profiles[0], "A"), (profiles[1], "B"), (profiles[0], "A")):
                result = subprocess.run(
                    [str(executable), "lifeos-infer", "--print", "--model", f"model-{name}",
                     "--effort", "low", "--output-format", "json", "--system-prompt-file", str(system),
                     "--allowedTools", "Read"], input=f"@{image}\n\nSay READY.",
                    cwd=root, env=env, text=True, capture_output=True, timeout=60,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(json.loads(result.stdout)["result"], "READY")
                self.assertEqual(requests[-1][1]["model"], f"model-{name}")
                self.assertEqual(requests[-1][2], f"Bearer fixture-{name}")
                self.assertEqual(requests[-1][1]["messages"][0]["content"], system.read_text())
                self.assertEqual(requests[-1][1]["messages"][1]["content"][0]["type"], "image_url")
                self.assertEqual(requests[-1][1]["messages"][1]["content"][1]["text"], "Say READY.")
            probe = subprocess.run([str(executable), "lifeos-probe", "--check"], cwd=root,
                                   env=profiles[0], text=True, capture_output=True, timeout=60)
            self.assertEqual(probe.returncode, 1, probe.stdout + probe.stderr)
            self.assertIn("NEVER RUN", probe.stderr)
            main_probe = subprocess.run([str(executable), "lifeos-probe", "--check-main-rung", "fable"],
                                        cwd=root, env=profiles[0], text=True, capture_output=True, timeout=60)
            self.assertEqual(main_probe.returncode, 0, main_probe.stdout + main_probe.stderr)
            self.assertIn("HOLDS", main_probe.stdout)
            live_probe = subprocess.run([str(executable), "lifeos-probe", "--run"],
                                        cwd=root, env=profiles[0], text=True, capture_output=True, timeout=60)
            self.assertEqual(live_probe.returncode, 0, live_probe.stdout + live_probe.stderr)
            self.assertIn("HOLDS", live_probe.stdout)
            failure = subprocess.run(
                [str(executable), "lifeos-infer", "--print", "--model", "unavailable", "--effort", "low",
                 "--output-format", "json", "--system-prompt", "Answer briefly."], input="Say READY.",
                cwd=root, env=profiles[0], text=True, capture_output=True, timeout=60,
            )
            self.assertNotEqual(failure.returncode, 0)
            self.assertIn("selected route unavailable", failure.stderr)
            self.assertFalse(any(body.get("model", "").startswith("fallback-") for _, body, _ in requests))
