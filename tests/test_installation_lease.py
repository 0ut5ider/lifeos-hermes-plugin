# ABOUTME: Verifies continuous installation exclusion through explicitly borrowed owner leases.
# ABOUTME: Uses actual competing processes, threads, and profile helpers instead of simulated lock results.
import json
import os
from pathlib import Path
import select
import signal
import tempfile
from concurrent.futures import ThreadPoolExecutor
import unittest

from lifeos_hook_bridge.installation_lock import installation_lock
import test_installation_lock as lock_fixture


class InstallationLeaseTests(unittest.TestCase):
    def competitor_is_blocked(self, profile):
        fixture = lock_fixture.InstallationLockTests()
        self.addCleanup(fixture.doCleanups)
        child = fixture.child(profile, wait=False)
        output, error = child.communicate(timeout=5)
        self.assertNotEqual(child.returncode, 0)
        self.assertEqual(output, '')
        self.assertIn('Another installation operation is running', error)

    def test_borrowed_helpers_keep_the_original_process_lock_until_outer_exit(self):
        with tempfile.TemporaryDirectory() as directory:
            profile = Path(directory)
            with installation_lock(profile) as lease:
                with installation_lock(profile, lease=lease):
                    self.competitor_is_blocked(profile)
                self.competitor_is_blocked(profile)
            with installation_lock(profile):
                pass

    def test_expired_and_other_profile_leases_refuse_without_reacquiring(self):
        with tempfile.TemporaryDirectory() as directory:
            profile = Path(directory)
            other = profile / 'other'
            other.mkdir(mode=0o700)
            with installation_lock(profile) as lease:
                with self.assertRaisesRegex(RuntimeError, 'profile'):
                    with installation_lock(other, lease=lease):
                        self.fail('The lease borrows another profile')
                self.competitor_is_blocked(profile)
            with self.assertRaisesRegex(RuntimeError, 'expired'):
                with installation_lock(profile, lease=lease):
                    self.fail('The closed lease reacquires a lock')

    def test_another_thread_cannot_borrow_the_coordinator_lease(self):
        with tempfile.TemporaryDirectory() as directory:
            profile = Path(directory)
            with installation_lock(profile) as lease, ThreadPoolExecutor(max_workers=1) as executor:
                def borrow():
                    with installation_lock(profile, lease=lease):
                        return 'unexpected'
                with self.assertRaisesRegex(RuntimeError, 'owner'):
                    executor.submit(borrow).result(timeout=5)
                self.competitor_is_blocked(profile)

    def test_replaced_lock_file_invalidates_the_borrowed_lease(self):
        with tempfile.TemporaryDirectory() as directory:
            profile = Path(directory)
            with installation_lock(profile) as lease:
                lock = profile / '.lifeos-installation/lock'
                lock.rename(lock.with_name('original-lock'))
                lock.write_text('')
                lock.chmod(0o600)
                with self.assertRaisesRegex(RuntimeError, 'identity'):
                    with installation_lock(profile, lease=lease):
                        self.fail('The lease borrows a different lock inode')

    def test_forked_process_cannot_borrow_the_parent_lease(self):
        with tempfile.TemporaryDirectory() as directory:
            profile = Path(directory)
            with installation_lock(profile) as lease:
                reader, writer = os.pipe()
                child = os.fork()
                if child == 0:
                    os.close(reader)
                    try:
                        with installation_lock(profile, lease=lease):
                            result = {'type': 'unexpected', 'message': 'The child borrows the parent lease'}
                    except BaseException as error:
                        result = {'type': type(error).__name__, 'message': str(error)}
                    os.write(writer, json.dumps(result).encode())
                    os.close(writer)
                    os._exit(0)
                os.close(writer)
                try:
                    if not select.select([reader], [], [], 5)[0]:
                        os.kill(child, signal.SIGKILL)
                        os.waitpid(child, 0)
                        self.fail('The forked lease borrower does not report its refusal')
                    result = json.loads(os.read(reader, 16384))
                    _, status = os.waitpid(child, 0)
                finally:
                    os.close(reader)
                self.assertEqual(status, 0)
                self.assertEqual(result['type'], 'RuntimeError')
                self.assertIn('owner', result['message'])
                self.competitor_is_blocked(profile)

    def test_missing_explicit_lease_and_forged_values_do_not_bypass_exclusion(self):
        with tempfile.TemporaryDirectory() as directory:
            profile = Path(directory)
            with installation_lock(profile) as lease:
                with self.assertRaisesRegex(RuntimeError, 'Another installation'):
                    with installation_lock(profile):
                        self.fail('The same thread implicitly borrows a held lease')
                for value in ({}, [], False, 0, 'synthetic lease'):
                    with self.subTest(value=value), self.assertRaisesRegex(RuntimeError, 'issued'):
                        with installation_lock(profile, lease=value):
                            self.fail('The caller supplies a forged lease value')
                with installation_lock(profile, lease=lease):
                    self.competitor_is_blocked(profile)

    def test_permission_changes_invalidate_the_lease_before_borrowing(self):
        with tempfile.TemporaryDirectory() as directory:
            profile = Path(directory)
            with installation_lock(profile) as lease:
                lock = profile / '.lifeos-installation/lock'
                lock.chmod(0o644)
                with self.assertRaisesRegex(RuntimeError, 'permissions'):
                    with installation_lock(profile, lease=lease):
                        self.fail('The lease borrows an exposed lock file')
                lock.chmod(0o600)
                self.competitor_is_blocked(profile)


