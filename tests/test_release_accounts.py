# ABOUTME: Verifies the owner account boundary separately from native service HOME.
# ABOUTME: Uses actual private directories and child processes to check profile and launcher scope.
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from optional.lifeos_release_manager.release_catalog import ReleaseRejected


class ReleaseAccountTests(unittest.TestCase):
    def test_standard_profile_keeps_account_home_under_native_service_home(self):
        from optional.lifeos_release_manager.release_accounts import account_home
        with tempfile.TemporaryDirectory() as temporary:
            owner = Path(temporary)
            profile = owner / '.hermes'
            profile.mkdir(mode=0o700)
            native_home = owner / 'native/home'
            native_home.mkdir(parents=True, mode=0o700)
            code = ('import json,sys;from pathlib import Path;'
                'from optional.lifeos_release_manager.release_accounts import account_home;'
                'print(json.dumps({"account":str(account_home(Path(sys.argv[1]))),"service":str(Path.home())}))')
            result = subprocess.run([sys.executable, '-B', '-c', code, str(profile)],
                env=dict(os.environ, HOME=str(native_home)), capture_output=True, text=True, check=True)
            self.assertEqual(result.stderr, '')
            self.assertEqual(json.loads(result.stdout), {'account': str(owner), 'service': str(native_home)})
            self.assertEqual(account_home(profile), owner)

    def test_named_profile_selects_its_account_not_the_native_home(self):
        from optional.lifeos_release_manager.release_accounts import account_home
        with tempfile.TemporaryDirectory() as temporary:
            owner = Path(temporary)
            profile = owner / '.hermes/profiles/work'
            profile.mkdir(parents=True, mode=0o700)
            self.assertEqual(account_home(profile), owner)

    def test_custom_profile_preserves_explicit_home(self):
        from optional.lifeos_release_manager.release_accounts import account_home
        with tempfile.TemporaryDirectory() as temporary:
            profile = Path(temporary) / 'custom-profile'
            profile.mkdir(mode=0o700)
            self.assertEqual(account_home(profile), Path.home())

    def test_account_alias_and_shared_write_permissions_refuse(self):
        from optional.lifeos_release_manager.release_accounts import account_home
        with tempfile.TemporaryDirectory() as temporary:
            owner = Path(temporary) / 'owner'
            profile = owner / '.hermes'
            profile.mkdir(parents=True, mode=0o700)
            alias = Path(temporary) / 'alias'
            alias.symlink_to(owner, target_is_directory=True)
            with self.assertRaises(ReleaseRejected):
                account_home(alias / '.hermes')
            owner.chmod(0o770)
            with self.assertRaises(ReleaseRejected):
                account_home(profile)
            owner.chmod(0o700)

    def test_untrusted_account_refuses_before_preparation_creates_files(self):
        from optional.lifeos_release_manager import release_preparation
        with tempfile.TemporaryDirectory() as temporary:
            owner = Path(temporary) / 'owner'
            owner.mkdir(mode=0o700)
            profile = owner / '.hermes'
            profile.mkdir(mode=0o700)
            owner.chmod(0o770)
            try:
                with self.assertRaises(ReleaseRejected):
                    release_preparation.queue(profile, {'intent': 'update', 'version': '0.4.3'})
                self.assertEqual(list(profile.iterdir()), [])
            finally:
                owner.chmod(0o700)


if __name__ == '__main__':
    unittest.main()
