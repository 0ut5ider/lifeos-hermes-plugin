# ABOUTME: Verifies configurable LifeOS tier routes and the local model fallback.
# ABOUTME: Checks that invalid dashboard values cannot silently change inference routes.

import unittest

from lifeos_hook_bridge.model_tiers import configured_model_map, resolve_route


class ModelTierTests(unittest.TestCase):
    def test_defaults_use_one_model_with_three_efforts(self):
        mapping = configured_model_map(lambda key, default: default)
        self.assertEqual(mapping["pin"], "fable")
        self.assertEqual(
            {tier: (route["model"], route["effort"]) for tier, route in mapping.items() if tier != "pin"},
            {
                "haiku": ("", "low"), "sonnet": ("", "medium"),
                "opus": ("", "xhigh"), "fable": ("", "xhigh"),
            },
        )
        self.assertEqual(resolve_route("claude-opus-5", "default-local", mapping), ("default-local", "xhigh"))

    def test_each_tier_can_select_its_own_model_and_effort(self):
        settings = {
            "pinned_tier": "opus", "haiku_model": "fast-local", "haiku_effort": "minimal",
            "sonnet_model": "balanced-local", "sonnet_effort": "high",
            "opus_model": "large-local", "opus_effort": "max",
            "fable_model": "largest-local", "fable_effort": "ultra",
        }
        mapping = configured_model_map(settings.get)
        self.assertEqual(mapping["pin"], "opus")
        for tier, model, effort in (
            ("haiku", "fast-local", "minimal"),
            ("sonnet", "balanced-local", "high"),
            ("opus", "large-local", "max"),
            ("fable", "largest-local", "ultra"),
        ):
            with self.subTest(tier=tier):
                self.assertEqual(resolve_route(tier, "", mapping), (model, effort))

    def test_invalid_pin_and_effort_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "pinned_tier"):
            configured_model_map({"pinned_tier": "unknown"}.get)
        with self.assertRaisesRegex(ValueError, "sonnet_effort"):
            configured_model_map({"sonnet_effort": "unbounded"}.get)
        with self.assertRaisesRegex(ValueError, "no configured model"):
            resolve_route("sonnet", "", configured_model_map(lambda key, default: default))


if __name__ == "__main__":
    unittest.main()
