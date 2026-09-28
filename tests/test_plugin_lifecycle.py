# ABOUTME: Checks that unloading the plugin stops its background hook bridge workers.
# ABOUTME: Uses a disposable LifeOS settings file and the real bridge watcher thread.

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from lifeos_hook_bridge import register


class PluginLifecycleTests(unittest.TestCase):
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
