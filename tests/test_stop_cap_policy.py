# ABOUTME: Checks that a real native Stop block uses the configured cap policy.
# ABOUTME: Registers the bridge through its Hermes entry point with disposable hook settings.

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from lifeos_hook_bridge import register


class Context:
    def __init__(self, settings):
        self.settings = settings
        self.hooks = {}
        self.unload = []

    def get_config(self, key, default=None):
        return self.settings.get(key, default)

    def register_hook(self, name, callback):
        self.hooks[name] = callback

    def on_unload(self, callback):
        self.unload.append(callback)


class StopCapPolicyTests(unittest.TestCase):
    def test_native_stop_block_uses_configured_cap_policy(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            hook = root / "block.py"
            hook.write_text('import json\nprint(json.dumps({"decision":"block","reason":"run checks"}))\n')
            settings = root / "settings.json"
            settings.write_text(json.dumps({"hooks": {"Stop": [{"hooks": [
                {"type": "command", "command": f"{sys.executable} {hook}"},
            ]}]}}))
            with patch.dict(os.environ, {"LIFEOS_HOOK_SETTINGS": str(settings)}):
                for policy, expected in (
                    ({}, {"action": "continue", "message": "run checks"}),
                    ({"stop_cap_policy": "fail_closed"},
                     {"action": "continue", "message": "run checks", "on_limit": "fail"}),
                ):
                    context = Context(policy)
                    register(context)
                    result = context.hooks["pre_turn_stop"](
                        final_response="candidate", session_id="stop-policy-test", attempt=0,
                    )
                    self.assertEqual(result, expected)
                    for callback in context.unload:
                        callback()


if __name__ == "__main__":
    unittest.main()
