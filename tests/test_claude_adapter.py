# ABOUTME: Checks the child Claude launcher maps LifeOS model rungs to local reasoning effort.
# ABOUTME: Uses an isolated home and a recording executable, with no model request.

import json
import os
import base64
import subprocess
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ADAPTER = Path(__file__).resolve().parents[1] / "lifeos_hook_bridge/bin/claude"


class ClaudeAdapterTests(unittest.TestCase):
    def test_direct_inference_uses_local_gateway_without_claude_cli(self):
        requests = []

        class Gateway(BaseHTTPRequestHandler):
            def do_POST(self):
                requests.append((self.path, dict(self.headers), json.loads(self.rfile.read(int(self.headers["Content-Length"])))))
                body = {
                    "type": "message", "model": "local-model", "stop_reason": "end_turn",
                    "content": [{"type": "thinking", "thinking": "private"}, {"type": "text", "text": "READY"}],
                    "usage": {"input_tokens": 5, "output_tokens": 8},
                }
                encoded = json.dumps(body).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(encoded)))
                self.end_headers()
                self.wfile.write(encoded)

            def log_message(self, *_):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Gateway)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)

        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            (home / ".local/bin").mkdir(parents=True)
            (home / ".config/lifeos-hook-bridge").mkdir(parents=True)
            (home / ".local/bin/claude").write_text("#!/bin/sh\nexit 99\n")
            (home / ".local/bin/claude").chmod(0o700)
            (home / ".config/lifeos-hook-bridge/model.env").write_text(
                f"ANTHROPIC_BASE_URL=http://127.0.0.1:{server.server_port}\n"
                "ANTHROPIC_AUTH_TOKEN=test-token\nANTHROPIC_MODEL=local-model\n"
                "LIFEOS_CHILD_INFERENCE_DIRECT=1\n"
            )
            image = home / "one.png"
            image.write_bytes(base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Y9Wj9sAAAAASUVORK5CYII="))
            result = subprocess.run(
                [str(ADAPTER), "--print", "--model", "haiku", "--effort", "high",
                 "--allowedTools", "Read", "--output-format", "json",
                 "--system-prompt", "Answer briefly."],
                input=f"@{image}\n\nSay READY.", text=True, capture_output=True,
                env={**os.environ, "HOME": str(home)}, timeout=10,
            )
            system_prompt_file = home / "system-prompt.txt"
            system_prompt_file.write_text("Use the file prompt.")
            file_result = subprocess.run(
                [str(ADAPTER), "--print", "--model", "sonnet", "--effort", "high",
                 "--tools", "", "--output-format", "json",
                 "--system-prompt-file", str(system_prompt_file)],
                input="Say READY.", text=True, capture_output=True,
                env={**os.environ, "HOME": str(home)}, timeout=10,
            )
            future_result = subprocess.run(
                [str(ADAPTER), "--print", "--model", "fable", "--effort", "low",
                 "--tools", "", "--output-format", "json", "--system-prompt", "Answer briefly."],
                input="Say READY.", text=True, capture_output=True,
                env={**os.environ, "HOME": str(home), "LIFEOS_MODEL_TIER_MAP": json.dumps({
                    "fable": {"model": "future-local", "effort": "max"},
                })}, timeout=10,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(file_result.returncode, 0, file_result.stderr)
        self.assertEqual(future_result.returncode, 0, future_result.stderr)
        envelope = json.loads(result.stdout)
        self.assertEqual(envelope["result"], "READY")
        self.assertEqual(envelope["modelUsage"]["local-model"]["outputTokens"], 8)
        self.assertEqual(len(requests), 3)
        path, headers, request = requests[0]
        self.assertEqual(path, "/v1/messages")
        self.assertEqual(headers["Authorization"], "Bearer test-token")
        self.assertEqual(request["output_config"]["effort"], "low")
        self.assertEqual(request["system"], "Answer briefly.")
        self.assertEqual(request["messages"][0]["content"][0]["type"], "image")
        self.assertEqual(request["messages"][0]["content"][1]["text"], "Say READY.")
        self.assertEqual(requests[1][2]["system"], "Use the file prompt.")
        self.assertEqual(requests[1][2]["output_config"]["effort"], "medium")
        self.assertEqual(requests[2][2]["model"], "future-local")
        self.assertEqual(requests[2][2]["output_config"]["effort"], "max")

    def test_lifeos_model_rungs_map_to_local_effort(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            (home / ".local/bin").mkdir(parents=True)
            (home / ".config/lifeos-hook-bridge").mkdir(parents=True)
            (home / ".config/lifeos-hook-bridge/model.env").write_text(
                "ANTHROPIC_MODEL=local-model\n"
            )
            target = home / ".local/bin/claude"
            target.write_text(
                "#!/usr/bin/env python3\n"
                "import json,sys\n"
                "print(json.dumps(sys.argv[1:]))\n"
            )
            target.chmod(0o700)
            expected = {
                "haiku": "low",
                "sonnet": "medium",
                "opus": "xhigh",
                "claude-fable-5": "xhigh",
            }
            for requested_model, effort in expected.items():
                with self.subTest(model=requested_model):
                    result = subprocess.run(
                        [str(ADAPTER), "--print", "--model", requested_model,
                         "--effort", "high", "hello"],
                        text=True, capture_output=True, check=True,
                        env={**os.environ, "HOME": str(home)},
                    )
                    self.assertEqual(
                        json.loads(result.stdout),
                        ["--print", "--model", "local-model", "--effort", effort, "hello"],
                    )
            equals_form = subprocess.run(
                [str(ADAPTER), "--model=claude-opus-5", "--effort=high", "hello"],
                text=True, capture_output=True, check=True,
                env={**os.environ, "HOME": str(home)},
            )
            self.assertEqual(
                json.loads(equals_form.stdout),
                ["--model=local-model", "--effort=xhigh", "hello"],
            )

    def test_plugin_tier_settings_select_distinct_models_and_efforts(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            (home / ".local/bin").mkdir(parents=True)
            (home / ".config/lifeos-hook-bridge").mkdir(parents=True)
            (home / ".config/lifeos-hook-bridge/model.env").write_text("")
            target = home / ".local/bin/claude"
            target.write_text("#!/usr/bin/env python3\nimport json,sys\nprint(json.dumps(sys.argv[1:]))\n")
            target.chmod(0o700)
            tiers = {
                "haiku": {"model": "fast-local", "effort": "minimal"},
                "sonnet": {"model": "balanced-local", "effort": "high"},
                "opus": {"model": "large-local", "effort": "max"},
                "fable": {"model": "largest-local", "effort": "ultra"},
            }
            for tier, route in tiers.items():
                with self.subTest(tier=tier):
                    result = subprocess.run(
                        [str(ADAPTER), "--model", tier, "--effort", "medium", "hello"],
                        text=True, capture_output=True, check=True,
                        env={**os.environ, "HOME": str(home), "LIFEOS_MODEL_TIER_MAP": json.dumps(tiers)},
                    )
                    self.assertEqual(
                        json.loads(result.stdout),
                        ["--model", route["model"], "--effort", route["effort"], "hello"],
                    )


if __name__ == "__main__":
    unittest.main()
