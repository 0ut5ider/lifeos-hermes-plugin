# ABOUTME: Exercises bounded preparation selections and actual private file locking.
# ABOUTME: Checks duplicate preparation and interrupted worker reporting without downloading a release.
import fcntl
import json
import os
from pathlib import Path
import tempfile
import unittest

from optional.lifeos_release_manager import release_preparation
from optional.lifeos_release_manager.cli import status, write_state
from optional.lifeos_release_manager.release_operation import OperationBusy
from optional.lifeos_release_manager.release_programs import publish


class ReleasePreparationTests(unittest.TestCase):
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
