# ABOUTME: Verifies managed-account admission before removal of account-wide launchers.
# ABOUTME: Refuses other profiles and modified or non-default installation layouts.
from pathlib import Path
import tempfile
import unittest


class RemovalGenerationTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory();self.addCleanup(self.directory.cleanup)
        self.home=Path(self.directory.name);self.profile=self.home/'.hermes';self.profile.mkdir(mode=0o700)
        self.installed=self.home/'.claude';self.installed.mkdir(mode=0o700)

    def operation(self):
        from optional.lifeos_release_manager.removal_generation import account
        return account

    def test_one_default_profile_is_admitted_without_changing_files(self):
        self.assertEqual(self.operation()(self.profile,self.installed),self.home)
        self.assertEqual(sorted(path.name for path in self.home.iterdir()),['.claude','.hermes'])

    def test_another_profile_refuses_account_wide_software_removal(self):
        (self.profile/'profiles/another').mkdir(parents=True)
        with self.assertRaises(ValueError):self.operation()(self.profile,self.installed)

    def test_named_profile_or_selected_external_home_refuses(self):
        other=self.home/'external/.claude';other.mkdir(parents=True)
        with self.assertRaises(ValueError):self.operation()(self.profile,other)
        named=self.profile/'profiles/testing';named.mkdir(parents=True)
        with self.assertRaises(ValueError):self.operation()(named,self.installed)
