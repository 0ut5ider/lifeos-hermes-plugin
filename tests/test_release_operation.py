# ABOUTME: Exercises release review seals and action admission with private operation files.
# ABOUTME: Checks process locking, artifact changes, and recovery eligibility before live publication.
import json
import os
from pathlib import Path
import tempfile
import unittest

from optional.lifeos_release_manager.cli import read_private, write_state
from optional.lifeos_release_manager.release_operation import (
    action_state, operation_lock, seal_plan, validate_admission, write_admission,
)
from optional.lifeos_release_manager.release_programs import publish


class ReleaseOperationTests(unittest.TestCase):
    def test_grant_cleanup_is_bounded_to_the_recorded_private_profile(self):
        from optional.lifeos_release_manager.release_worker import revoke_recorded_authorization
        with tempfile.TemporaryDirectory() as temp:
            profile = Path(temp)
            folder = profile / '.lifeos-releases'
            folder.mkdir(mode=0o700)
            job, request = self.fixture(folder)
            directory = profile / '.lifeos-memory-admin'
            directory.mkdir(mode=0o700)
            grant = directory / ('b' * 32 + '.json')
            grant.write_text('Synthetic private grant')
            request.update(profile=str(profile), memory_authorization=str(grant))
            publish(job / 'request.json', json.dumps(request).encode())
            revoke_recorded_authorization(job)
            self.assertFalse(grant.exists())
            outside = profile / 'keep.txt'
            outside.write_text('Synthetic preserve')
            request['memory_authorization'] = str(outside)
            publish(job / 'request.json', json.dumps(request).encode())
            with self.assertRaisesRegex(ValueError, 'authorization path'):
                revoke_recorded_authorization(job)
            self.assertEqual(outside.read_text(), 'Synthetic preserve')

    def test_worker_receipt_tracks_actual_process_lifetime(self):
        import signal
        from optional.lifeos_release_manager.release_operation import record_worker, worker_running
        with tempfile.TemporaryDirectory() as temp:
            job, request = self.fixture(Path(temp))
            reader, writer = os.pipe()
            child = os.fork()
            if child == 0:
                os.close(writer)
                os.read(reader, 1)
                os._exit(0)
            os.close(reader)
            try:
                record_worker(job, child)
                self.assertTrue(worker_running(job))
                os.kill(child, signal.SIGKILL)
                os.waitpid(child, 0)
                self.assertFalse(worker_running(job))
            finally:
                os.close(writer)

    @unittest.skipUnless(os.environ.get('LIFEOS_MANAGED_FRESH_OPERATION'), 'A prepared fresh operation is required')
    def test_prepared_fresh_operation_loads_candidate_without_a_prior_bridge(self):
        from optional.lifeos_release_manager.release_worker import recovery_bridge
        job = Path(os.environ['LIFEOS_MANAGED_FRESH_OPERATION'])
        request = read_private(job / 'request.json')
        source = recovery_bridge(job, Path(request['profile']))
        self.assertEqual(Path(source.__file__).parent, job / 'package/lifeos_hook_bridge')

    def fixture(self, root):
        job = root / ('a' * 32)
        job.mkdir(mode=0o700)
        request = {'identifier': job.name, 'profile': str(root), 'version': '0.4.0'}
        publish(job / 'request.json', json.dumps(request).encode())
        write_state(job, 'ready')
        return job, request

    def test_review_seals_exact_plan_into_owner_grant_request(self):
        with tempfile.TemporaryDirectory() as temp:
            job, request = self.fixture(Path(temp))
            seal_plan(job, request, {'fresh': False, 'services': None})
            self.assertEqual(read_private(job / 'request.json'), request)
            write_admission(job, request, 'apply')
            write_state(job, 'queued-apply')
            validate_admission(job, request, 'apply')
            publish(job / 'plan.json', b'{"fresh":true,"services":null}')
            with self.assertRaisesRegex(ValueError, 'reviewed plan'):
                validate_admission(job, request, 'apply')

    def test_request_changes_and_action_substitution_refuse(self):
        with tempfile.TemporaryDirectory() as temp:
            job, request = self.fixture(Path(temp))
            seal_plan(job, request, {'fresh': False})
            write_admission(job, request, 'apply')
            write_state(job, 'queued-apply')
            with self.assertRaises(ValueError):
                validate_admission(job, {**request, 'version': '0.5.0'}, 'apply')
            with self.assertRaises(ValueError):
                validate_admission(job, request, 'restore')

    def test_review_cannot_change_a_queued_operation(self):
        with tempfile.TemporaryDirectory() as temp:
            job, request = self.fixture(Path(temp))
            seal_plan(job, request, {'fresh': False})
            before = (job / 'plan.json').read_bytes()
            write_state(job, 'queued-apply')
            with self.assertRaises(ValueError):
                seal_plan(job, request, {'fresh': True})
            self.assertEqual((job / 'plan.json').read_bytes(), before)

    def test_recovery_and_rollback_have_distinct_admission_states(self):
        for state, allowed in [('ready', {'apply'}), ('applied', {'restore'}),
                               ('applying', {'recover'}), ('recovery_required', {'recover'}),
                               ('restoring', {'recover'}), ('rolled_back', set())]:
            with self.subTest(state=state), tempfile.TemporaryDirectory() as temp:
                job, request = self.fixture(Path(temp))
                write_state(job, state)
                for action in ('apply', 'restore', 'recover'):
                    if action in allowed:
                        action_state(job, action)
                    else:
                        with self.assertRaises(ValueError):
                            action_state(job, action)

    def test_process_exit_releases_operation_lock(self):
        with tempfile.TemporaryDirectory() as temp:
            job, request = self.fixture(Path(temp))
            with operation_lock(job):
                child = os.fork()
                if child == 0:
                    try:
                        with operation_lock(job):
                            os._exit(91)
                    except RuntimeError:
                        os._exit(0)
                _, result = os.waitpid(child, 0)
                self.assertEqual(os.waitstatus_to_exitcode(result), 0)
            with operation_lock(job):
                pass

    def test_mount_recovery_refuses_another_jobs_journal(self):
        from types import SimpleNamespace
        from optional.lifeos_release_manager.release_worker import _restore_mount
        with tempfile.TemporaryDirectory() as temp:
            job, request = self.fixture(Path(temp))
            journal = job / 'native-mount.json'
            publish(journal, b'{"binding":{"job":"another-job"}}')
            publish(job / 'mount-intent.json', b'{"prior_journal_sha256":null}')
            with self.assertRaisesRegex(ValueError, 'another release operation'):
                _restore_mount(job, request, SimpleNamespace(journal=journal))
