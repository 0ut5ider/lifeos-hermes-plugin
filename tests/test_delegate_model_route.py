# ABOUTME: Checks that LifeOS Agent tier aliases become Hermes child model and effort routes.
# ABOUTME: Uses the bridge callback that Hermes invokes before child construction.

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from lifeos_hook_bridge.bridge import HookBridge
from lifeos_hook_bridge.model_tiers import configured_model_map


class DelegateModelRouteTests(unittest.TestCase):
    def test_agent_hook_keeps_requested_tier_and_routes_actual_child(self):
        with TemporaryDirectory(prefix="delegate-route-") as directory:
            root = Path(directory)
            settings = root / "settings.json"
            settings.write_text(json.dumps({"hooks": {}}))
            mapping = configured_model_map({"fable_model": "largest-local", "fable_effort": "ultra"}.get)
            bridge = HookBridge(settings, root, model_tiers_provider=lambda: mapping)
            try:
                args = {"tasks": [{"goal": "Inspect the report", "model": "fable"}]}
                verdict = bridge.pre_tool_call("delegate_task", args, session_id="tier-route")
                self.assertEqual(verdict, {"action": "modify", "args": {
                    "tasks": [{"goal": "Inspect the report", "model": "largest-local",
                               "reasoning_effort": "ultra"}],
                }})
            finally:
                bridge.close()


if __name__ == "__main__":
    unittest.main()