class ProfileLeaseTests(unittest.TestCase):
    def test_one_lease_covers_real_service_drain_backup_ownership_and_restart(self):
        from lifeos_hook_bridge.memory_ownership import OwnershipTransaction
        from lifeos_hook_bridge.profile_backup import create
        from lifeos_hook_bridge.profile_services import ProfileServices
        import test_profile_backup as backup_fixture
        import test_profile_services as service_fixture
        from test_memory_ownership import install_connector
        backup = backup_fixture.ProfileBackupTests()
        backup.setUp()
        self.addCleanup(backup.doCleanups)
        profile, configuration = backup.profile, backup.configuration
        configuration.update(lambda value: value.update(ownership_enabled=False,
            accounts={**value['accounts'], 'dashboard:owner': 'owner'}))
        install_connector(configuration)
        services = service_fixture.ProfileServicesTests()
        services.fixture_home = backup.fixture.fixture.home
        services.fixture_profile = profile
        services.setUp()
        self.addCleanup(services.doCleanups)
        check = InstallationLeaseTests()
        self.addCleanup(check.doCleanups)
        with installation_lock(profile) as lease:
            barrier = ProfileServices(profile, backup.fixture.fixture.root, units=services.units, installation_lease=lease)
            barrier.drain()
            check.competitor_is_blocked(profile)
            snapshot = create(configuration, backup.destination, account='dashboard:owner', installation_lease=lease)
            barrier.verify_stopped()
            check.competitor_is_blocked(profile)
            ownership = OwnershipTransaction(configuration, installation_lease=lease)
            plan = ownership.preview(Path(snapshot['snapshot']), snapshot['signature'], account='dashboard:owner')
            ownership.apply(Path(snapshot['snapshot']), snapshot['signature'], plan['signature'], account='dashboard:owner')
            check.competitor_is_blocked(profile)
            ownership.rollback(account='dashboard:owner')
            self.assertFalse(configuration.load()['ownership_enabled'])
            barrier.resume()
            check.competitor_is_blocked(profile)
        with installation_lock(profile):
            pass
        destination = os.environ.get('LIFEOS_LEASE_EVIDENCE_DIR')
        if destination:
            path = Path(destination)
            path.mkdir(parents=True, exist_ok=True)
            (path / 'combined-profile-lease.json').write_text(json.dumps({'snapshot': snapshot, 'plan': plan,
                'ownership': json.loads(ownership.journal.read_text()), 'services': json.loads(barrier.journal.read_text())}, indent=2) + '\n')


if __name__ == '__main__':
    unittest.main()
