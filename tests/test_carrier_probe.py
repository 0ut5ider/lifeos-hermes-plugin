# ABOUTME: Checks Hermes carrier evidence freshness and route-change invalidation.
# ABOUTME: Keeps the persistent LifeOS integrity gate tied to an observed child run.

import datetime as dt
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from lifeos_hook_bridge import carrier_probe
from lifeos_hook_bridge.carrier_probe import check_main_rung, check_state, route_fingerprint


class CarrierProbeTests(unittest.TestCase):
    def setUp(self):
        self.route = route_fingerprint("custom", "local-model", "xhigh", "http://127.0.0.1:3000/v1", "chat_completions")
        self.now = dt.datetime(2026, 9, 28, 15, 0, tzinfo=dt.timezone.utc)
        self.state = {
            "ts": "2026-09-28T14:00:00+00:00",
            "verdict": "HOLDS",
            "route_fingerprint": self.route,
            "observed": {"provider": "custom", "model": "local-model", "effort": "xhigh", "api_calls": 1},
        }

    def test_fresh_observed_route_passes(self):
        self.assertEqual(check_state(self.state, self.route, now=self.now), (True, "HOLDS"))

    def test_unprobed_route_fails(self):
        self.assertEqual(check_state(None, self.route, now=self.now), (False, "NEVER RUN"))

    def test_configured_model_change_invalidates_probe(self):
        changed = route_fingerprint("custom", "other-model", "xhigh", "http://127.0.0.1:3000/v1", "chat_completions")
        self.assertEqual(check_state(self.state, changed, now=self.now), (False, "ROUTE CHANGED"))

    def test_effort_and_endpoint_change_invalidate_probe(self):
        for effort, endpoint in (("high", "http://127.0.0.1:3000/v1"),
                                 ("xhigh", "http://127.0.0.1:3001/v1")):
            changed = route_fingerprint("custom", "local-model", effort, endpoint, "chat_completions")
            self.assertEqual(check_state(self.state, changed, now=self.now), (False, "ROUTE CHANGED"))

    def test_stale_and_failed_evidence_do_not_pass(self):
        old = dict(self.state, ts="2026-08-28T14:00:00+00:00")
        self.assertEqual(check_state(old, self.route, now=self.now), (False, "STALE"))
        failed = dict(self.state, verdict="INCONCLUSIVE")
        self.assertEqual(check_state(failed, self.route, now=self.now), (False, "INCONCLUSIVE"))

    def test_missing_execution_evidence_does_not_pass(self):
        incomplete = dict(self.state, observed={"provider": "custom", "model": "local-model", "effort": "xhigh", "api_calls": 0})
        self.assertEqual(check_state(incomplete, self.route, now=self.now), (False, "INCONCLUSIVE"))

    def test_main_rung_matches_provider_model_and_effort(self):
        self.assertEqual(
            check_main_rung(("custom", "local-model", "xhigh"), ("custom", "local-model", "xhigh")),
            (True, "HOLDS"),
        )
        self.assertEqual(
            check_main_rung(("custom", "local-model", "medium"), ("custom", "local-model", "xhigh")),
            (False, "MAIN EFFORT MISMATCH"),
        )
        self.assertEqual(
            check_main_rung(("cloud", "local-model", "xhigh"), ("custom", "local-model", "xhigh")),
            (False, "MAIN PROVIDER MISMATCH"),
        )

    def test_failed_live_probe_invalidates_previous_success(self):
        with tempfile.TemporaryDirectory() as directory:
            state_path = Path(directory) / "carrier.json"
            state_path.write_text(json.dumps(self.state))
            route = ("custom", "local-model", "xhigh", {
                "base_url": "http://127.0.0.1:3000/v1", "api_mode": "chat_completions",
            })
            with patch.object(carrier_probe, "_state_path", return_value=state_path), \
                    patch.object(carrier_probe, "_route", return_value=route), \
                    patch.object(carrier_probe, "_run_child", side_effect=RuntimeError("model unavailable")), \
                    patch("sys.stderr", new_callable=io.StringIO):
                self.assertEqual(carrier_probe.main(["--run"]), 2)
            self.assertEqual(json.loads(state_path.read_text())["verdict"], "INCONCLUSIVE")

    def test_saved_plugin_tiers_are_used_without_hook_environment(self):
        config = {"plugins": {"entries": {"lifeos-hook-bridge": {"settings": {
            "fable_provider": "custom", "fable_model": "alternate-local", "fable_effort": "ultra",
        }}}}}
        with patch.dict("os.environ", {}, clear=True):
            self.assertEqual(
                carrier_probe._mapping(config)["fable"],
                {"provider": "custom", "model": "alternate-local", "effort": "ultra"},
            )

    def test_unsaved_tiers_use_hermes_current_model(self):
        config = {"model": {"provider": "custom", "default": "flashnext"},
                  "plugins": {"entries": {"lifeos-hook-bridge": {"settings": {
                      "sonnet_inherit_child_default": True,
                  }}}}}
        with patch.dict("os.environ", {}, clear=True):
            mapping = carrier_probe._mapping(config)
        self.assertEqual(mapping["haiku"], {"provider": "custom", "model": "flashnext", "effort": "low"})
        self.assertEqual(mapping["sonnet"], {"provider": "", "model": "", "effort": "medium"})


if __name__ == "__main__":
    unittest.main()
