# ABOUTME: Checks that unloading the plugin stops its background hook bridge workers.
# ABOUTME: Uses a disposable LifeOS settings file and the real bridge watcher thread.

import json
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from lifeos_hook_bridge import register


class PluginLifecycleTests(unittest.TestCase):
    def test_stock_hermes_registers_only_supported_hooks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            settings = root / "settings.json"
            marker = root / "post-tool-ran"
            hook = root / "record.py"
            hook.write_text(
                "import json,sys\nfrom pathlib import Path\n"
                "json.load(sys.stdin)\n"
                f"Path({str(marker)!r}).write_text('ran')\n"
            )
            settings.write_text(json.dumps({"hooks": {"PostToolUse": [{"matcher": "Read", "hooks": [{
                "type": "command", "command": f"python3 {hook}",
            }]}]}}))

            class Context:
                def __init__(self):
                    self.hooks = {}
                    self.unload = []

                def register_cli_command(self, name, **entry):
                    pass

                def get_config(self, name, default=None):
                    return default

                def register_hook(self, name, callback):
                    self.hooks.setdefault(name, []).append(callback)

                def on_unload(self, callback):
                    self.unload.append(callback)

            host = types.ModuleType("hermes_cli.plugins")
            host.VALID_HOOKS = {
                "pre_tool_call", "post_tool_call", "pre_llm_call", "on_session_finalize",
                "api_request_error", "transform_tool_result",
            }
            ctx = Context()
            with patch.dict(sys.modules, {"hermes_cli": types.ModuleType("hermes_cli"),
                                          "hermes_cli.plugins": host}):
                with patch.dict(os.environ, {"LIFEOS_HOOK_SETTINGS": str(settings)}):
                    register(ctx)
            self.addCleanup(lambda: [callback() for callback in ctx.unload])
            self.assertEqual(set(ctx.hooks), {
                "pre_tool_call", "post_tool_call", "pre_llm_call", "on_session_finalize",
                "api_request_error",
            })
            for callback in ctx.hooks["post_tool_call"]:
                callback("read_file", {"path": str(root / "note.txt")}, "synthetic result",
                         session_id="stock-test", tool_call_id="call-1")
            self.assertEqual(marker.read_text(), "ran")

    def test_plugin_loads_before_lifeos_installation(self):
        with tempfile.TemporaryDirectory() as directory:
            settings = Path(directory) / "missing-settings.json"

            class Context:
                def __init__(self):
                    self.hooks = {}
                    self.unload = []

                def register_cli_command(self, name, **entry):
                    pass

                def get_config(self, name, default=None):
                    return default

                def register_hook(self, name, callback):
                    self.hooks[name] = callback

                def on_unload(self, callback):
                    self.unload.append(callback)

            ctx = Context()
            with patch.dict(os.environ, {"LIFEOS_HOOK_SETTINGS": str(settings), "HERMES_HOME": directory}):
                register(ctx)
            if 'pre_message_delivery' in ctx.hooks:
                self.assertEqual(set(ctx.hooks), {'pre_message_delivery'})
                self.assertEqual(ctx.hooks['pre_message_delivery'](
                    platform='discord',chat_id='60',guild_id='10',hermes_home=directory)['action'],'block')
            else:
                self.assertEqual(ctx.hooks, {})
            self.assertEqual(ctx.unload, [])

    def test_unload_stops_config_watcher(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            settings = root / "settings.json"
            settings.write_text(json.dumps({
                "hooks": {"ConfigChange": [{"matcher": "skills", "hooks": [
                    {"type": "command", "command": "true"},
                ]}]},
            }))

            class Context:
                def __init__(self):
                    self.hooks = {}
                    self.unload = []

                def register_cli_command(self, name, **entry):
                    pass

                def get_config(self, name, default=None):
                    return default

                def register_hook(self, name, callback):
                    self.hooks[name] = callback

                def on_unload(self, callback):
                    self.unload.append(callback)

            ctx = Context()
            with patch.dict(os.environ, {"LIFEOS_HOOK_SETTINGS": str(settings)}):
                register(ctx)
            bridge = ctx.hooks["pre_tool_call"].__self__
            self.addCleanup(bridge.close)
            bridge._start_config_watcher()
            self.assertTrue(bridge.watcher.is_alive())
            for callback in ctx.unload:
                callback()
            self.assertFalse(bridge.watcher.is_alive())
