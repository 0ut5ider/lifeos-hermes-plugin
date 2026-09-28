# ABOUTME: Checks that Hermes Stop hooks receive the effort sent to the model.
# ABOUTME: Uses the installed Hermes core extension when its source is available.

import unittest
from types import SimpleNamespace
from unittest.mock import patch

try:
    from agent.turn_stop_gates import _pre_turn_stop_nudge
except ImportError:
    _pre_turn_stop_nudge = None


@unittest.skipUnless(_pre_turn_stop_nudge, "Hermes source is required")
class CoreStopEffortTests(unittest.TestCase):
    def test_stop_hook_receives_wire_effort(self):
        agent = SimpleNamespace(
            session_id="effort-probe", platform="cli", model="flashnext-w4a16-fp8ple",
            reasoning_config={"enabled": True, "effort": "medium"},
            _wire_reasoning_config={"enabled": True, "effort": "xhigh"},
        )
        with (
            patch("hermes_cli.lifecycle.has_hook", return_value=True),
            patch("hermes_cli.plugins.get_pre_turn_stop_continue_message", return_value=None) as hook,
        ):
            _pre_turn_stop_nudge(agent, "answer", 0)
        self.assertEqual(hook.call_args.kwargs["reasoning_effort"], "xhigh")
