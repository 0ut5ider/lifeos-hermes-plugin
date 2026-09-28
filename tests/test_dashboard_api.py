# ABOUTME: Verifies the LifeOS dashboard reads and saves only declared plugin settings.
# ABOUTME: Uses a fake Hermes settings service so the API boundary is testable locally.

import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


API_PATH = Path(__file__).resolve().parents[1] / "lifeos_hook_bridge/dashboard/plugin_api.py"


class DashboardApiTests(unittest.TestCase):
    def load_api(self, fields, save):
        fastapi = types.ModuleType("fastapi")
        fastapi.APIRouter = lambda: types.SimpleNamespace(
            get=lambda _path: lambda handler: handler,
            put=lambda _path: lambda handler: handler,
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


if __name__ == "__main__":
    unittest.main()
