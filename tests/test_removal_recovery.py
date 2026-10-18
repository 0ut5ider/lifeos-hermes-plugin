# ABOUTME: Checks standalone recovery authentication against the actual Hermes basic provider.
# ABOUTME: Uses the login recorded at removal preparation; refuses invalid credentials and another owner.
import unittest

from plugins.dashboard_auth.basic import hash_password
from hermes_cli.dashboard_auth.base import InvalidCredentialsError


class RemovalRecoveryTests(unittest.TestCase):
    """Standalone recovery checks the password against the login that removal preparation recorded."""

    def setUp(self):
        self.login={'username':'synthetic-owner','password_hash':hash_password('synthetic-test-password')}

    def authenticate(self,username,password,owner='dashboard:basic:synthetic-owner',login=None):
        from optional.lifeos_release_manager.removal_recovery import authenticate
        return authenticate(login or self.login,username,password,owner)

    def test_actual_owner_password_returns_the_same_dashboard_identity(self):
        self.assertEqual(self.authenticate('synthetic-owner','synthetic-test-password'),'dashboard:basic:synthetic-owner')

    def test_wrong_password_or_other_installation_owner_cannot_authorize(self):
        with self.assertRaises(InvalidCredentialsError):
            self.authenticate('synthetic-owner','synthetic-wrong-password')
        with self.assertRaises(PermissionError):
            self.authenticate('synthetic-owner','synthetic-test-password',owner='dashboard:basic:another-owner')
        with self.assertRaises(InvalidCredentialsError):
            self.authenticate('another-owner','synthetic-test-password')

    def test_recorded_login_must_be_the_dashboard_password_owner(self):
        from optional.lifeos_release_manager.removal_recovery import recovery_login
        from optional.lifeos_release_manager.release_catalog import ReleaseRejected
        self.assertEqual(recovery_login(self.login,'dashboard:basic:synthetic-owner'),self.login)
        for value,owner in ((self.login,'dashboard:basic:another-owner'),(self.login,'dashboard:oauth:synthetic-owner'),
                            (None,'dashboard:basic:synthetic-owner'),({**self.login,'extra':1},'dashboard:basic:synthetic-owner'),
                            ({**self.login,'password_hash':'scrypt\\$16384\\$8\\$1\\$a\\$b'},'dashboard:basic:synthetic-owner'),
                            ({**self.login,'password_hash':'plain-text'},'dashboard:basic:synthetic-owner'),
                            ({**self.login,'username':''},'dashboard:basic:')):
            with self.subTest(value=value,owner=owner),self.assertRaisesRegex(ReleaseRejected,'password-authenticated dashboard'):
                recovery_login(value,owner)
