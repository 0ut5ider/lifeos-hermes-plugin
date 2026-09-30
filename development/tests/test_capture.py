# ABOUTME: Verifies private development evidence using real hook processes.
# ABOUTME: Compares traced behavior with the unchanged LifeOS bridge.

import gzip
import base64
import json
import os
import subprocess
import sys
import tempfile
import unittest
import threading
import time
import venv
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLUGIN = (ROOT / "lifeos_hook_bridge").resolve()
sys.path.insert(0, str(ROOT / "development"))


class EvidenceTests(unittest.TestCase):
    def test_credential_fields_inside_json_stdin_and_stdout_are_redacted(self):
        from hook_capture.store import safe
        from hook_capture.instrument import transport_input, transport_output
        value = "UNREGISTERED-TOOL-API-KEY-731"
        body = json.dumps({"tool_input": {"api_key": value, "apiKey": value,
                           "accessToken": value, "clientSecret": value}, "prompt": "keep this prompt"})
        clean = safe({"input": body, "stdout": body})
        self.assertNotIn(value, str(clean))
        self.assertEqual(json.loads(clean["input"])["prompt"], "keep this prompt")
        encoded = base64.b64encode(b"true").decode()
        wire = encoded + "\n0\n" + body
        self.assertNotIn(value, transport_input(wire, []))
        marker = "__LIFEOS_HOOK_" + "b" * 32 + "__"
        wire = "\n".join(("", marker, "0", base64.b64encode(body.encode()).decode(), "", marker + "_END"))
        decoded = base64.b64decode(transport_output(wire, []).splitlines()[3]).decode()
        self.assertNotIn(value, decoded)
        self.assertNotIn(value, safe('{"api_key":"' + value + '"'))

    def test_encoded_transport_credentials_are_removed_before_storage(self):
        from hook_capture.instrument import transport_input, transport_output
        encode = lambda text: base64.b64encode(text.encode()).decode()
        secret = "CANARY-CREDENTIAL-9472"
        wire = "\n".join((encode("echo " + secret), "1", encode("PRIVATE_KEY=" + secret), '{"prompt":"p"}'))
        clean = transport_input(wire, [secret])
        self.assertNotIn(secret, base64.b64decode(clean.splitlines()[0]).decode())
        self.assertEqual(base64.b64decode(clean.splitlines()[2]).decode(), "PRIVATE_KEY=[REDACTED]")
        marker = "__LIFEOS_HOOK_" + "a" * 32 + "__"
        wire = "\n".join(("", marker, "0", encode("out-" + secret), encode("err-" + secret), marker + "_END", ""))
        clean = transport_output(wire, [secret])
        self.assertEqual(base64.b64decode(clean.splitlines()[3]).decode(), "out-[REDACTED]")
        self.assertEqual(base64.b64decode(clean.splitlines()[4]).decode(), "err-[REDACTED]")
        truncated = "\n".join(("", marker, "0", encode(secret)))
        self.assertEqual(base64.b64decode(transport_output(truncated, [secret]).splitlines()[3]).decode(), "[REDACTED]")

    def test_artifacts_are_complete_private_and_credentials_are_removed(self):
        from hook_capture.store import Recorder
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            recorder = Recorder(root, "test-run", secrets=["CANARY-CREDENTIAL-9472"])
            value = {"prompt": "p" * 1100000, "stdout": "CANARY-CREDENTIAL-9472",
                     "authorization": "Bearer anything", "max_tokens": 4000}
            ref = recorder.artifact(value)
            loaded = json.loads(gzip.decompress((root / ref["path"]).read_bytes()))
            self.assertEqual(loaded["prompt"], value["prompt"])
            self.assertEqual(loaded["stdout"], "[REDACTED]")
            self.assertEqual(loaded["authorization"], "[REDACTED]")
            self.assertEqual(loaded["max_tokens"], 4000)
            self.assertEqual((root / ref["path"]).stat().st_mode & 0o777, 0o600)
            self.assertEqual(ref, recorder.artifact(value))
            dynamic = "DYNAMIC-CREDENTIAL-918342"
            ref = recorder.artifact({"stdout": dynamic, "environment": {"API_KEY": dynamic}})
            self.assertNotIn(dynamic, gzip.decompress((root / ref["path"]).read_bytes()).decode())
            ref = recorder.artifact({"stdout": dynamic})
            self.assertNotIn(dynamic, gzip.decompress((root / ref["path"]).read_bytes()).decode())

    def test_index_handles_a_partial_tail_and_reports_missing_completion(self):
        from hook_capture.store import Recorder
        from hook_capture.analysis import rebuild, summary
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            recorder = Recorder(root, "test-run")
            recorder.emit("hook.started", invocation_id="unfinished", registration_id="reg")
            recorder.emit("hook.completed", invocation_id="done", exit_code=2, status="intervention")
            with recorder.event_path.open("ab") as stream:
                stream.write(b'{"partial":')
            index = rebuild(root)
            report = summary(index)
            self.assertEqual(report["incomplete_invocations"], 1)
            self.assertEqual(report["partial_tails"], 1)
            self.assertEqual(report["statuses"]["intervention"], 1)


