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


class DashboardLoginSourceTests(unittest.TestCase):
    """The dashboard reads its login from the profile .env, then its unit environment, then config.yaml."""

    def setUp(self):
        self.directory=tempfile.TemporaryDirectory();self.addCleanup(self.directory.cleanup)
        self.profile=Path(self.directory.name)/'.hermes'
        self.profile.mkdir(mode=0o700)
        self.config({})
        self.unit=([],[])

    def private(self,path,text):
        path.write_text(text);path.chmod(0o600)
        return path

    def config(self,basic):
        path=self.profile/'config.yaml'
        with path.open('w') as stream:YAML().dump({'dashboard':{'basic_auth':basic}},stream)
        path.chmod(0o600)

    def settings(self):
        from optional.lifeos_release_manager.removal_recovery import basic_settings
        return basic_settings(self.profile,unit=lambda:self.unit)

    def login(self,username,password):
        from optional.lifeos_release_manager.removal_recovery import authenticate
        from unittest import mock
        with mock.patch('optional.lifeos_release_manager.removal_recovery.dashboard_unit_environment',
                        return_value=self.unit):
            return authenticate(self.profile,username,password,'dashboard:basic:'+username)

    def test_unit_environment_file_supplies_the_login(self):
        env=self.private(self.profile.parent/'dashboard-auth.env',
            'HERMES_DASHBOARD_BASIC_AUTH_USERNAME=unit-owner\n'
            "HERMES_DASHBOARD_BASIC_AUTH_PASSWORD_HASH='"+hash_password('synthetic-unit-password')+"'\n")
        self.unit=([],[env])
        self.assertEqual(self.settings()['username'],'unit-owner')
        self.assertEqual(self.login('unit-owner','synthetic-unit-password'),'dashboard:basic:unit-owner')

    def test_inline_unit_environment_supplies_the_login(self):
        self.unit=(['HERMES_DASHBOARD_BASIC_AUTH_USERNAME=inline-owner',
                    'HERMES_DASHBOARD_BASIC_AUTH_PASSWORD_HASH='+hash_password('synthetic-inline-password')],[])
        self.assertEqual(self.login('inline-owner','synthetic-inline-password'),'dashboard:basic:inline-owner')

    def test_profile_env_wins_over_the_unit_and_the_unit_over_config(self):
        self.config({'username':'config-owner','password_hash':hash_password('synthetic-config-password')})
        env=self.private(self.profile.parent/'dashboard-auth.env','HERMES_DASHBOARD_BASIC_AUTH_USERNAME=unit-owner\n')
        self.unit=([],[env])
        self.assertEqual(self.settings()['username'],'unit-owner')
        self.private(self.profile/'.env','HERMES_DASHBOARD_BASIC_AUTH_USERNAME=profile-owner\n')
        self.assertEqual(self.settings()['username'],'profile-owner')
        # The password hash still comes from config.yaml, the only source that sets it.
        self.assertEqual(self.login('profile-owner','synthetic-config-password'),'dashboard:basic:profile-owner')

    def test_empty_values_do_not_shadow_a_later_source(self):
        self.config({'username':'config-owner','password_hash':hash_password('synthetic-config-password')})
        self.private(self.profile/'.env','HERMES_DASHBOARD_BASIC_AUTH_USERNAME=\n')
        self.assertEqual(self.settings()['username'],'config-owner')

    def test_plaintext_environment_password_is_hashed_like_the_dashboard(self):
        self.private(self.profile/'.env','HERMES_DASHBOARD_BASIC_AUTH_USERNAME=env-owner\n'
                     'HERMES_DASHBOARD_BASIC_AUTH_PASSWORD=synthetic-plain-password\n')
        self.config({'password_hash':hash_password('synthetic-other-password')})
        self.assertEqual(self.login('env-owner','synthetic-plain-password'),'dashboard:basic:env-owner')

    def test_shared_login_files_refuse(self):
        from optional.lifeos_release_manager.release_catalog import ReleaseRejected
        env=self.private(self.profile.parent/'dashboard-auth.env','HERMES_DASHBOARD_BASIC_AUTH_USERNAME=unit-owner\n')
        env.chmod(0o640)
        self.unit=([],[env])
        with self.assertRaises(ReleaseRejected):self.settings()
        self.unit=([],[])
        self.private(self.profile/'.env','HERMES_DASHBOARD_BASIC_AUTH_USERNAME=x\n').chmod(0o644)
        with self.assertRaises(ReleaseRejected):self.settings()

    def test_missing_login_refuses(self):
        from optional.lifeos_release_manager.release_catalog import ReleaseRejected
        with self.assertRaisesRegex(ReleaseRejected,'password-authenticated dashboard recovery owner'):self.settings()
