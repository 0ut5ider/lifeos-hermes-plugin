# ABOUTME: Verifies the LifeOS dashboard reads and saves only declared plugin settings.
# ABOUTME: Uses real FastAPI routes with isolated settings delegation and installation fixtures.

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch


API_PATH = Path(__file__).resolve().parents[1] / "lifeos_hook_bridge/dashboard/plugin_api.py"


class DashboardApiTests(unittest.TestCase):
    def test_update_worker_starts_installed_runtime_with_bound_home_and_tools(self):
        api = self.load_api(lambda *_: [], lambda *_: [])
        from hermes_cli import _launchers
        host = Path(_launchers.__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            api.INSTALLED_ROOT = home / '.claude'
            api.HERMES_HOME = home / '.hermes'
            api.HERMES_HOME.mkdir()
            api.HOST_SOURCE = host
            api.PLUGIN_DIR = home / 'plugin'
            api.PLUGIN_DIR.mkdir()
            tools = home / '.local/bin'
            tools.mkdir(parents=True)
            bun = shutil.which('bun') or '/home/outsider/.bun/bin/bun'
            (tools / 'bun').symlink_to(bun)
            (api.PLUGIN_DIR / 'update_worker.py').write_text(
                'import json,os,shutil,sys\nimport hermes_yaml\n'
                'print(json.dumps(dict(home=os.environ["HOME"], profile=os.environ["HERMES_HOME"],'
                'bun=shutil.which("bun"),pulse=os.environ.get("PULSE_URL"),args=sys.argv[1:])))\n')
            job = home / 'job'
            job.mkdir()
            (job / 'status.json').write_text('{"state":"queued"}')
            commands = []
            with patch.dict(os.environ, {'PATH':str(tools)+':/usr/bin:/bin',
                                         'PULSE_URL':'http://127.0.0.1:8923'}):
                with patch.object(api.subprocess, 'run', side_effect=lambda command, **_: commands.append(command) or
                                  types.SimpleNamespace(returncode=0, stdout='active')):
                    api._launch_lifeos_update(job)
            launch = commands[-1]
            self.assertIn('--setenv=HOME='+str(home), launch)
            self.assertIn('--setenv=PATH='+str(tools)+':/usr/bin:/bin', launch)
            self.assertIn('--setenv=PULSE_URL=http://127.0.0.1:8923', launch)
            environment = dict(os.environ, HOME='/wrong-home', PATH='/usr/bin:/bin')
            for value in launch:
                if value.startswith('--setenv='):
                    key, data = value[len('--setenv='):].split('=', 1)
                    environment[key] = data
            start = launch.index(sys.executable)
            child = subprocess.run(launch[start:], env=environment, capture_output=True, text=True, timeout=30)
            self.assertEqual(child.returncode, 0, child.stderr)
            self.assertEqual(child.stderr, '')
            self.assertEqual(json.loads(child.stdout), {'home':str(home),'profile':str(api.HERMES_HOME),
                'bun':str(tools/'bun'),'pulse':'http://127.0.0.1:8923','args':[str(job)]})

    def test_installation_status_distinguishes_missing_partial_and_installed(self):
        api = self.load_api(lambda *_: [], lambda *_: [])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / ".claude"
            api.INSTALLED_ROOT = root
            host = types.ModuleType("hermes_cli.plugins")
            host.VALID_HOOKS = {"pre_tool_call", "post_tool_call", "pre_llm_call",
                                "on_session_finalize", "api_request_error"}
            with patch.dict(sys.modules, {"hermes_cli": types.ModuleType("hermes_cli"),
                                          "hermes_cli.plugins": host}):
                self.assertEqual(api.get_installation()["lifeos"], "missing")
                self.assertEqual(api.get_installation()["hermes"], "stock")
                (root / "LIFEOS").mkdir(parents=True)
                self.assertEqual(api.get_installation()["lifeos"], "partial")
                (root / "LIFEOS/VERSION").write_text("7.40.4\n")
                (root / "settings.json").write_text("{}")
                installed = api.get_installation()
                self.assertEqual(installed["lifeos"], "installed")
                self.assertEqual(installed["version"], "7.40.4")
                host.VALID_HOOKS.update({"pre_command_approval", "augment_tool_result",
                                         "pre_turn_stop", "on_turn_result"})
                self.assertEqual(api.get_installation()["hermes"], "partial")
                self.assertEqual(api.get_installation()["missing_hooks"], ["pre_prompt_admission"])
                host.VALID_HOOKS.add("pre_prompt_admission")
                self.assertEqual(api.get_installation()["hermes"], "patched_hooks_present")

    def test_installation_reports_a_dashboard_restart_after_a_host_change(self):
        api = self.load_api(lambda *_: [], lambda *_: [])
        stock = {"pre_tool_call", "post_tool_call", "pre_llm_call", "on_session_finalize", "api_request_error"}
        cases = (("applied", stock, True), ("rolled_back", stock | api.PATCHED_HOOKS, True),
                 ("applied", stock | api.PATCHED_HOOKS, False), ("rolled_back", stock, False))
        for state, hooks, expected in cases:
            with self.subTest(state=state, patched=hooks >= api.PATCHED_HOOKS), \
                    tempfile.TemporaryDirectory() as directory:
                api.INSTALLED_ROOT = Path(directory) / ".claude"
                api.HOST_PATCH_ROOT = Path(directory) / "host-patches"
                (api.HOST_PATCH_ROOT / "patch-1").mkdir(parents=True)
                (api.HOST_PATCH_ROOT / "patch-1/manifest.json").write_text(json.dumps({"state": state}))
                host = types.ModuleType("hermes_cli.plugins")
                host.VALID_HOOKS = set(hooks)
                with patch.dict(sys.modules, {"hermes_cli": types.ModuleType("hermes_cli"),
                                              "hermes_cli.plugins": host}):
                    self.assertIs(api.get_installation()["dashboard_restart_required"], expected)

    def test_prepares_candidate_only_when_lifeos_is_missing(self):
        api = self.load_api(lambda *_: [], lambda *_: [])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            api.INSTALLED_ROOT = root / ".claude"
            api.INSTALL_CANDIDATE = root / "candidate"
            prepared = []

            def prepare(target):
                prepared.append(target)
                target.mkdir()
                return {"upstream_commit": "a" * 40, "patches": []}

            api.prepare_latest_lifeos = prepare
            self.assertEqual(api.prepare_installation()["upstream_commit"], "a" * 40)
            self.assertEqual(prepared, [api.INSTALL_CANDIDATE])
            with self.assertRaises(api.HTTPException) as duplicate:
                api.prepare_installation()
            self.assertEqual(duplicate.exception.status_code, 409)
            api.INSTALL_CANDIDATE.rename(root / "archived-candidate")
            (api.INSTALLED_ROOT / "LIFEOS").mkdir(parents=True)
            with self.assertRaises(api.HTTPException) as partial:
                api.prepare_installation()
            self.assertEqual(partial.exception.status_code, 409)

    def test_prepares_next_candidate_without_moving_baseline_source(self):
        api = self.load_api(lambda *_: [], lambda *_: [])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            api.INSTALLED_ROOT = root / ".claude"
            (api.INSTALLED_ROOT / "LIFEOS").mkdir(parents=True)
            (api.INSTALLED_ROOT / "LIFEOS/VERSION").write_text("7.40.4\n")
            api.BASELINE_PATH = root / "baseline.json"
            api.BASELINE_PATH.write_text("{}")
            api.INSTALL_CANDIDATE = root / "lifeos-candidate"
            api.INSTALL_CANDIDATE.mkdir()
            api.LIFEOS_UPDATE_ROOT = root / "updates"
            job = api.LIFEOS_UPDATE_ROOT / "update-one"
            job.mkdir(parents=True)
            (job / "request.json").write_text("{}")
            (job / "status.json").write_text('{"state":"applied"}')
            prepared = []
            def prepare(path):
                path.mkdir()
                prepared.append(path)
                return {"upstream_commit": "b" * 40, "patches": []}
            api.prepare_latest_lifeos = prepare
            result = api.prepare_installation()
            self.assertEqual(result["upstream_commit"], "b" * 40)
            self.assertEqual(len(prepared), 1)
            self.assertNotEqual(prepared[0], api.INSTALL_CANDIDATE)
            self.assertTrue(api.INSTALL_CANDIDATE.is_dir())
            self.assertEqual(api._candidate_path(), prepared[0])

    def test_installs_validated_candidate_into_empty_home(self):
        api = self.load_api(lambda *_: [], lambda *_: [])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            api.INSTALLED_ROOT = root / ".claude"
            api.INSTALL_CANDIDATE = root / "candidate"
            api.INSTALL_CANDIDATE.mkdir()
            api.validate_prepared_lifeos = lambda candidate: {
                "upstream_commit": "a" * 40, "patches": [{"name": "one.patch"}],
            }
            host = types.ModuleType("hermes_cli.plugins")
            host.VALID_HOOKS = set()
            with patch.dict(sys.modules, {"hermes_cli": types.ModuleType("hermes_cli"),
                                          "hermes_cli.plugins": host}):
                status = api.get_installation()
                self.assertTrue(status["candidate_ready"])
                self.assertEqual(status["candidate_commit"], "a" * 40)
                self.assertEqual(status["candidate_patch_count"], 1)
            calls = []
            def install(candidate, installed, failed):
                calls.append((candidate, installed, failed))
                (installed / "LIFEOS").mkdir(parents=True)
                (installed / "LIFEOS/VERSION").write_text("7.40.4\n")
                (installed / "settings.json").write_text("{}")
                return {"installed_version": "7.40.4", "restart_required": True}
            api.install_prepared_lifeos = install
            result = api.apply_installation()
            self.assertEqual(result["installed_version"], "7.40.4")
            self.assertEqual(calls[0][:2], (api.INSTALL_CANDIDATE, api.INSTALLED_ROOT))
            self.assertEqual(calls[0][2].parent, api.INSTALL_CANDIDATE.parent)
            with self.assertRaises(api.HTTPException) as duplicate:
                api.apply_installation()
            self.assertEqual(duplicate.exception.status_code, 409)

    def test_rejects_changed_candidate_and_existing_claude_home(self):
        api = self.load_api(lambda *_: [], lambda *_: [])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            api.INSTALLED_ROOT = root / ".claude"
            api.INSTALL_CANDIDATE = root / "candidate"
            api.INSTALL_CANDIDATE.mkdir()
            api.validate_prepared_lifeos = lambda candidate: (_ for _ in ()).throw(
                api.IncompatibleLifeOS("candidate changed"))
            host = types.ModuleType("hermes_cli.plugins")
            host.VALID_HOOKS = set()
            with patch.dict(sys.modules, {"hermes_cli": types.ModuleType("hermes_cli"),
                                          "hermes_cli.plugins": host}):
                status = api.get_installation()
                self.assertFalse(status["candidate_ready"])
                self.assertIn("candidate changed", status["candidate_error"])
            with self.assertRaises(api.HTTPException) as changed:
                api.apply_installation()
            self.assertEqual(changed.exception.status_code, 409)
            self.assertIn("candidate changed", changed.exception.detail)
            api.INSTALLED_ROOT.mkdir()
            with patch.dict(sys.modules, {"hermes_cli": types.ModuleType("hermes_cli"),
                                          "hermes_cli.plugins": host}):
                self.assertEqual(api.get_installation()["lifeos"], "partial")

    def test_prepares_host_patch_only_for_supported_stock_source(self):
        api = self.load_api(lambda *_: [], lambda *_: [])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            api.INSTALLED_ROOT = root / ".claude"
            (api.INSTALLED_ROOT / "LIFEOS").mkdir(parents=True)
            (api.INSTALLED_ROOT / "LIFEOS/VERSION").write_text("7.40.4\n")
            (api.INSTALLED_ROOT / "settings.json").write_text("{}")
            api.HERMES_CANDIDATE = root / "hermes-candidate"
            api.HOST_SOURCE = root / "stock-hermes"
            api.HOST_SOURCE.mkdir()
            prepared = []
            def prepare(source, target):
                prepared.append((source, target))
                target.mkdir()
                return {"base_commit": "a" * 40, "patches": [1]}
            api.prepare_supported_hermes = prepare
            self.assertEqual(api.prepare_hermes_installation()["base_commit"], "a" * 40)
            self.assertEqual(prepared, [(api.HOST_SOURCE, api.HERMES_CANDIDATE)])
            with self.assertRaises(api.HTTPException) as duplicate:
                api.prepare_hermes_installation()
            self.assertEqual(duplicate.exception.status_code, 409)
            api.HERMES_CANDIDATE.rename(root / "archived")
            api.prepare_supported_hermes = lambda *_: (_ for _ in ()).throw(
                api.IncompatibleLifeOS("Hermes source is not the tested commit"))
            with self.assertRaises(api.HTTPException) as unsupported:
                api.prepare_hermes_installation()
            self.assertEqual(unsupported.exception.status_code, 409)

    def test_finalizes_installed_lifeos_from_prepared_candidate(self):
        api = self.load_api(lambda *_: [], lambda *_: [])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            api.INSTALLED_ROOT = root / ".claude"
            (api.INSTALLED_ROOT / "LIFEOS").mkdir(parents=True)
            (api.INSTALLED_ROOT / "LIFEOS/VERSION").write_text("7.40.4\n")
            (api.INSTALLED_ROOT / "settings.json").write_text("{}")
            api.INSTALL_CANDIDATE = root / "candidate"
            api.INSTALL_CANDIDATE.mkdir()
            api.HERMES_HOME = root / ".hermes"
            api.BASELINE_PATH = root / "baseline.json"
            api.HERMES_HOME.mkdir()
            calls = []

            def finalize(*args):
                calls.append(args)
                api.BASELINE_PATH.write_text("{}")
                return {"mounted": True, "baseline_created": True, "restart_required": True}

            api.finalize_prepared_lifeos = finalize
            self.assertTrue(api.finalize_installation()["mounted"])
            self.assertEqual(calls[0][:4], (api.INSTALL_CANDIDATE, api.INSTALLED_ROOT,
                                            api.HERMES_HOME, api.BASELINE_PATH))
            with self.assertRaises(api.HTTPException) as duplicate:
                api.finalize_installation()
            self.assertEqual(duplicate.exception.status_code, 409)

    def test_stages_lifeos_update_from_validated_candidate_and_baseline(self):
        api = self.load_api(lambda *_: [], lambda *_: [])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            api.INSTALLED_ROOT = root / ".claude"
            api.INSTALLED_ROOT.mkdir()
            (api.INSTALLED_ROOT / "LIFEOS").mkdir()
            (api.INSTALLED_ROOT / "LIFEOS/VERSION").write_text("7.40.4\n")
            (api.INSTALLED_ROOT / "settings.json").write_text("{}")
            api.HERMES_HOME = root / ".hermes"
            api.HERMES_HOME.mkdir()
            api.HOST_SOURCE = root / "stock-hermes"
            api.BASELINE_PATH = root / "baseline.json"
            (root / "prior/LifeOS/install").mkdir(parents=True)
            api.BASELINE_PATH.write_text(json.dumps({
                "source_root": str(root / "prior/LifeOS/install"),
                "installed_root": str(api.INSTALLED_ROOT.resolve()), "source_commit": "a" * 40,
            }))
            api.INSTALL_CANDIDATE = root / "candidate"
            api.INSTALL_CANDIDATE.mkdir()
            api.LIFEOS_UPDATE_ROOT = root / "jobs"
            api.validate_prepared_lifeos = lambda _: {"upstream_commit": "b" * 40}
            api.load_baseline = lambda path, installed: json.loads(path.read_text())
            launched = []
            api._launch_lifeos_update = lambda job: launched.append(job)

            self.assertEqual(api.get_lifeos_update_status()["state"], "none")
            result = api.apply_lifeos_update()
            self.assertEqual(result["state"], "queued")
            self.assertEqual(launched, [Path(result["job"])])
            request = json.loads((launched[0] / "request.json").read_text())
            self.assertEqual(request["candidate"], str(api.INSTALL_CANDIDATE))
            self.assertEqual(request["prior_source"], str(root / "prior/LifeOS/install"))
            self.assertEqual(api.get_lifeos_update_status()["state"], "queued")
            with self.assertRaises(api.HTTPException) as duplicate:
                api.apply_lifeos_update()
            self.assertEqual(duplicate.exception.status_code, 409)

    def test_reports_interrupted_update_and_launches_recovery(self):
        api = self.load_api(lambda *_: [], lambda *_: [])
        with tempfile.TemporaryDirectory() as directory:
            api.LIFEOS_UPDATE_ROOT = Path(directory)
            api.HERMES_HOME = Path(directory) / 'profile'
            api.HERMES_HOME.mkdir()
            job = api.LIFEOS_UPDATE_ROOT / "update-one"
            (job / "snapshot").mkdir(parents=True)
            (job / "request.json").write_text("{}")
            (job / "status.json").write_text(json.dumps({
                "state": "applying", "unit": "lifeos-bridge-update-test"}))
            (job / "snapshot/manifest.json").write_text(json.dumps({"state": "swapped"}))
            launched = []
            api._launch_lifeos_update = lambda path, action="apply": launched.append((path, action))
            with patch.object(api.subprocess, "run", return_value=types.SimpleNamespace(returncode=3, stdout="inactive")):
                self.assertEqual(api.get_lifeos_update_status()["state"], "interrupted")
                result = api._recover_lifeos_update('dashboard:basic:synthetic-owner')
            self.assertEqual(result["state"], "recovering")
            self.assertEqual(launched, [(job, "recover")])

    def test_stages_host_patch_and_launches_detached_worker(self):
        api = self.load_api(lambda *_: [], lambda *_: [])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            api.INSTALLED_ROOT = root / ".claude"
            (api.INSTALLED_ROOT / "LIFEOS").mkdir(parents=True)
            (api.INSTALLED_ROOT / "LIFEOS/VERSION").write_text("7.40.4\n")
            (api.INSTALLED_ROOT / "settings.json").write_text("{}")
            api.HERMES_HOME = root / ".hermes"
            api.HERMES_HOME.mkdir()
            (api.HERMES_HOME / "config.yaml").write_text("model: local\n")
            api.HERMES_CANDIDATE = root / "candidate"
            api.HERMES_CANDIDATE.mkdir()
            api.HOST_SOURCE = root / "source"
            api.HOST_SOURCE.mkdir()
            api.HOST_PATCH_ROOT = root / "patch-jobs"
            staged = []

            def stage(snapshot, current, candidate, config):
                staged.append((snapshot, current, candidate, config))
                snapshot.mkdir()
                (snapshot / "manifest.json").write_text('{"state": "staged"}')

            api.stage_supported_hermes_patch = stage
            commands = []
            with patch.object(api.subprocess, "run", side_effect=lambda command, **_: commands.append(command) or
                              types.SimpleNamespace(returncode=0, stdout="active")):
                result = api.apply_hermes_installation()
            self.assertEqual(result["state"], "staged")
            self.assertEqual(staged[0][1:], (api.HOST_SOURCE, api.HERMES_CANDIDATE,
                                             api.HERMES_HOME / "config.yaml"))
            self.assertTrue(any(command[0] == "systemd-run" for command in commands))
            self.assertEqual(api.get_host_patch_status()["state"], "staged")

    def test_interrupted_host_change_reports_and_launches_recovery(self):
        api = self.load_api(lambda *_: [], lambda *_: [])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            api.HERMES_HOME = root / ".hermes"
            api.HERMES_HOME.mkdir()
            api.HOST_PATCH_ROOT = root / "patch-jobs"
            snapshot = api.HOST_PATCH_ROOT / "patch-1"
            snapshot.mkdir(parents=True)
            (snapshot / "manifest.json").write_text(json.dumps({"state": "restoring", "unit": "lifeos-bridge-restore-1"}))
            inactive = lambda command, **_: types.SimpleNamespace(returncode=3, stdout="inactive\n", stderr="")
            with patch.object(api.subprocess, "run", side_effect=inactive):
                status = api.get_host_patch_status()
            self.assertEqual((status["state"], status["transaction_state"]), ("interrupted", "restoring"))
            launched = []
            with patch.object(api.subprocess, "run", side_effect=inactive), \
                    patch.object(api, "_launch_host_patch", side_effect=lambda snap, action: launched.append((snap, action))):
                result = api._recover_hermes_installation()
            self.assertEqual(result, {"state": "recovering", "snapshot": str(snapshot)})
            self.assertEqual(launched, [(snapshot, "recover")])
            active = lambda command, **_: types.SimpleNamespace(returncode=0, stdout="active\n", stderr="")
            with patch.object(api.subprocess, "run", side_effect=active):
                self.assertEqual(api.get_host_patch_status()["state"], "restoring")
                with self.assertRaises(api.HTTPException):
                    api._recover_hermes_installation()

    def load_api(self, fields, save):
        settings = types.ModuleType("hermes_cli.plugins_settings")
        settings.plugin_settings_fields = fields
        settings.save_plugin_settings = save
        with patch.dict(sys.modules, {"hermes_cli.plugins_settings": settings}):
            spec = importlib.util.spec_from_file_location("lifeos_dashboard_test", API_PATH)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        return module

    def test_installation_paths_follow_the_selected_lifeos_home(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            account, store = root / "account", root / "store/home"
            profile = account / ".hermes"
            profile.mkdir(parents=True, mode=0o700)
            (store / ".claude").mkdir(parents=True)
            setting = (profile / "lifeos-installation.json")
            setting.write_text(json.dumps({"version": 1, "home": str(store),
                                           "workspace": str(account / "HermesWorkspace")}))
            setting.chmod(0o600)
            with patch.dict(os.environ, {"HOME": str(account), "HERMES_HOME": str(profile)}):
                api = self.load_api(lambda *_: [], lambda *_: None)
            self.assertEqual(api.INSTALLED_ROOT, store / ".claude")
            self.assertEqual(api.BASELINE_PATH,
                             store / ".local/state/lifeos-hook-bridge/version-drift-baseline.json")
            self.assertEqual(api.INSTALL_CANDIDATE, account / ".local/share/lifeos-bridge/lifeos-candidate")
            setting.unlink()
            with patch.dict(os.environ, {"HOME": str(account), "HERMES_HOME": str(profile)}):
                api = self.load_api(lambda *_: [], lambda *_: None)
            self.assertEqual(api.INSTALLED_ROOT, account / ".claude")

    def test_reads_declared_settings(self):
        expected = [{"key": "haiku_effort", "value": "low", "type": "enum"}]
        api = self.load_api(lambda name, path: expected, lambda *_: None)
        self.assertEqual(api.get_settings(), {"fields": expected})

    def test_rejects_unknown_setting(self):
        api = self.load_api(lambda *_: [], lambda *_: (_ for _ in ()).throw(ValueError("unknown key")))
        with self.assertRaises(api.HTTPException) as error:
            api.put_settings({"unknown": "value"})
        self.assertEqual(error.exception.status_code, 400)

    def test_saves_declared_setting(self):
        saved = []
        api = self.load_api(lambda *_: [], lambda name, path, values: saved.append((name, values)) or list(values))
        self.assertEqual(api.put_settings({"haiku_effort": "medium"}), {"saved": ["haiku_effort"], "restart_required": True})
        self.assertEqual(saved, [("lifeos-hook-bridge", {"haiku_effort": "medium"})])

    def test_version_baseline_requires_reviewed_file_list(self):
        api = self.load_api(lambda *_: [], lambda *_: [])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            installed = root / "home" / ".claude"
            for base in (source, installed):
                (base / "LIFEOS/TOOLS").mkdir(parents=True)
                (base / "LIFEOS/VERSION").write_text("7.40.4\n")
                (base / "LIFEOS/TOOLS/Check.ts").write_text("baseline")
            subprocess.run(["git", "init", "-q", str(source)], check=True)
            subprocess.run(["git", "-C", str(source), "add", "LIFEOS"], check=True)
            subprocess.run(["git", "-C", str(source), "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                            "commit", "-qm", "fixture"], check=True)
            api.INSTALLED_ROOT = installed
            api.BASELINE_PATH = root / "config" / "baseline.json"
            self.assertEqual(api.get_version_drift()["state"], "missing")
            diagnostic = api.adapter_error_path(api.BASELINE_PATH)
            diagnostic.parent.mkdir(parents=True)
            diagnostic.write_text(json.dumps({"message": "Baseline missing"}))
            self.assertEqual(api.get_version_drift()["state"], "error")
            preview = api.preview_version_drift({"source": str(source)})
            self.assertEqual(preview["files"], ["LIFEOS/TOOLS/Check.ts"])
            (installed / "LIFEOS/TOOLS/Check.ts").write_text("changed after preview")
            with self.assertRaises(api.HTTPException) as error:
                api.apply_version_drift({"source": str(source), "fingerprint": preview["fingerprint"]})
            self.assertEqual(error.exception.status_code, 409)
            preview = api.preview_version_drift({"source": str(source)})
            applied = api.apply_version_drift({"source": str(source), "fingerprint": preview["fingerprint"]})
            self.assertEqual(applied["state"], "ready")
            self.assertFalse(diagnostic.exists())
            self.assertEqual(json.loads(api.BASELINE_PATH.read_text())["version"], "7.40.4")
            self.assertEqual(api.BASELINE_PATH.stat().st_mode & 0o777, 0o600)
            self.assertEqual(api.get_version_drift()["changed_count"], 0)
            (installed / "LIFEOS/VERSION").write_text("7.40.5\n")
            self.assertTrue(api.get_version_drift()["version_mismatch"])
            (installed / "LIFEOS/VERSION").write_text("7.40.4\n")
            diagnostic.write_text(json.dumps({"message": "Adapter could not read baseline"}))
            self.assertEqual(api.get_version_drift(), {
                "state": "error", "message": "Adapter could not read baseline", "baseline_exists": True,
            })
            diagnostic.unlink()
            with self.assertRaises(api.HTTPException) as error:
                api.apply_version_drift({"source": str(source), "fingerprint": preview["fingerprint"]})
            self.assertEqual(error.exception.status_code, 409)
            api.BASELINE_PATH.write_text("{")
            self.assertEqual(api.get_version_drift()["baseline_exists"], True)
            recovered = api.apply_version_drift({
                "source": str(source), "fingerprint": preview["fingerprint"], "renew": True,
            })
            self.assertEqual(recovered["state"], "ready")


if __name__ == "__main__":
    unittest.main()
