# ABOUTME: Verifies authenticated memory policy independently of messaging transport.
# ABOUTME: Exercises identity bindings, audience restrictions, and changing session scopes.

import unittest

from lifeos_hook_bridge.memory_policy import MemoryPolicy, SessionContext


class MemoryPolicyTests(unittest.TestCase):
    def setUp(self):
        self.policy = MemoryPolicy({
            "version": 1, "principal": "owner",
            "accounts": {"app-one:123": "owner", "app-two:456": "owner"},
            "destinations": {
                "app-one:private-a": {"visibility": "private", "participants": ["owner"],
                                        "read": ["project", "principal", "assistant"],
                                        "write": ["project", "principal", "assistant"]},
                "app-two:private-b": {"visibility": "private", "participants": ["owner"],
                                        "read": ["project", "principal", "assistant"],
                                        "write": ["project", "principal", "assistant"]},
                "app-one:shared": {"visibility": "shared", "participants": ["owner", "guest"],
                                     "read": ["project"], "write": ["project"]},
            },
        })

    def context(self, app="app-one", author="123", destination="private-a", visibility="private"):
        return SessionContext(app, author, destination, visibility, ("owner",), "local", "session")

    def test_equivalent_accounts_have_equivalent_memory_access(self):
        first = self.policy.resolve(self.context())
        second = self.policy.resolve(self.context("app-two", "456", "private-b"))
        self.assertEqual(first.read, second.read)
        self.assertEqual(first.write, second.write)
        self.assertEqual(first.principal, second.principal)

    def test_display_name_or_unbound_account_does_not_authenticate(self):
        self.assertEqual(self.policy.resolve(self.context(author="owner")).read, ())

    def test_unknown_audience_and_visibility_are_restricted(self):
        self.assertEqual(self.policy.resolve(self.context(destination="unknown")).read, ())
        self.assertEqual(self.policy.resolve(self.context(visibility="unknown")).read, ())

    def test_shared_audience_requires_verified_participants(self):
        context = SessionContext("app-one", "123", "shared", "shared", ("owner", "guest"), "local", "session")
        scope = self.policy.resolve(context)
        self.assertEqual(scope.read, ("project",))
        self.assertNotIn("principal", scope.write)
        changed = SessionContext("app-one", "123", "shared", "shared", ("owner", "stranger"), "local", "session")
        self.assertEqual(self.policy.resolve(changed).read, ())

    def test_scope_changes_when_audience_route_or_author_changes(self):
        original = self.policy.resolve(self.context()).signature
        routed = SessionContext("app-one", "123", "private-a", "private", ("owner",), "cloud", "session")
        self.assertNotEqual(original, self.policy.resolve(routed).signature)
        self.assertNotEqual(original, self.policy.resolve(self.context(author="other")).signature)

    def test_invalid_policy_fails_instead_of_granting_access(self):
        with self.assertRaises(ValueError):
            MemoryPolicy({"version": 99, "principal": "owner", "accounts": {}, "destinations": {}})
        with self.assertRaises(ValueError):
            MemoryPolicy({"version": 1, "principal": "owner", "accounts": {"app:user": "owner"},
                          "destinations": {"app:place": {"read": ["all"], "write": []}}})


if __name__ == "__main__":
    unittest.main()
