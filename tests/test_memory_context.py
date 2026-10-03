# ABOUTME: Verifies memory context admission uses host identities and actual destinations.
# ABOUTME: Covers equivalent messaging apps, unknown audiences, schedules, and model routes.

import unittest

from lifeos_hook_bridge.memory_context import host_context, route_identity
from lifeos_hook_bridge.memory_policy import MemoryPolicy


class MemoryContextTests(unittest.TestCase):
    def setUp(self):
        self.route = route_identity("local-provider", "private-model", "http://192.168.8.200:8000/v1", "chat_completions")
        grant = {"visibility": "private", "participants": ["owner"], "read": ["principal", "project"],
                 "write": ["project"], "projects": ["lab"], "model_routes": [self.route]}
        self.configuration = {"version": 1, "principal": "owner", "accounts": {"chat-a:100": "owner", "chat-b:300": "owner"},
                              "destinations": {"chat-a:200": grant, "chat-b:400": grant}}

    def context(self, platform="chat-a", user="100", chat="200", **changes):
        metadata = {"HERMES_SESSION_PLATFORM": platform, "HERMES_SESSION_USER_ID": user,
                    "HERMES_SESSION_CHAT_ID": chat, "HERMES_SESSION_CHAT_TYPE": "dm", "HERMES_SESSION_ID": "session"}
        metadata.update(changes)
        return host_context(self.configuration, metadata, model_route=self.route, hermes_home="/synthetic/profile")

    def test_private_conversations_have_the_same_policy_on_different_apps(self):
        policy = MemoryPolicy(self.configuration)
        a = policy.resolve(self.context())
        b = policy.resolve(self.context("chat-b", "300", "400"))
        self.assertEqual(a.read, b.read)
        self.assertEqual(a.write, b.write)
        self.assertEqual(a.principal, "owner")
        self.assertNotEqual(a.writer, b.writer)

    def test_display_names_and_unknown_audiences_cannot_authorize_private_memory(self):
        context = self.context(user="unbound", HERMES_SESSION_USER_NAME="owner")
        self.assertEqual(MemoryPolicy(self.configuration).resolve(context).read, ())
        context = self.context(HERMES_SESSION_CHAT_TYPE="channel")
        self.assertEqual(context.visibility, "unknown")
        self.assertEqual(MemoryPolicy(self.configuration).resolve(context).read, ())

    def test_schedule_binds_its_delivery_destination_and_does_not_assume_a_private_author(self):
        context = self.context(HERMES_CRON_SESSION="1", HERMES_CRON_AUTO_DELIVER_PLATFORM="chat-b",
                               HERMES_CRON_AUTO_DELIVER_CHAT_ID="400")
        self.assertEqual((context.transport, context.destination), ("chat-b", "400"))
        self.assertEqual(context.author, "")
        self.assertEqual(MemoryPolicy(self.configuration).resolve(context).read, ())

    def test_actual_thread_and_author_change_the_context_instead_of_reusing_the_parent_grant(self):
        context = self.context(HERMES_SESSION_THREAD_ID="201")
        self.assertEqual(context.destination, "200/201")
        self.assertEqual(MemoryPolicy(self.configuration).resolve(context).read, ())
        context = host_context(self.configuration, {"HERMES_SESSION_PLATFORM": "chat-a", "HERMES_SESSION_USER_ID": "100",
                                "HERMES_SESSION_CHAT_ID": "200", "HERMES_SESSION_CHAT_TYPE": "dm"}, model_route=self.route,
                               hermes_home="/synthetic/profile", author_id="other")
        self.assertEqual(context.author, "other")
        self.assertEqual(MemoryPolicy(self.configuration).resolve(context).read, ())

    def test_route_identity_changes_when_a_model_moves_to_another_endpoint(self):
        cloud = route_identity("local-provider", "private-model", "https://example.com/v1", "chat_completions")
        self.assertNotEqual(self.route, cloud)
        self.assertEqual(route_identity("local-provider", "private-model", "http://user:password@host/v1", "chat_completions"), "unknown")


if __name__ == "__main__":
    unittest.main()
