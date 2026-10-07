# ABOUTME: Verifies private development evidence using real hook processes.
# ABOUTME: Compares traced behavior with the unchanged LifeOS bridge.

import gzip
import base64
import dataclasses
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
    def test_discord_slash_observer_preserves_dispatch_and_exception(self):
        import asyncio
        from types import SimpleNamespace
        from hook_capture import instrument
        from hook_capture.store import Recorder
        interaction = SimpleNamespace(id=111, application_id=222, channel_id=333,
            user=SimpleNamespace(id=444), type=SimpleNamespace(value=2),
            token="SYNTHETIC-PRIVATE-TOKEN", data={"name": "stop"})
        calls = []

        async def dispatch(self, interaction, command_text):
            calls.append(command_text)
            if command_text == "/fail":
                raise ValueError("synthetic dispatch failure")
            return True

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original = instrument.RECORDER
            instrument.RECORDER = Recorder(root, "slash-test")
            try:
                observed = instrument.discord_interaction_observed(dispatch, "dispatch")
                self.assertTrue(asyncio.run(observed(None, interaction, "/stop")))
                with self.assertRaisesRegex(ValueError, "synthetic dispatch failure"):
                    asyncio.run(observed(None, interaction, "/fail"))
            finally:
                instrument.RECORDER = original
            self.assertEqual(calls, ["/stop", "/fail"])
            events = [json.loads(line) for path in root.glob("runs/*/events/*/*.jsonl")
                      for line in path.read_text().splitlines()]
            self.assertEqual([event["stage"] for event in events], ["discord.dispatch.entered",
                "discord.dispatch.returned", "discord.dispatch.entered", "discord.dispatch.failed"])
            for artifact in root.glob("artifacts/**/*.json.gz"):
                self.assertNotIn(interaction.token, gzip.decompress(artifact.read_bytes()).decode())

    def test_discord_interaction_snapshot_excludes_tokens_and_options(self):
        from types import SimpleNamespace
        from hook_capture.instrument import discord_interaction_snapshot
        interaction = SimpleNamespace(id=111, application_id=222, channel_id=333,
            user=SimpleNamespace(id=444), type=SimpleNamespace(value=2),
            token="SYNTHETIC-INTERACTION-TOKEN", data={"name": "stop",
                "options": [{"name": "private", "value": "SYNTHETIC-PRIVATE-OPTION"}]})
        snapshot = discord_interaction_snapshot(interaction)
        self.assertEqual(snapshot, {"interaction_id": "111", "application_id": "222",
            "channel_id": "333", "user_id": "444", "interaction_type": 2, "command_name": "stop"})
        self.assertNotIn("SYNTHETIC", json.dumps(snapshot))

    def test_environment_values_and_unknown_credential_echoes_are_not_recorded(self):
        from hook_capture.store import Recorder
        environment = {'ANTHROPIC_KEY':'SYNTHETIC-KEY-311804', 'GH_PAT':'SYNTHETIC-PAT-311805',
                       'SSH_PASSPHRASE':'SYNTHETIC-PHRASE-311806',
                       'SLACK_WEBHOOK_URL':'https://hooks.slack.com/services/T000/B000/SYNTHETIC-WEBHOOK-311807',
                       'ORDINARY_CUSTOM_SETTING':'SYNTHETIC-UNKNOWN-311808', 'LANG':'C.UTF-8',
                       'LIFEOS_CHILD_EFFORT':'medium'}
        for name in ('env', 'environment'):
            with self.subTest(field=name), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                recorder = Recorder(root, 'test-run')
                ref = recorder.artifact({'options':{name:environment}, 'stdout':list(environment.values())[:5]})
                raw = gzip.decompress((root / ref['path']).read_bytes()).decode()
                for key in list(environment)[:5]:
                    self.assertNotIn(environment[key], raw)
                captured = json.loads(raw)['options'][name]
                self.assertEqual(set(captured), set(environment))
                self.assertEqual(captured['LANG'], 'C.UTF-8')
                self.assertEqual(captured['LIFEOS_CHILD_EFFORT'], 'medium')

    def test_installed_recorder_captures_detached_hook_with_another_startup_home(self):
        from hook_capture import setup as capture_setup
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            home = root / 'profile-home'
            home.mkdir()
            configuration = home / '.config/lifeos-development-capture/config.json'
            host = root / 'host'
            for name in capture_setup.HOST_FILES:
                target = host / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text('# Synthetic pinned host source\n')
            environment = root / 'python'
            venv.EnvBuilder(with_pip=False).create(environment)
            python = environment / 'bin/python'
            site = next((environment / 'lib').glob('python*/site-packages'))
            installer = ('import sys\nfrom pathlib import Path\nfrom hook_capture.setup import install\n'
                         'install(*map(Path,sys.argv[1:]))\n')
            installed = subprocess.run([sys.executable, '-c', installer, str(PLUGIN), str(host),
                str(root / 'capture'), str(configuration), str(site)],
                env={**os.environ, 'HOME': str(home), 'PYTHONPATH': str(ROOT / 'development')},
                capture_output=True, text=True, timeout=20)
            self.assertEqual(installed.returncode, 0, installed.stderr)
            spool = root / 'hook.json'
            spool.write_text(json.dumps({'command': 'printf synthetic-detached-output',
                'payload': {'hook_event_name': 'Stop'}, 'cwd': str(home),
                'environment': {**os.environ, 'HOME': str(home)},
                '_development_capture': {'invocation_id': 'synthetic-detached-id'}}))
            spool.chmod(0o600)
            env = {**os.environ, 'HOME': str(root / 'systemd-home')}
            env.pop('HERMES_HOOK_CAPTURE_CONFIG', None)
            result = subprocess.run([str(python), str(PLUGIN / 'bin/hook_runner.py'), str(spool)],
                env=env, capture_output=True, text=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stderr)
            events = [json.loads(line) for path in (root / 'capture').glob('runs/*/events/*/*.jsonl')
                      for line in path.read_text().splitlines()]
            completed = [event for event in events if event['stage'] == 'hook.completed']
            self.assertEqual(len(completed), 1)
            self.assertEqual(completed[0]['invocation_id'], 'synthetic-detached-id')

    def test_shared_container_declarations_are_learned_in_sensitive_context(self):
        from hook_capture.store import Recorder
        secret = "SYNTHETIC-ALIASED-CREDENTIAL-847261"
        shared = [secret]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            recorder = Recorder(root, "test-run")
            ref = recorder.artifact({"ordinary": shared, "api_key": shared})
            self.assertNotIn(secret, gzip.decompress((root / ref["path"]).read_bytes()).decode())

    def test_basic_authorization_learns_encoded_and_decoded_credentials(self):
        from hook_capture.store import Recorder
        secret = "SYNTHETIC-BASIC-PASSWORD-483729"
        encoded = base64.b64encode(("synthetic-user:" + secret).encode()).decode()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            recorder = Recorder(root, "test-run")
            ref = recorder.artifact({"headers": {"Authorization": "Basic " + encoded},
                                     "echo": secret, "encoded_echo": encoded})
            raw = gzip.decompress((root / ref["path"]).read_bytes()).decode()
            self.assertNotIn(secret, raw)
            self.assertNotIn(encoded, raw)

    def test_cookie_declarations_redact_cookie_value_echoes(self):
        from hook_capture.store import Recorder
        secret = "SYNTHETIC-CLOSURE-COOKIE-192837"
        for header, value in (("Set-Cookie", "session=" + secret + "; HttpOnly; Path=/"),
                              ("Cookie", "ordinary=another-cookie-value; session=" + secret)):
            with self.subTest(header=header), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                recorder = Recorder(root, "test-run")
                ref = recorder.artifact({"headers": {header: value}, "body": json.dumps({"echo": secret})})
                self.assertNotIn(secret, gzip.decompress((root / ref["path"]).read_bytes()).decode())

    def test_each_artifact_reference_validates_its_expected_digest(self):
        from hook_capture.store import Recorder
        from hook_capture.analysis import rebuild, summary
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            recorder = Recorder(root, "test-run")
            event = recorder.emit("observed.valid", data={"registrations": [{"registration_id": "bad-digest"}]})
            with recorder.event_path.open("a") as stream:
                stream.write(json.dumps({**event, "event_id": "second-event", "stage": "inventory.observed",
                    "data_ref": {**event["data_ref"], "sha256": "0" * 64}}) + "\n")
            report = summary(rebuild(root))
            self.assertEqual(report["events"], 2)
            self.assertEqual(report["known_registrations"], 0)
            self.assertEqual(report["integrity_issues"], {"artifact_error": 1})

    def test_bearer_declarations_redact_bare_token_echoes(self):
        from hook_capture.store import Recorder
        secret = "SYNTHETIC-BEARER-CREDENTIAL-482739"
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            recorder = Recorder(root, "test-run")
            ref = recorder.artifact({"headers": {"Authorization": "Bearer " + secret}, "stdout": secret})
            self.assertNotIn(secret, gzip.decompress((root / ref["path"]).read_bytes()).decode())

    def test_transport_learns_all_decoded_frames_before_redaction(self):
        from hook_capture.instrument import transport_input, transport_output
        secret = "SYNTHETIC-REMOTE-DECLARATION-283749"
        encode = lambda value: base64.b64encode(value.encode()).decode()
        marker = "__LIFEOS_HOOK_" + "a" * 32 + "__"
        for stdout, stderr in ((secret, json.dumps({"api_key": secret})),
                               (json.dumps({"api_key": secret, "echo": secret}), secret)):
            wire = "\n".join((marker, "0", encode(stdout), encode(stderr), marker + "_END"))
            clean = transport_output(wire, [])
            for frame in clean.splitlines()[2:4]:
                self.assertNotIn(secret, base64.b64decode(frame).decode())
        wire = "\n".join((encode("echo " + secret), "1", encode("API_KEY=" + secret),
                           json.dumps({"echo": secret})))
        clean = transport_input(wire, [])
        self.assertNotIn(secret, base64.b64decode(clean.splitlines()[0]).decode())
        self.assertNotIn(secret, clean.splitlines()[-1])

    def test_index_rejects_invalid_inventory_and_keeps_valid_events(self):
        from hook_capture.store import Recorder
        from hook_capture.analysis import rebuild, summary
        for malformed in ({"registrations": [{"registration_id": "bad", "matcher": []}]},
                          {"registrations": None}, {"registrations": [None]}):
            with self.subTest(inventory=malformed), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                recorder = Recorder(root, "test-run")
                recorder.emit("inventory.observed", data=malformed)
                recorder.emit("observed.valid")
                report = summary(rebuild(root))
                self.assertEqual(report["events"], 2)
                self.assertEqual(report["known_registrations"], 0)
                self.assertEqual(report["integrity_issues"], {"invalid_inventory": 1})

    def test_index_rejects_out_of_range_integers_and_keeps_valid_events(self):
        from hook_capture.store import Recorder
        from hook_capture.analysis import rebuild, summary
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            recorder = Recorder(root, "test-run")
            event = recorder.emit("observed.valid")
            with recorder.event_path.open("a") as stream:
                for field in ("sequence", "duration_ns", "exit_code"):
                    stream.write(json.dumps({**event, field: 2**100}) + "\n")
            report = summary(rebuild(root))
            self.assertEqual(report["events"], 1)
            self.assertEqual(report["integrity_issues"], {"invalid_event": 3})

    def test_http_credentials_are_redacted_and_echoed_values_are_learned(self):
        from hook_capture.store import Recorder
        secret = "SYNTHETIC-HTTP-CREDENTIAL-928374"
        cases = [
            {"headers": {"X-API-Key": secret}},
            {"url": "https://operator:" + secret + "@example.invalid/route?ordinary=yes"},
            {"url": "https://example.invalid/route?ordinary=yes&access_token=" + secret},
            {"url": "https://example.invalid/route#access_token=" + secret},
        ]
        for declared in cases:
            with self.subTest(declared=declared), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                recorder = Recorder(root, "test-run")
                ref = recorder.artifact({**declared, "stdout": secret, "prompt": "keep this ordinary prompt"})
                raw = gzip.decompress((root / ref["path"]).read_bytes()).decode()
                self.assertNotIn(secret, raw)
                self.assertEqual(json.loads(raw)["prompt"], "keep this ordinary prompt")
                if "url" in declared and "ordinary=yes" in declared["url"]:
                    self.assertIn("ordinary=yes", json.loads(raw)["url"])

    def test_json_text_and_dataclasses_declare_credentials_before_echo_redaction(self):
        from hook_capture.store import Recorder
        secret = "SYNTHETIC-DECLARED-CREDENTIAL-382719"
        @dataclasses.dataclass
        class Result:
            api_key: str
            stdout: str
        for declared in (json.dumps({"api_key": secret, "stdout": secret}), Result(secret, secret),
                         subprocess.CompletedProcess(["true"], 0, json.dumps({"api_key": secret, "echo": secret}), secret)):
            with self.subTest(kind=type(declared).__name__), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                recorder = Recorder(root, "test-run")
                ref = recorder.artifact({"input": declared, "stdout": secret})
                self.assertNotIn(secret, gzip.decompress((root / ref["path"]).read_bytes()).decode())

    def test_summary_reports_known_capture_loss_and_instrumentation_gaps(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        script = """
import sys, json
from pathlib import Path
from hook_capture.store import Recorder
from hook_capture.analysis import rebuild, summary
root = Path(sys.argv[1])
first = Recorder(root, 'test-run')
first.emit('lost.first', data={'value': float('nan')})
first.emit('observed.first')
first.emit('observed.second')
second = Recorder(root, 'test-run')
second.emit('lost.second', data={'value': float('nan')})
second.emit('lost.third', data={'value': float('nan')})
second.emit('instrumentation.failed', status='capture_gap')
print(json.dumps(summary(rebuild(root))))
"""
        env = dict(os.environ, PYTHONPATH=str(ROOT / "development"))
        result = subprocess.run([sys.executable, "-c", script, str(root)], env=env,
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr.count("Development capture lost an event (ValueError)"), 3)
        report = json.loads(result.stdout)
        self.assertEqual(report["known_lost_events"], 3)
        self.assertEqual(report["capture_failure_processes"], 2)
        self.assertEqual(report["capture_gaps"], 1)

    def test_index_reports_malformed_records_and_corrupt_compressed_artifacts(self):
        from hook_capture.store import Recorder
        from hook_capture.analysis import rebuild, summary
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            recorder = Recorder(root, "test-run")
            event = recorder.emit("observed.artifact", data={"content": "a" * 1000})
            artifact = root / event["data_ref"]["path"]
            damaged = bytearray(artifact.read_bytes())
            damaged[10:14] = b"\xff\xff\xff\xff"
            artifact.write_bytes(damaged)
            with recorder.event_path.open("a") as stream:
                for malformed in ([], None, {"schema_version": 1, "data_ref": ["bad"]},
                                  {"schema_version": 1, "status": ["bad"]}, {"schema_version": 1},
                                  {**event, "data_ref": []}):
                    stream.write(json.dumps(malformed) + "\n")
            report = summary(rebuild(root))
            self.assertEqual(report["events"], 1)
            self.assertEqual(report["integrity_issues"], {"invalid_event": 6, "artifact_error": 1})

    def test_failed_hook_is_reported_as_failure_not_successful_execution(self):
        from hook_capture.store import Recorder
        from hook_capture.analysis import rebuild, summary
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            recorder = Recorder(root, "test-run")
            recorder.emit("hook.failed", registration_id="failed", status="timeout", duration_ns=100)
            report = summary(rebuild(root))
            hook = report["hooks"][0]
            self.assertEqual(hook["terminal_outcomes"], 1)
            self.assertEqual(hook["successful_executions"], 0)
            self.assertEqual(hook["failures"], 1)

    def test_host_identity_retains_native_agent_turn(self):
        from hook_capture.instrument import identity
        class Agent:
            session_id = "native-session"
            _current_turn_id = "native-turn"
        self.assertEqual(identity({"agent": Agent()}), {"session_id": "native-session", "turn_id": "native-turn"})

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
    def run_bridge(self, hooks, action, *, traced=True, setup="", config_overrides=None):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        settings = root / "settings.json"
        settings.write_text(json.dumps({"hooks": hooks}))
        config = {"enabled": True, "root": str(root / "capture"), "run_id": "test-run",
                  "plugin_root": str(PLUGIN), "host_root": "",
                  "fingerprints": {}}
        import hashlib
        config["capture_sources"] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                     for p in (ROOT / "development/hook_capture").glob("*.py")}
        for name in ("bridge.py", "bin/hook_runner.py", "remote_hooks.py", "__init__.py"):
            p = PLUGIN / name
            config["fingerprints"][str(p)] = hashlib.sha256(p.read_bytes()).hexdigest()
        config.update(config_overrides or {})
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

    def test_recorder_source_drift_is_reported_without_changing_native_result(self):
        hooks = {"PreToolUse": [{"hooks": [{"type": "command", "command": "true"}]}]}
        action = "bridge.pre_tool_call('terminal',{'command':'pwd'},session_id='source-drift')"
        _, baseline, _ = self.run_bridge(hooks, action, traced=False)
        _, observed, events = self.run_bridge(hooks, action, config_overrides={"capture_sources": {"instrument.py": "0" * 64}})
        self.assertEqual(baseline, observed)
        self.assertTrue(any(e.get("status") == "capture_gap" for e in events))
        self.assertFalse(any(e["stage"] == "hook.completed" for e in events))

    def test_identical_hooks_at_distinct_settings_origins_have_distinct_registration_ids(self):
        hooks = {"PreToolUse": [{"hooks": [{"type": "command", "command": "true"}]}]}
        setup = """
def run_two_origins(bridge):
    second_settings = bridge.settings_path.with_name('second-settings.json')
    second_settings.write_text(bridge.settings_path.read_text())
    second = type(bridge)(second_settings, bridge.root)
    try:
        return [b.pre_tool_call('terminal', {'command':'pwd'}, session_id='origins') for b in (bridge,second)]
    finally:
        second.close()
"""
        root, _, events = self.run_bridge(hooks, "run_two_origins(bridge)", setup=setup)
        completed = [e for e in events if e["stage"] == "hook.completed"]
        self.assertEqual(len(completed), 2)
        self.assertEqual(len({e["registration_id"] for e in completed}), 2)
        from hook_capture.analysis import rebuild, summary
        self.assertEqual(summary(rebuild(root / "capture"))["known_registrations"], 2)

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

    def test_real_hook_credential_echo_is_filtered_before_every_result_artifact(self):
        secret = "SYNTHETIC-HOOK-CREDENTIAL-172839"
        setup = """
def run_credential_hook(bridge):
    import sys, json
    path = bridge.root / 'credential-hook.py'
    body = {'api_key': 'SYNTHETIC-HOOK-CREDENTIAL-172839', 'echo': 'SYNTHETIC-HOOK-CREDENTIAL-172839'}
    path.write_text('import json\\nprint(json.dumps(' + repr(body) + '))\\n')
    bridge.hooks['PreToolUse'][0]['hooks'][0]['command'] = sys.executable + ' ' + str(path)
    return bridge.pre_tool_call('terminal', {'command':'pwd'}, session_id='credential-echo')
"""
        hooks = {"PreToolUse": [{"hooks": [{"type": "command", "command": "true"}]}]}
        _, baseline, _ = self.run_bridge(hooks, "run_credential_hook(bridge)", setup=setup, traced=False)
        root, observed, events = self.run_bridge(hooks, "run_credential_hook(bridge)", setup=setup)
        self.assertEqual(observed, baseline)
        stages = {"process.completed", "run_command.returned", "hook.completed", "response.parsed.entered"}
        inspected = set()
        for event in events:
            if event["stage"] in stages:
                raw = gzip.decompress((root / "capture" / event["data_ref"]["path"]).read_bytes()).decode()
                self.assertNotIn(secret, raw)
                inspected.add(event["stage"])
        self.assertEqual(inspected, stages)

    def test_real_hook_unknown_environment_credential_echo_is_filtered(self):
        secret = 'SYNTHETIC-UNKNOWN-ENV-CREDENTIAL-313819'
        setup = """
def run_environment_hook(bridge):
    import os, sys
    os.environ['CUSTOM_PROVIDER_VALUE'] = 'SYNTHETIC-UNKNOWN-ENV-CREDENTIAL-313819'
    path = bridge.root / 'environment-hook.py'
    path.write_text('import os, json\\nprint(json.dumps({"echo":os.environ["CUSTOM_PROVIDER_VALUE"]}))\\n')
    bridge.hooks['PreToolUse'][0]['hooks'][0]['command'] = sys.executable + ' ' + str(path)
    return bridge.pre_tool_call('terminal', {'command':'pwd'}, session_id='environment-echo')
"""
        hooks = {'PreToolUse':[{'hooks':[{'type':'command','command':'true'}]}]}
        _, baseline, _ = self.run_bridge(hooks, 'run_environment_hook(bridge)', setup=setup, traced=False)
        root, observed, events = self.run_bridge(hooks, 'run_environment_hook(bridge)', setup=setup)
        self.assertEqual(observed, baseline)
        stages = {'process.started', 'process.completed', 'run_command.returned', 'hook.completed'}
        inspected = set()
        for event in events:
            if event['stage'] in stages:
                raw = gzip.decompress((root / 'capture' / event['data_ref']['path']).read_bytes()).decode()
                self.assertNotIn(secret, raw)
                inspected.add(event['stage'])
        self.assertEqual(inspected, stages)

    def test_real_http_url_headers_and_response_credentials_are_filtered(self):
        query_secret = "SYNTHETIC-QUERY-CREDENTIAL-928374"
        response_secret = "SYNTHETIC-RESPONSE-CREDENTIAL-918273"
        cookie_secret = "SYNTHETIC-COOKIE-CREDENTIAL-918274"
        second_cookie = "SYNTHETIC-SECOND-COOKIE-918275"
        body = json.dumps({"api_key": response_secret, "echo": response_secret, "cookie_echo": cookie_secret,
                           "second_echo": second_cookie}).encode()
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                self.rfile.read(int(self.headers["Content-Length"]))
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("X-API-Key", response_secret)
                self.send_header("Set-Cookie", "session=" + cookie_secret + "; HttpOnly; Path=/")
                self.send_header("Set-Cookie", "access=" + second_cookie + "; HttpOnly; Path=/")
                self.end_headers()
                self.wfile.write(body)
            def log_message(self, *args):
                pass
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        hooks = {"PreToolUse": [{"hooks": [{"type": "http", "url": f"http://127.0.0.1:{server.server_port}/?access_token={query_secret}"}]}]}
        action = "bridge.pre_tool_call('terminal',{'command':'pwd'},session_id='http-credentials')"
        _, baseline, _ = self.run_bridge(hooks, action, traced=False)
        root, observed, events = self.run_bridge(hooks, action)
        self.assertEqual(observed, baseline)
        for event in events:
            if event["stage"] in {"http.request", "http.response_read", "hook.completed", "run_http.returned", "inventory.observed"}:
                raw = gzip.decompress((root / "capture" / event["data_ref"]["path"]).read_bytes()).decode()
                self.assertNotIn(query_secret, raw)
                self.assertNotIn(response_secret, raw)
                self.assertNotIn(cookie_secret, raw)
                self.assertNotIn(second_cookie, raw)
                if event["stage"] == "http.response_read":
                    decoded = base64.b64decode(json.loads(raw)["body"]["bytes"]).decode()
                    self.assertNotIn(response_secret, decoded)
                    self.assertNotIn(cookie_secret, decoded)
                    self.assertNotIn(second_cookie, decoded)

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
                "capture_sources": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                    for p in (ROOT / "development/hook_capture").glob("*.py")},
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