class OverlayTests(unittest.TestCase):
    def run_bridge(self, hooks, action, *, traced=True, setup=""):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        settings = root / "settings.json"
        settings.write_text(json.dumps({"hooks": hooks}))
        config = {"enabled": True, "root": str(root / "capture"), "run_id": "test-run",
                  "plugin_root": str(PLUGIN), "host_root": "",
                  "fingerprints": {}}
        import hashlib
        for name in ("bridge.py", "bin/hook_runner.py", "remote_hooks.py", "__init__.py"):
            p = PLUGIN / name
            config["fingerprints"][str(p)] = hashlib.sha256(p.read_bytes()).hexdigest()
        configuration = root / "capture.json"
        configuration.write_text(json.dumps(config))
        code = ("from hook_capture.instrument import install\n"
                f"install({str(configuration)!r})\n" if traced else "")
        code += (setup + "\nfrom pathlib import Path\nfrom lifeos_hook_bridge.bridge import HookBridge\n"
                 f"bridge=HookBridge(Path({str(settings)!r}),Path({str(root)!r}))\n"
                 f"result={action}\nprint('OUTCOME:'+__import__('json').dumps(result))\nbridge.close()\n")
        env = dict(os.environ, PYTHONPATH=os.pathsep.join((str(ROOT / "development"), str(ROOT))))
        result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                                env=env, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        events = []
        for p in (root / "capture").glob("runs/*/events/*/*.jsonl"):
            events.extend(json.loads(line) for line in p.read_text().splitlines())
        return root, result.stdout, events

    def test_duplicate_commands_and_skips_have_exact_distinct_identities(self):
        command = "printf '{\"hookSpecificOutput\":{\"hookEventName\":\"PreToolUse\",\"permissionDecision\":\"deny\"}}'"
        hooks = {"PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": command},
                                                               {"type": "command", "command": command}]},
                               {"matcher": "Read", "hooks": [{"type": "command", "command": "true"}]}]}
        action = "bridge.pre_tool_call('terminal',{'command':'echo hi'},session_id='session')"
        _, baseline, _ = self.run_bridge(hooks, action, traced=False)
        _, observed, events = self.run_bridge(hooks, action)
        self.assertEqual(baseline, observed)
        completed = [e for e in events if e["stage"] == "hook.completed"]
        self.assertEqual(len(completed), 2)
        self.assertEqual(len({e["registration_id"] for e in completed}), 2)
        self.assertTrue(all(e.get("callback_id") for e in completed))
        parsed = [e for e in events if e["stage"] == "response.parsed.returned"]
        self.assertEqual({e.get("invocation_id") for e in parsed}, {e["invocation_id"] for e in completed})
        skipped = [e for e in events if e["stage"] == "registration.skipped"]
        self.assertTrue(any(e["reason"] == "matcher_mismatch" for e in skipped))

    def test_large_stdout_stderr_and_timeout_evidence_precede_conversion(self):
        command = "python3 -c \"import sys;sys.stdout.write('o'*1100000);sys.stderr.write('e'*1100000)\""
        hooks = {"PreToolUse": [{"hooks": [{"type": "command", "command": command}]}]}
        root, _, events = self.run_bridge(hooks, "bridge.pre_tool_call('terminal',{'command':'pwd'},session_id='s')")
        completion = next(e for e in events if e["stage"] == "hook.completed")
        payload = json.loads(gzip.decompress((root / "capture" / completion["data_ref"]["path"]).read_bytes()))
        self.assertEqual(len(payload["result"]["stdout"]), 1100000)
        self.assertEqual(len(payload["result"]["stderr"]), 1100000)
        hooks["PreToolUse"][0]["hooks"][0] = {"type": "command", "timeout": 1,
            "command": "python3 -c \"import time;print('partial',flush=True);time.sleep(3)\""}
        root, _, events = self.run_bridge(hooks, "bridge.pre_tool_call('terminal',{'command':'pwd'},session_id='s')")
        failed = next(e for e in events if e["stage"] == "process.failed")
        payload = json.loads(gzip.decompress((root / "capture" / failed["data_ref"]["path"]).read_bytes()))
        self.assertIn("partial", str(payload))

    def test_http_observes_the_same_read_limit_without_draining_the_response(self):
        body = b"h" * 100000
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                self.rfile.read(int(self.headers["Content-Length"]))
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            def log_message(self, *args):
                pass
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        hooks = {"PreToolUse": [{"hooks": [{"type": "http", "url": f"http://127.0.0.1:{server.server_port}/"}]}]}
        action = "bridge.pre_tool_call('terminal',{'command':'pwd'},session_id='http')"
        _, baseline, _ = self.run_bridge(hooks, action, traced=False)
        root, observed, events = self.run_bridge(hooks, action)
        self.assertEqual(observed, baseline)
        read = next(e for e in events if e["stage"] == "http.response_read")
        payload = json.loads(gzip.decompress((root / "capture" / read["data_ref"]["path"]).read_bytes()))
        self.assertEqual(len(base64.b64decode(payload["body"]["bytes"])), 65536)
        self.assertEqual(read["completeness"], "unknown_at_limit")

    def test_a_real_storage_failure_does_not_change_the_hook_decision(self):
        command = "printf '{\"hookSpecificOutput\":{\"hookEventName\":\"PreToolUse\",\"permissionDecision\":\"deny\",\"permissionDecisionReason\":\"CANARY-BLOCK\"}}'"
        hooks = {"PreToolUse": [{"hooks": [{"type": "command", "command": command}]}]}
        setup = "from hook_capture.instrument import RECORDER\nRECORDER.root=__import__('pathlib').Path('/dev/null/capture')"
        _, result, _ = self.run_bridge(hooks, "bridge.pre_tool_call('terminal',{'command':'pwd'},session_id='disk')", setup=setup)
        self.assertIn("CANARY-BLOCK", result)

    def test_malformed_specific_output_does_not_change_native_behavior(self):
        hooks = {"PreToolUse": [{"hooks": [{"type": "command", "command": "printf '{\"hookSpecificOutput\":\"not-an-object\"}'"}]}]}
        action = "bridge.pre_tool_call('terminal',{'command':'pwd'},session_id='malformed')"
        _, baseline, _ = self.run_bridge(hooks, action, traced=False)
        _, observed, events = self.run_bridge(hooks, action)
        self.assertEqual(observed, baseline)
        self.assertTrue(any(e["stage"] == "response.parsed.returned" for e in events))

    def test_thread_pool_retains_only_the_capture_context(self):
        setup = ("from concurrent.futures import ThreadPoolExecutor\n"
                 "from hook_capture.instrument import CURRENT,observed\n"
                 "from contextvars import ContextVar\n"
                 "other=ContextVar('native_other',default='native-default')\nother.set('caller-only')\n"
                 "CURRENT.set({'session_id':'threaded','span_id':'parent-span'})\n"
                 "def value():return other.get()\n"
                 "worker=observed(value,'host.thread_probe')\n"
                 "pool=ThreadPoolExecutor(max_workers=1)\n")
        _, outcome, events = self.run_bridge({}, "pool.submit(worker).result()", setup=setup)
        self.assertIn('"native-default"', outcome)
        entered = next(e for e in events if e["stage"] == "host.thread_probe.entered")
        self.assertEqual(entered["session_id"], "threaded")
        self.assertEqual(entered["parent_span_id"], "parent-span")

    def test_detached_runner_survives_parent_and_captures_discarded_large_streams(self):
        import hashlib
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            venv.EnvBuilder(with_pip=False).create(root / "venv")
            python = root / "venv/bin/python"
            site = Path(subprocess.check_output([str(python), "-c", "import site;print(site.getsitepackages()[0])"], text=True).strip())
            configuration = root / "config.json"
            configuration.write_text(json.dumps({"enabled": True, "root": str(root / "capture"),
                "run_id": "async-run", "plugin_root": str(PLUGIN),
                "fingerprints": {str(PLUGIN / name): hashlib.sha256((PLUGIN / name).read_bytes()).hexdigest()
                                 for name in ("bridge.py", "remote_hooks.py", "__init__.py", "bin/hook_runner.py")}}))
            configuration.chmod(0o600)
            (site / "development_capture.pth").write_text(f"import sys; sys.path.insert(0, {str(ROOT / 'development')!r}); from hook_capture.bootstrap import start; start()\n")
            command = "python3 -c \"import time,sys;time.sleep(.2);sys.stdout.write('o'*1100000);sys.stderr.write('e'*1100000)\""
            settings = root / "settings.json"
            settings.write_text(json.dumps({"hooks": {"UserPromptSubmit": [{"hooks": [{"type": "command", "command": command, "async": True}]}]}}))
            code = ("from pathlib import Path\nfrom lifeos_hook_bridge.bridge import HookBridge\n"
                    f"bridge=HookBridge(Path({str(settings)!r}),Path({str(root)!r}))\n"
                    "bridge.pre_llm_call([{'role':'user','content':'ASYNC-CANARY'}],session_id='detached')\nbridge.close()\n")
            env = dict(os.environ, PYTHONPATH=str(ROOT), HERMES_HOOK_CAPTURE_CONFIG=str(configuration))
            env.pop("XDG_RUNTIME_DIR", None)  # Exercise the Popen fallback on this machine.
            parent = subprocess.run([str(python), "-c", code], env=env, capture_output=True, text=True, timeout=20)
            self.assertEqual(parent.returncode, 0, parent.stderr)
            events = []
            for _ in range(100):
                events = [json.loads(line) for path in (root / "capture").glob("runs/*/events/*/*.jsonl")
                          for line in path.read_text().splitlines() if line.endswith("}")]
                if any(e["stage"] == "hook.completed" for e in events):
                    break
                time.sleep(.05)
            handoff = next(e for e in events if e["stage"] == "async.handoff")
            done = next(e for e in events if e["stage"] == "hook.completed")
            self.assertEqual(handoff["invocation_id"], done["invocation_id"])
            self.assertNotEqual(handoff["process_id"], done["process_id"])
            payload = json.loads(gzip.decompress((root / "capture" / done["data_ref"]["path"]).read_bytes()))
            self.assertEqual(len(payload["stdout"]), 1100000)
            self.assertEqual(len(base64.b64decode(payload["stderr"]["bytes"])), 1100000)
            self.assertEqual(list(root.glob("**/async-results/**/*.json")), [])


if __name__ == "__main__":
    unittest.main()
