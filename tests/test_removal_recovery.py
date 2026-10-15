# ABOUTME: Checks standalone recovery authentication against the actual Hermes basic provider.
# ABOUTME: Refuses invalid credentials and another owner without printing or saving passwords.
from pathlib import Path
import tempfile
import unittest

from ruamel.yaml import YAML
from plugins.dashboard_auth.basic import hash_password
from hermes_cli.dashboard_auth.base import InvalidCredentialsError


class RemovalRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory();self.addCleanup(self.directory.cleanup)
        self.profile=Path(self.directory.name)
        path=self.profile/'config.yaml'
        with path.open('w') as stream:YAML().dump({'dashboard':{'basic_auth':{
            'username':'synthetic-owner','password_hash':hash_password('synthetic-test-password')}}},stream)
        path.chmod(0o600)

    def operation(self):
        from optional.lifeos_release_manager.removal_recovery import authenticate
        return authenticate

    def test_actual_owner_password_returns_the_same_dashboard_identity(self):
        result=self.operation()(self.profile,'synthetic-owner','synthetic-test-password','dashboard:basic:synthetic-owner')
        self.assertEqual(result,'dashboard:basic:synthetic-owner')

    def test_wrong_password_or_other_installation_owner_cannot_authorize(self):
        with self.assertRaises(InvalidCredentialsError):
            self.operation()(self.profile,'synthetic-owner','synthetic-wrong-password','dashboard:basic:synthetic-owner')
        with self.assertRaises(PermissionError):
            self.operation()(self.profile,'synthetic-owner','synthetic-test-password','dashboard:basic:another-owner')
        with self.assertRaises(InvalidCredentialsError):
            self.operation()(self.profile,'another-owner','synthetic-test-password','dashboard:basic:synthetic-owner')

    def test_changed_or_public_configuration_refuses_before_authentication(self):
        (self.profile/'config.yaml').chmod(0o644)
        with self.assertRaises(ValueError):self.operation()(self.profile,'synthetic-owner','synthetic-test-password','dashboard:basic:synthetic-owner')
