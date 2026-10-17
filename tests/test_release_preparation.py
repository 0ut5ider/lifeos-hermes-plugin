# ABOUTME: Exercises bounded preparation selections and actual private file locking.
# ABOUTME: Checks duplicate preparation and interrupted worker reporting without downloading a release.
import fcntl
import json
import os
from pathlib import Path
import inspect
import sys
import tempfile
import unittest
from unittest import mock

from optional.lifeos_release_manager import inplace_preparation, release_preparation
from optional.lifeos_release_manager.cli import status, write_state
from optional.lifeos_release_manager.release_operation import OperationBusy
from optional.lifeos_release_manager.release_programs import publish


def admitted_host():
    """Admit the test profile's host so that preparation reaches its download boundary.

    The compatibility check runs before the download, and the test interpreter's Hermes is not an admitted host.
    """
    return mock.patch.object(inplace_preparation, 'check', return_value={'state': 'compatible'})


class ReleasePreparationTests(unittest.TestCase):
    def test_synchronous_preparation_holds_the_same_lease_as_the_dashboard(self):
        from optional.lifeos_release_manager.cli import prepare
        with tempfile.TemporaryDirectory() as temp:
            profile = Path(temp)
            test = self
            lines, start = inspect.getsourcelines(release_preparation.queue)
            boundary = start + next(i for i, line in enumerate(lines) if 'process = subprocess.Popen(' in line)
            def trace(frame, event, argument):
                if frame.f_code is release_preparation.queue.__code__ and event == 'line' and frame.f_lineno == boundary:
                    raise AssertionError('Overlapping preparation reaches child launch')
                return trace
            class StopAtDownload:
                def download_integration(self, directory, version):
                    previous = sys.gettrace()
                    sys.settrace(trace)
                    try:
                        with test.assertRaises(OperationBusy):
                            release_preparation.queue(profile, {'intent': 'install'})
                    finally:
                        sys.settrace(previous)
                    test.assertEqual(len([p for p in directory.parent.parent.iterdir() if p.is_dir()]), 1)
                    raise ValueError('Synthetic download boundary')
            with admitted_host(), self.assertRaisesRegex(ValueError, 'Synthetic download boundary'):
                prepare(profile, catalog=StopAtDownload())

    def test_synchronous_preparation_refuses_a_held_lease_before_download(self):
        from optional.lifeos_release_manager.cli import prepare
        with tempfile.TemporaryDirectory() as temp:
            profile = Path(temp)
            state = profile / '.lifeos-releases'
            state.mkdir(mode=0o700)
            class NoDownload:
                def download_integration(self, directory, version):
                    raise AssertionError('A duplicate synchronous preparation reaches download')
            with (state / 'preparation.lock').open('wb') as lock:
                os.fchmod(lock.fileno(), 0o600)
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                with self.assertRaises(OperationBusy):
                    prepare(profile, catalog=NoDownload())
            self.assertEqual([p.name for p in state.iterdir()], ['preparation.lock'])

    def test_synchronous_preparation_refuses_pending_installation_or_recovery(self):
        from optional.lifeos_release_manager.cli import prepare
        for phase in ('queued-apply', 'applying', 'recovering', 'restoring', 'recovery_required'):
            with self.subTest(phase=phase), tempfile.TemporaryDirectory() as temp:
                profile = Path(temp)
                job = profile / '.lifeos-releases' / ('a' * 32)
                job.mkdir(parents=True, mode=0o700)
                job.parent.chmod(0o700)
                write_state(job, phase)
                class NoDownload:
                    def download_integration(self, directory, version):
                        raise AssertionError('Preparation reaches download during a pending operation')
                with self.assertRaises(OperationBusy):
                    prepare(profile, catalog=NoDownload())
                self.assertEqual([p.name for p in job.parent.iterdir() if p.is_dir()], [job.name])

    def test_synchronous_preparation_can_retry_after_an_expired_preparation(self):
        from optional.lifeos_release_manager.cli import prepare
        with tempfile.TemporaryDirectory() as temp:
            profile = Path(temp)
            job = profile / '.lifeos-releases' / ('a' * 32)
            job.mkdir(parents=True, mode=0o700)
            job.parent.chmod(0o700)
            write_state(job, 'preparing')
            publish(job / 'preparation-worker.json', json.dumps({'pid': os.getpid(), 'start_time': 'expired'}).encode())
            class StopAtDownload:
                def download_integration(self, directory, version):
                    raise ValueError('Synthetic retry reaches download')
            with admitted_host(), self.assertRaisesRegex(ValueError, 'Synthetic retry reaches download'):
                prepare(profile, catalog=StopAtDownload())
            self.assertEqual(len([p for p in job.parent.iterdir() if p.is_dir()]), 2)

    def test_live_synchronous_preparation_records_its_process_before_download(self):
        from optional.lifeos_release_manager.cli import prepare
        with tempfile.TemporaryDirectory() as temp:
            profile = Path(temp)
            class StopAtDownload:
                def download_integration(self, directory, version):
                    self.result = status(profile)['operations'][0]
                    raise ValueError('Synthetic download boundary')
            catalog = StopAtDownload()
            with admitted_host(), self.assertRaisesRegex(ValueError, 'Synthetic download boundary'):
                prepare(profile, catalog=catalog)
            self.assertEqual(catalog.result['state'], 'preparing')
            self.assertEqual(status(profile)['operations'][0]['state'], 'preparation_failed')
    def test_invalid_selections_do_not_create_profile_files(self):
        with tempfile.TemporaryDirectory() as temp:
            profile = Path(temp)
            for value in (None, [], {'intent': []}, {'intent': 'update', 'version': True},
                          {'intent': 'update', 'version': 'main'}, {'intent': 'shell'},
                          {'intent': 'install', 'name': '\n'}, {'intent': 'install', 'assistant': 'x' * 101},
                          {'intent': 'plugin', 'profile': '/different'}):
                with self.subTest(value=value), self.assertRaises(ValueError):
                    release_preparation.queue(profile, value)
            self.assertEqual(list(profile.iterdir()), [])

    def test_running_preparation_refuses_duplicate_before_creating_an_operation(self):
        with tempfile.TemporaryDirectory() as temp:
            profile = Path(temp)
            state = profile / '.lifeos-releases'
            state.mkdir(mode=0o700)
            with (state / 'preparation.lock').open('wb') as lock:
                os.fchmod(lock.fileno(), 0o600)
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                with self.assertRaises(OperationBusy):
                    release_preparation.queue(profile, {'intent': 'install'})
                self.assertEqual([path.name for path in state.iterdir()], ['preparation.lock'])

    def test_preparation_lock_rejects_symlinks(self):
        with tempfile.TemporaryDirectory() as temp:
            profile = Path(temp)
            state = profile / '.lifeos-releases'
            state.mkdir(mode=0o700)
            outside = profile / 'outside'
            outside.write_text('Preserve this file')
            (state / 'preparation.lock').symlink_to(outside)
            with self.assertRaises(OSError):
                release_preparation.queue(profile, {'intent': 'install'})
            self.assertEqual(outside.read_text(), 'Preserve this file')

    def test_required_recovery_refuses_preparation_before_creating_another_operation(self):
        with tempfile.TemporaryDirectory() as temp:
            profile = Path(temp)
            job = profile / '.lifeos-releases' / ('a' * 32)
            job.mkdir(parents=True, mode=0o700)
            job.parent.chmod(0o700)
            write_state(job, 'recovery_required')
            with self.assertRaises(OperationBusy):
                release_preparation.queue(profile, {'intent': 'update'})
            self.assertEqual([p.name for p in job.parent.iterdir() if p.is_dir()], [job.name])

    def test_status_identifies_an_interrupted_preparation_without_changing_programs(self):
        with tempfile.TemporaryDirectory() as temp:
            profile = Path(temp)
            job = profile / '.lifeos-releases' / ('a' * 32)
            job.mkdir(parents=True, mode=0o700)
            write_state(job, 'preparing')
            publish(job / 'preparation-worker.json', json.dumps({'pid': os.getpid(), 'start_time': 'expired'}).encode())
            result = status(profile, job.name)
            self.assertEqual(result['state'], 'preparation_interrupted')
            self.assertEqual(json.loads((job / 'status.json').read_text())['state'], 'preparing')
            self.assertFalse((job / 'request.json').exists())

    def test_status_identifies_interruption_before_worker_publication(self):
        with tempfile.TemporaryDirectory() as temp:
            profile = Path(temp)
            job = profile / '.lifeos-releases' / ('a' * 32)
            job.mkdir(parents=True, mode=0o700)
            job.parent.chmod(0o700)
            write_state(job, 'preparing')
            self.assertEqual(status(profile, job.name)['state'], 'preparation_interrupted')
            self.assertEqual(json.loads((job / 'status.json').read_text())['state'], 'preparing')

    def test_empty_preparation_directory_does_not_hide_other_operations(self):
        with tempfile.TemporaryDirectory() as temp:
            profile = Path(temp)
            job = profile / '.lifeos-releases' / ('a' * 32)
            job.mkdir(parents=True, mode=0o700)
            job.parent.chmod(0o700)
            other = job.with_name('b' * 32)
            other.mkdir(mode=0o700)
            write_state(other, 'preparation_failed')
            self.assertEqual([value['state'] for value in status(profile)['operations']],
                             ['preparation_interrupted', 'preparation_failed'])
            from optional.lifeos_release_manager.release_operation import process_stamp
            publish(job / 'preparation-worker.json', json.dumps({'pid': os.getpid(),
                'start_time': process_stamp(os.getpid())}).encode())
            self.assertEqual(status(profile, job.name)['state'], 'preparing')

    def test_held_launch_lease_preserves_preparing_without_worker_identity(self):
        with tempfile.TemporaryDirectory() as temp:
            profile = Path(temp)
            job = profile / '.lifeos-releases' / ('a' * 32)
            job.mkdir(parents=True, mode=0o700)
            job.parent.chmod(0o700)
            write_state(job, 'preparing')
            with (job.parent / 'preparation.lock').open('wb') as lock:
                os.fchmod(lock.fileno(), 0o600)
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                self.assertEqual(status(profile, job.name)['state'], 'preparing')
                publish(job / 'preparation-worker.json', json.dumps({'pid': os.getpid(), 'start_time': 'expired'}).encode())
                self.assertEqual(status(profile, job.name)['state'], 'preparing')
            self.assertEqual(status(profile, job.name)['state'], 'preparation_interrupted')

    def test_status_identifies_interruption_after_the_request_is_published(self):
        with tempfile.TemporaryDirectory() as temp:
            profile = Path(temp)
            job = profile / '.lifeos-releases' / ('a' * 32)
            job.mkdir(parents=True, mode=0o700)
            write_state(job, 'preparing')
            publish(job / 'preparation-worker.json', json.dumps({'pid': os.getpid(), 'start_time': 'expired'}).encode())
            publish(job / 'request.json', json.dumps({'profile': str(profile), 'identifier': job.name,
                'version': '0.4.2-rc.1', 'commit': 'b' * 40}).encode())
            self.assertEqual(status(profile, job.name)['state'], 'preparation_interrupted')

    def test_selected_software_removal_blocks_synchronous_preparation_before_download(self):
        from optional.lifeos_release_manager.cli import prepare
        with tempfile.TemporaryDirectory() as directory:
            profile=Path(directory)
            publish(profile/'.lifeos-removal.json',b'{"format":1,"workflow":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","signature":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"}')
            class NoDownload:
                def download_integration(self,directory,version):raise AssertionError('Removal overlap reaches a release download')
            with self.assertRaisesRegex(ValueError,'removal'):
                prepare(profile,catalog=NoDownload())
            self.assertFalse((profile/'.lifeos-releases').exists())
