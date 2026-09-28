# ABOUTME: Checks native WebFetch matching for real browser result classes.
# ABOUTME: Serves a disposable page on loopback and closes its browser session.

import json
import os
import shlex
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from lifeos_hook_bridge.bridge import HookBridge


class ProbePage(BaseHTTPRequestHandler):
    def do_GET(self):
        body = (
            b"<html><head><title>LifeOS Browser Probe</title></head><body>"
            b"<h1>PAGE_SAFETY_PROBE</h1>"
            b"<img src='/one.gif' alt='IMAGE_SAFETY_PROBE'>"
            b"<script>console.log('CONSOLE_SAFETY_PROBE')</script>"
            b"</body></html>"
        ) if self.path == "/" else b"GIF89a"
        self.send_response(200)
        self.send_header("Content-Type", "text/html" if self.path == "/" else "image/gif")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_):
        pass


@unittest.skipUnless(os.environ.get("LIFEOS_BROWSER_PROBE") == "1", "real browser fixture is required")
class LiveBrowserResultSafetyTests(unittest.TestCase):
    def test_content_bearing_browser_results_reach_webfetch_matcher(self):
        from tools import browser_tool_lifecycle as lifecycle
        from tools.browser_tool import browser_console, browser_get_images, browser_navigate, browser_snapshot
        from tools.browser_tool_install import check_browser_requirements

        self.assertTrue(check_browser_requirements())
        server = ThreadingHTTPServer(("127.0.0.1", 0), ProbePage)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        task_id = f"lifeos-browser-results-{uuid4().hex}"
        try:
            with TemporaryDirectory(prefix="browser-result-safety-") as directory:
                root = Path(directory)
                marker = root / "events.jsonl"
                recorder = root / "record.py"
                recorder.write_text(
                    "# ABOUTME: Records a native WebFetch matcher input from a browser result.\n"
                    "# ABOUTME: Appends one JSON payload to a disposable local file.\n"
                    "import json,sys\nfrom pathlib import Path\n"
                    f"with Path({str(marker)!r}).open('a') as out: "
                    "out.write(json.dumps(json.load(sys.stdin))+'\\n')\n"
                )
                settings = root / "settings.json"
                settings.write_text(json.dumps({"hooks": {"PostToolUse": [{
                    "matcher": "WebFetch", "hooks": [{
                        "type": "command", "command": f"{shlex.quote(sys.executable)} {shlex.quote(str(recorder))}",
                    }],
                }]}}))
                bridge = HookBridge(settings, root)
                try:
                    url = f"http://127.0.0.1:{server.server_port}/"
                    results = {
                        "browser_navigate": browser_navigate(url, task_id=task_id),
                        "browser_snapshot": browser_snapshot(full=True, task_id=task_id),
                        "browser_console": browser_console(task_id=task_id),
                        "browser_get_images": browser_get_images(task_id=task_id),
                    }
                    for name, result in results.items():
                        self.assertTrue(json.loads(result).get("success"), (name, result))
                        bridge.augment_tool_result(name, {"url": url}, result, result,
                                                   session_id=task_id, tool_call_id=name)
                    payloads = [json.loads(line) for line in marker.read_text().splitlines()]
                    self.assertEqual(len(payloads), len(results))
                    self.assertEqual([payload["tool_name"] for payload in payloads], ["WebFetch"] * len(results))
                    self.assertIn("PAGE_SAFETY_PROBE", json.dumps(payloads[0]))
                    self.assertIn("PAGE_SAFETY_PROBE", json.dumps(payloads[1]))
                    self.assertIn("CONSOLE_SAFETY_PROBE", json.dumps(payloads[2]))
                    self.assertIn("IMAGE_SAFETY_PROBE", json.dumps(payloads[3]))
                finally:
                    bridge.close()
        finally:
            lifecycle._cleanup_single_browser_session(task_id)
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    unittest.main()
