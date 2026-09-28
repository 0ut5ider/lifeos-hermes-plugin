# ABOUTME: Checks Claude file-rule matching for Bash file targets.
# ABOUTME: Covers source anchors, glob depth, and symlink destinations.

import tempfile
import unittest
import subprocess
from pathlib import Path

from lifeos_hook_bridge.file_permissions import file_target_decision, resolve_backend_path


class FilePermissionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.project = self.root / "project"
        self.project.mkdir()

    def decide(self, target, rules, operation="write", source=None, cwd=None):
        return file_target_decision(
            target, operation, str(cwd or self.project),
            [(rules, str(source or self.project))], host_paths=True,
        )

    def test_relative_rule_uses_current_directory(self):
        cwd = self.project / "nested"
        cwd.mkdir()
        rules = {"deny": ["Edit(./blocked.txt)"]}
        self.assertEqual(self.decide("blocked.txt", rules, cwd=cwd), "deny")
        self.assertEqual(self.decide("../blocked.txt", rules, cwd=cwd), "unknown")

    def test_source_rule_uses_settings_anchor(self):
        rules = {"deny": ["Edit(/blocked.txt)"]}
        self.assertEqual(self.decide("blocked.txt", rules, source=self.project), "deny")
        nested = self.project / "nested"
        nested.mkdir()
        self.assertEqual(self.decide("blocked.txt", rules, source=self.project, cwd=nested), "allow")

    def test_absolute_rule_and_glob_depth(self):
        target = self.project / "vendor/secrets/token.txt"
        target.parent.mkdir(parents=True)
        absolute = {"deny": [f"Edit(//{str(target).lstrip('/')})"]}
        self.assertEqual(self.decide(str(target), absolute), "deny")
        nested = {"deny": ["Edit(secrets/**)"]}
        self.assertEqual(self.decide("vendor/secrets/token.txt", nested), "deny")
        anchored = {"deny": ["Edit(/secrets/**)"]}
        self.assertEqual(self.decide("vendor/secrets/token.txt", anchored), "allow")

    def test_symlink_target_denial_and_allow(self):
        secret = self.root / "secret.txt"
        secret.write_text("secret")
        link = self.project / "link.txt"
        link.symlink_to(secret)
        deny = {"deny": [f"Edit(//{str(secret).lstrip('/')})"]}
        self.assertEqual(self.decide("link.txt", deny), "deny")
        allow = {"allow": ["Edit(./link.txt)"]}
        self.assertEqual(self.decide("link.txt", allow), "unknown")

    def test_remote_symlink_uses_resolved_destination(self):
        secret = self.root / "secret.txt"
        secret.write_text("secret")
        link = self.project / "link.txt"
        link.symlink_to(secret)
        rules = [({"deny": [f"Read(//{str(secret).lstrip('/')})"]}, str(self.project))]
        self.assertEqual(file_target_decision(
            "link.txt", "read", str(self.project), rules, host_paths=False,
            resolved_path=str(secret),
        ), "deny")
        self.assertEqual(file_target_decision(
            "link.txt", "read", str(self.project), rules, host_paths=False,
        ), "unknown")

    def test_backend_resolves_remote_symlink_without_interpreting_filename(self):
        secret = self.root / "secret's.txt"
        secret.write_text("secret")
        (self.project / "link.txt").symlink_to(secret)

        class ShellBackend:
            def execute(self, command, cwd, timeout):
                process = subprocess.run(
                    ["bash", "-c", command], cwd=cwd, capture_output=True,
                    text=True, timeout=timeout,
                )
                return {"returncode": process.returncode, "output": process.stdout + process.stderr}

        self.assertEqual(resolve_backend_path("link.txt", str(self.project), ShellBackend()), str(secret))

    def test_read_deny_applies_to_output_target(self):
        self.assertEqual(self.decide("blocked.txt", {"deny": ["Read(./blocked.txt)"]}), "deny")

    def test_negation_only_carves_same_source(self):
        rules = {"deny": ["Edit(*.env)", "Edit(!sample.env)"]}
        self.assertEqual(self.decide("sample.env", rules), "allow")
        self.assertEqual(self.decide("private.env", rules), "deny")
        separate = [({"deny": ["Edit(*.env)"]}, str(self.project)),
                    ({"deny": ["Edit(!sample.env)"]}, str(self.project))]
        self.assertEqual(file_target_decision("sample.env", "write", str(self.project),
                                               separate, host_paths=True), "deny")

    def test_negation_does_not_reopen_anchored_or_blocked_directory(self):
        path = self.project / "sample.env"
        anchored = {"deny": [f"Edit(//{str(path).lstrip('/')})", "Edit(!sample.env)"]}
        self.assertEqual(self.decide("sample.env", anchored), "deny")
        directory = {"deny": ["Edit(secrets/**)", "Edit(!secrets/public/**)"]}
        self.assertEqual(self.decide("secrets/public/sample.env", directory), "deny")
