# ABOUTME: Verifies the LifeOS dashboard reads and saves only declared plugin settings.
# ABOUTME: Uses a fake Hermes settings service so the API boundary is testable locally.

import importlib.util
import json
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch


API_PATH = Path(__file__).resolve().parents[1] / "lifeos_hook_bridge/dashboard/plugin_api.py"


class DashboardApiTests(unittest.TestCase):
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
                self.assertEqual(api.get_installation()["hermes"], "patched_hooks_present")

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

    def load_api(self, fields, save):
        fastapi = types.ModuleType("fastapi")
        fastapi.APIRouter = lambda: types.SimpleNamespace(
            get=lambda _path: lambda handler: handler,
            put=lambda _path: lambda handler: handler,
            post=lambda _path: lambda handler: handler,
        )
        class HTTPException(Exception):
            def __init__(self, status_code, detail):
                super().__init__(detail)
                self.status_code = status_code
                self.detail = detail

        fastapi.HTTPException = HTTPException
        settings = types.ModuleType("hermes_cli.plugins_settings")
        settings.plugin_settings_fields = fields
        settings.save_plugin_settings = save
        with patch.dict(sys.modules, {"fastapi": fastapi, "hermes_cli": types.ModuleType("hermes_cli"), "hermes_cli.plugins_settings": settings}):
            spec = importlib.util.spec_from_file_location("lifeos_dashboard_test", API_PATH)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        return module

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
