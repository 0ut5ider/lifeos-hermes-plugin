# ABOUTME: Verifies configurable LifeOS tier routes and the local model fallback.
# ABOUTME: Checks that invalid dashboard values cannot silently change inference routes.

import unittest

from lifeos_hook_bridge.model_tiers import configured_model_map, resolve_route, route_delegate_args


class ModelTierTests(unittest.TestCase):
    def test_hermes_current_model_is_the_default_for_all_tiers(self):
        mapping = configured_model_map(
            {}.get, default_provider="custom", default_model="flashnext",
        )
        self.assertEqual({tier: (mapping[tier]["provider"], mapping[tier]["model"], mapping[tier]["effort"])
                          for tier in ("haiku", "sonnet", "opus", "fable")}, {
            "haiku": ("custom", "flashnext", "low"),
            "sonnet": ("custom", "flashnext", "medium"),
            "opus": ("custom", "flashnext", "xhigh"),
            "fable": ("custom", "flashnext", "xhigh"),
        })

    def test_explicit_child_default_and_selected_model_override_hermes_default(self):
        mapping = configured_model_map({
            "haiku_inherit_child_default": True,
            "sonnet_provider": "second", "sonnet_model": "another-model",
        }.get, default_provider="custom", default_model="flashnext")
        self.assertEqual(mapping["haiku"]["model"], "")
        self.assertEqual(mapping["haiku"]["provider"], "")
        self.assertEqual(resolve_route("haiku", "model-env-default", mapping),
                         ("", "model-env-default", "low"))
        self.assertEqual(resolve_route("sonnet", "", mapping),
                         ("second", "another-model", "medium"))
        self.assertEqual(resolve_route("fable", "", mapping),
                         ("custom", "flashnext", "xhigh"))

    def test_defaults_use_one_model_with_three_efforts(self):
        mapping = configured_model_map(lambda key, default: default)
        self.assertEqual(mapping["pin"], "fable")
        self.assertEqual(
            {tier: (route["provider"], route["model"], route["effort"]) for tier, route in mapping.items() if tier != "pin"},
            {
                "haiku": ("", "", "low"), "sonnet": ("", "", "medium"),
                "opus": ("", "", "xhigh"), "fable": ("", "", "xhigh"),
            },
        )
        self.assertEqual(resolve_route("claude-opus-5", "default-local", mapping), ("", "default-local", "xhigh"))

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
                self.assertEqual(resolve_route(tier, "", mapping), ("", model, effort))

    def test_direct_route_includes_selected_provider(self):
        mapping = configured_model_map({
            "haiku_provider": "local-fast", "haiku_model": "small-model",
        }.get)
        self.assertEqual(resolve_route("haiku", "default-local", mapping),
                         ("local-fast", "small-model", "low"))

    def test_invalid_pin_and_effort_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "pinned_tier"):
            configured_model_map({"pinned_tier": "unknown"}.get)
        with self.assertRaisesRegex(ValueError, "sonnet_effort"):
            configured_model_map({"sonnet_effort": "unbounded"}.get)
        with self.assertRaisesRegex(ValueError, "no configured model"):
            resolve_route("sonnet", "", configured_model_map(lambda key, default: default))
        with self.assertRaisesRegex(ValueError, "haiku_provider"):
            configured_model_map({"haiku_provider": "bad\nprovider"}.get)
        with self.assertRaisesRegex(ValueError, "haiku_provider requires"):
            configured_model_map({"haiku_provider": "custom"}.get, default_model="flashnext")

    def test_delegated_tier_carries_selected_provider(self):
        mapping = configured_model_map({
            "haiku_provider": "local-fast", "haiku_model": "small-model",
        }.get)
        routed = route_delegate_args({"tasks": [{"goal": "quick", "model": "haiku"}]}, mapping)
        self.assertEqual(routed["tasks"], [{
            "goal": "quick", "model": "small-model", "provider": "local-fast", "reasoning_effort": "low",
        }])

    def test_delegated_tiers_use_configured_routes(self):
        mapping = configured_model_map({
            "haiku_model": "fast-local", "sonnet_model": "balanced-local",
            "fable_model": "largest-local", "fable_effort": "ultra",
        }.get)
        args = {"tasks": [
            {"goal": "quick", "model": "haiku"},
            {"goal": "review", "model": "claude-sonnet-4"},
            {"goal": "advise", "model": "fable"},
            {"goal": "direct", "model": "named-local", "reasoning_effort": "high"},
        ]}
        routed = route_delegate_args(args, mapping)
        self.assertEqual([(task.get("model"), task.get("reasoning_effort")) for task in routed["tasks"]], [
            ("fast-local", "low"), ("balanced-local", "medium"),
            ("largest-local", "ultra"), ("named-local", "high"),
        ])
        self.assertEqual(args["tasks"][0]["model"], "haiku")

    def test_unset_model_inherits_hermes_parent_with_mapped_effort(self):
        routed = route_delegate_args(
            {"goal": "advise", "model": "fable"}, configured_model_map(lambda key, default: default),
        )
        self.assertEqual(routed, {"tasks": [{"goal": "advise", "reasoning_effort": "xhigh"}]})


if __name__ == "__main__":
    unittest.main()
