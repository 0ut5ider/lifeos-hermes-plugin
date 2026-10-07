# ABOUTME: Checks the native LifeOS VersionDrift hook with tagged and plugin baselines.
# ABOUTME: Runs the hook through Hermes in disposable homes without changing user data.

import json
import os
import shutil
import shlex
import subprocess
import tempfile
import time
import unittest
from datetime import datetime
from pathlib import Path

from lifeos_hook_bridge.bridge import HookBridge
from lifeos_hook_bridge.version_drift import create_baseline, save_baseline


HOOK_PATH = os.environ.get("LIFEOS_VERSION_DRIFT_PATH")
TAGGED_REPO_PATH = os.environ.get("LIFEOS_VERSION_DRIFT_TAGGED_REPO_PATH")


@unittest.skipUnless(HOOK_PATH and shutil.which("bun"), "LifeOS VersionDrift and Bun are required")
class NativeVersionDriftTests(unittest.TestCase):
    def test_new_source_skill_reaches_native_drift_warning(self):
        with tempfile.TemporaryDirectory(prefix="lifeos-version-drift-skill-") as directory:
            home = Path(directory)
            source = home / "source"
            root = home / ".claude"
            for base in (source, root):
                (base / "hooks").mkdir(parents=True)
                (base / "LIFEOS/VERSION").parent.mkdir(parents=True)
                (base / "LIFEOS/VERSION").write_text("7.40.4\n")
            hook = root / "hooks/VersionDrift.hook.ts"
            shutil.copy2(HOOK_PATH, hook)
            for base in (source, root):
                helper = base / 'LIFEOS/PULSE/lib/atomic-write.ts'
                helper.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(Path(HOOK_PATH).parent.parent/'LIFEOS/PULSE/lib/atomic-write.ts', helper)
            hook.chmod(0o755)
            shutil.copy2(HOOK_PATH, source / "hooks/VersionDrift.hook.ts")
            subprocess.run(["git", "init", "-q", str(source)], check=True)
            subprocess.run(["git", "-C", str(source), "add", "hooks", "LIFEOS"], check=True)
            subprocess.run(["git", "-C", str(source), "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                            "commit", "-qm", "fixture"], check=True)
            baseline = create_baseline(source, root)
            baseline["created_at"] -= 49 * 3600
            baseline_path = home / "baseline.json"
            save_baseline(baseline, baseline_path)
            for base in (source, root):
                skill = base / "skills/new-source-skill/SKILL.md"
                skill.parent.mkdir(parents=True)
                skill.write_text("new skill")
            subprocess.run(["git", "-C", str(source), "add", "skills/new-source-skill/SKILL.md"], check=True)
            settings = root / "settings.json"
            settings.write_text(json.dumps({"hooks": {"UserPromptSubmit": [{"hooks": [
                {"type": "command", "command": str(hook), "timeout": 10},
            ]}]}}))
            bridge = HookBridge(settings, root)
            bridge.environment.update(HOME=str(home), LIFEOS_VERSION_DRIFT_BASELINE=str(baseline_path))
            try:
                result = bridge.pre_llm_call("Check a new skill", session_id="new-skill-probe")
                self.assertIn("VERSION-DRIFT: 1 core file(s)", result["context"])
            finally:
                bridge.close()

    def test_plugin_baseline_drives_native_hook_without_git_in_home(self):
        with tempfile.TemporaryDirectory(prefix="lifeos-version-drift-baseline-") as directory:
            home = Path(directory)
            source = home / "source"
            root = home / ".claude"
            for base in (source, root):
                (base / "hooks").mkdir(parents=True)
                (base / "LIFEOS/TOOLS").mkdir(parents=True)
                (base / "LIFEOS/VERSION").write_text("7.40.4\n")
            hook = root / "hooks/VersionDrift.hook.ts"
            shutil.copy2(HOOK_PATH, hook)
            for base in (source, root):
                helper = base / 'LIFEOS/PULSE/lib/atomic-write.ts'
                helper.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(Path(HOOK_PATH).parent.parent/'LIFEOS/PULSE/lib/atomic-write.ts', helper)
            hook.chmod(0o755)
            shutil.copy2(HOOK_PATH, source / "hooks/VersionDrift.hook.ts")
            for index in range(10):
                for base in (source, root):
                    (base / f"LIFEOS/TOOLS/Tool{index}.ts").write_text(f"baseline {index}\n")
            subprocess.run(["git", "init", "-q", str(source)], check=True)
            subprocess.run(["git", "-C", str(source), "add", "hooks", "LIFEOS"], check=True)
            subprocess.run(["git", "-C", str(source), "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                            "commit", "-qm", "fixture"], check=True)
            baseline = create_baseline(source, root)
            baseline["created_at"] -= 49 * 3600
            baseline_path = home / "version-drift-baseline.json"
            save_baseline(baseline, baseline_path)
            self.assertFalse((root / ".git").exists())
            (root / "LIFEOS/TOOLS/Tool0.ts").write_text("changed\n")
            settings = root / "settings.json"
            settings.write_text(json.dumps({"hooks": {"UserPromptSubmit": [{"hooks": [
                {"type": "command", "command": str(hook), "timeout": 10},
            ]}]}}))
            bridge = HookBridge(settings, root)
            bridge.environment.update(HOME=str(home), LIFEOS_VERSION_DRIFT_BASELINE=str(baseline_path))
            try:
                first = bridge.pre_llm_call("Check version", session_id="baseline-probe")
                second = bridge.pre_llm_call("Check version again", session_id="baseline-probe")
                self.assertIn("VERSION-DRIFT: 1 core file(s)", first["context"])
                self.assertIsNone(second)
                state = root / "LIFEOS/MEMORY/STATE/version-drift-nag.json"
                self.assertEqual(json.loads(state.read_text())["count"], 1)
                prior = state.read_bytes()
                stamp = int(datetime.fromisoformat(json.loads(prior)["ts"].replace("Z", "+00:00")).timestamp() * 1000)
                preload = home / "boundary-clock.cjs"
                preload.write_text('// ABOUTME: Supplies a controlled clock to the native interval predicate.\n'
                                   '// ABOUTME: Leaves native hook execution and filesystem effects unchanged.\n'
                                   'Date.now = () => Number(process.env.LIFEOS_BOUNDARY_NOW_MS);\n')
                original_command = bridge.hooks['UserPromptSubmit'][0]['hooks'][0]['command']
                bridge.hooks['UserPromptSubmit'][0]['hooks'][0]['command'] = shlex.join([
                    'bun', '--preload', str(preload), str(hook)])
                bridge.environment['LIFEOS_VERSION_DRIFT_ROOT'] = str(root)
                bridge.environment['LIFEOS_VERSION_DRIFT_SYSTEM_GIT'] = shutil.which('git')
                for offset in (-1, 0, 1):
                    with self.subTest(interval_offset_ms=offset):
                        state.write_bytes(prior)
                        bridge.environment['LIFEOS_BOUNDARY_NOW_MS'] = str(stamp + 3600000 + offset)
                        boundary = bridge.pre_llm_call('Measure native nag interval', session_id='baseline-probe')
                        if offset < 0:
                            self.assertIsNone(boundary)
                            self.assertEqual(state.read_bytes(), prior)
                        else:
                            self.assertIn('VERSION-DRIFT: 1 core file(s)', boundary['context'])
                state.write_bytes(prior)
                marker = home / 'state-write-started'
                preload.write_text('''// ABOUTME: Widens the native file truncation interval for an interruption control.
// ABOUTME: Leaves the final write to the native filesystem implementation.
const fs = require('node:fs');
Date.now = () => Number(process.env.LIFEOS_BOUNDARY_NOW_MS);
const original = fs.writeFileSync;
fs.writeFileSync = function(path, ...args) {
  if (/version-drift-nag\\.json(?:\\.tmp\\..*)?$/.test(String(path))) {
    fs.closeSync(fs.openSync(path, 'w'));
    original(process.env.LIFEOS_WRITE_MARKER, 'started');
    Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 30000);
  }
  return original.call(this, path, ...args);
};
''')
                environment = {**bridge.environment, 'LIFEOS_WRITE_MARKER': str(marker),
                               'LIFEOS_BOUNDARY_NOW_MS': str(stamp + 3600001)}
                with tempfile.TemporaryFile(mode='w+t') as captured:
                    writer = subprocess.Popen(['bun', '--preload', str(preload), str(hook)],
                                              env=environment, stdout=captured, stderr=captured)
                    try:
                        deadline = time.monotonic() + 10
                        while not marker.exists() and writer.poll() is None and time.monotonic() < deadline:
                            time.sleep(.01)
                        captured.seek(0)
                        self.assertTrue(marker.exists(), captured.read())
                    finally:
                        if writer.poll() is None:
                            writer.kill()
                        writer.wait(timeout=5)
                    captured.seek(0)
                    self.assertEqual(captured.read(), '')
                self.assertEqual(state.read_bytes(), prior, 'Interrupted native publication destroyed the prior nag state')
                for temporary in state.parent.glob('version-drift-nag.json.tmp.*'):
                    temporary.unlink()
                bridge.hooks['UserPromptSubmit'][0]['hooks'][0]['command'] = original_command
                bridge.environment.pop('LIFEOS_BOUNDARY_NOW_MS')
                bridge.environment.pop('LIFEOS_VERSION_DRIFT_ROOT')
                bridge.environment.pop('LIFEOS_VERSION_DRIFT_SYSTEM_GIT')
                state.unlink()
                (root / "LIFEOS/VERSION").write_text("7.40.5\n")
                self.assertIsNone(bridge.pre_llm_call("Bump in flight", session_id="baseline-probe"))
                (root / "LIFEOS/VERSION").write_text("7.40.4\n")
                for index in range(10):
                    (root / f"LIFEOS/TOOLS/Tool{index}.ts").write_text(f"changed {index}\n")
                self.assertIn("VERSION-DRIFT: 10 core file(s)",
                              bridge.pre_llm_call("Check many changes", session_id="baseline-probe")["context"])
            finally:
                bridge.close()
            (root / "LIFEOS/MEMORY/STATE/version-drift-nag.json").unlink()
            settings.write_text(json.dumps({"hooks": {"UserPromptSubmit": [{"hooks": [
                {"type": "command", "command": str(hook), "timeout": 10, "async": True},
            ]}]}}))
            bridge = HookBridge(settings, root)
            bridge.environment.update(HOME=str(home), LIFEOS_VERSION_DRIFT_BASELINE=str(baseline_path))
            try:
                self.assertIsNone(bridge.pre_llm_call("Check asynchronously", session_id="async-baseline-probe"))
                result_dir = bridge._async_result_dir("async-baseline-probe")
                deadline = time.monotonic() + 10
                while not list(result_dir.glob("*.json")) and time.monotonic() < deadline:
                    time.sleep(0.05)
                self.assertTrue(list(result_dir.glob("*.json")), "native async hook did not deliver a result")
                delivered = bridge.pre_llm_call("Collect async result", session_id="async-baseline-probe")
                self.assertIn("VERSION-DRIFT: 10 core file(s)", delivered["context"])
            finally:
                bridge.close()

    @unittest.skipUnless(TAGGED_REPO_PATH, "a tagged read-only Git repository is required")
    def test_native_tagged_control_nags_once(self):
        repo = Path(TAGGED_REPO_PATH)
        tags = subprocess.check_output(
            ["git", "-C", str(repo), "tag", "-l", "v[0-9]*.[0-9]*.[0-9]*", "--sort=-v:refname"],
            text=True,
        ).splitlines()
        if not tags:
            self.skipTest("the read-only Git repository has no semantic version tag")
        git_dir = subprocess.check_output(
            ["git", "-C", str(repo), "rev-parse", "--absolute-git-dir"], text=True,
        ).strip()

        with tempfile.TemporaryDirectory(prefix="lifeos-version-drift-active-") as directory:
            home = Path(directory)
            root = home / ".claude"
            (root / "LIFEOS").mkdir(parents=True)
            (root / "LIFEOS/VERSION").write_text(tags[0][1:] + "\n")
            settings = root / "settings.json"
            settings.write_text(json.dumps({"hooks": {"UserPromptSubmit": [{"hooks": [
                {"type": "command", "command": "env LIFEOS_VERSION_DRIFT_ROOT= LIFEOS_VERSION_DRIFT_BASELINE= bun " + shlex.quote(HOOK_PATH)},
            ]}]}}))
            bridge = HookBridge(settings, root)
            bridge.environment.update(HOME=str(home), GIT_DIR=git_dir, GIT_WORK_TREE=str(root))
            try:
                first = bridge.pre_llm_call("Check the release", session_id="version-probe")
                second = bridge.pre_llm_call("Check the release again", session_id="version-probe")
            finally:
                bridge.close()

            self.assertIn("VERSION-DRIFT", first["context"])
            self.assertIn(tags[0], first["context"])
            self.assertIsNone(second)
            state = json.loads((root / "LIFEOS/MEMORY/STATE/version-drift-nag.json").read_text())
            self.assertEqual(state["tag"], tags[0])
            self.assertGreaterEqual(state["count"], 10)

    def test_untagged_installation_does_not_nag(self):
        with tempfile.TemporaryDirectory(prefix="lifeos-version-drift-") as directory:
            home = Path(directory)
            root = home / ".claude"
            root.mkdir()
            settings = root / "settings.json"
            settings.write_text(json.dumps({"hooks": {"UserPromptSubmit": [{"hooks": [
                {"type": "command", "command": f"bun {HOOK_PATH}"},
            ]}]}}))
            bridge = HookBridge(settings, root)
            bridge.environment["HOME"] = str(home)
            try:
                result = bridge.pre_llm_call("Check the release", session_id="version-probe")
            finally:
                bridge.close()

            self.assertIsNone(result)
            self.assertFalse((root / "LIFEOS/MEMORY/STATE/version-drift-nag.json").exists())
