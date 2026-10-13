# ABOUTME: Exercises release review seals and action admission with private operation files.
# ABOUTME: Checks process locking, artifact changes, and recovery eligibility before live publication.
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest

from optional.lifeos_release_manager.cli import read_private, write_state
from optional.lifeos_release_manager.release_operation import (
    action_state, operation_lock, seal_plan, validate_admission, write_admission,
)
from optional.lifeos_release_manager.release_programs import publish


class ReleaseOperationTests(unittest.TestCase):
    def test_worker_failure_keeps_the_lock_until_state_publication(self):
        import inspect
        import select
        import sys
        from optional.lifeos_release_manager import release_worker as worker
        from optional.lifeos_release_manager.release_operation import OperationBusy
        with tempfile.TemporaryDirectory() as temp:
            profile, job, request = self.recovery_fixture(Path(temp))
            write_admission(job, request, 'recover')
            write_state(job, 'queued-recover')
            target_function = worker.execute
            lines, start = inspect.getsourcelines(target_function)
            target = start + next(index for index, line in enumerate(lines)
                                  if line.strip() == 'record_failure(job, error)')
            reader, writer = os.pipe()
            resume_reader, resume_writer = os.pipe()
            child = os.fork()
            if child == 0:
                os.close(reader)
                os.close(resume_writer)
                def trace(frame, event, arg):
                    if frame.f_code is target_function.__code__ and event == 'line' and frame.f_lineno == target:
                        sys.settrace(None)
                        os.write(writer, b'1')
                        os.read(resume_reader, 1)
                    return trace
                sys.argv = ['release_worker.py', str(job), '--action', 'recover']
                sys.settrace(trace)
                os._exit(worker.main())
            os.close(writer)
            os.close(resume_reader)
            try:
                self.assertTrue(select.select([reader], [], [], 20)[0], 'The worker does not reach failure publication')
                self.assertEqual(os.read(reader, 1), b'1')
                with self.assertRaises(OperationBusy):
                    worker.admit_operation(job, read_private(job / 'request.json'), 'recover')
            finally:
                os.write(resume_writer, b'1')
                _, result = os.waitpid(child, 0)
                os.close(reader)
                os.close(resume_writer)
            self.assertEqual(os.waitstatus_to_exitcode(result), 1)
            self.assertEqual(read_private(job / 'status.json')['state'], 'recovery_required')
            self.assertTrue((job / 'worker-failure.json').is_file())
            worker.admit_operation(job, read_private(job / 'request.json'), 'recover')
            validate_admission(job, read_private(job / 'request.json'), 'recover')

    def test_restore_admission_checks_the_recorded_profile(self):
        from optional.lifeos_release_manager.release_programs import ProgramTransaction
        from optional.lifeos_release_manager.release_worker import admit_operation
        with tempfile.TemporaryDirectory() as temp:
            profile, job, request = self.recovery_fixture(Path(temp))
            programs = ProgramTransaction(job / 'program-snapshot')
            programs.prepare(directories={}, files={})
            programs.apply()
            seal_plan(job, request, {'fresh': False, 'native_mount_required': False,
                'services': None, 'program_entries_sha256': programs.entries_digest()})
            write_state(job, 'applied')
            admit_operation(job, request, 'restore')
            self.assertEqual(read_private(job / 'status.json')['state'], 'queued-restore')
            validate_admission(job, read_private(job / 'request.json'), 'restore')
            from optional.lifeos_release_manager.release_worker import execute
            with self.assertRaisesRegex(ValueError, 'selected native installation'):
                execute(job, 'restore')
            self.assertEqual(read_private(job / 'status.json')['state'], 'applied')
            admit_operation(job, read_private(job / 'request.json'), 'restore')
            validate_admission(job, read_private(job / 'request.json'), 'restore')

    def recovery_fixture(self, root):
        profile = root / '.hermes'
        profile.mkdir(mode=0o700)
        folder = profile / '.lifeos-releases'
        folder.mkdir(mode=0o700)
        job, request = self.fixture(folder)
        request.update(profile=str(profile), installed=str(root / '.claude'), commit='b' * 40,
                       runtime={'source': str(root / 'native-source')})
        shutil.copytree(Path(__file__).resolve().parents[1] / 'lifeos_hook_bridge',
            profile / 'plugins/lifeos-hook-bridge', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        seal_plan(job, request, {'fresh': False, 'native_mount_required': False, 'services': None})
        return profile, job, request

    def test_coordinator_exit_before_launch_receipt_permits_recovery(self):
        from optional.lifeos_release_manager.cli import status
        from optional.lifeos_release_manager.release_worker import _admit_operation
        with tempfile.TemporaryDirectory() as temp:
            profile, job, request = self.recovery_fixture(Path(temp))
            child = os.fork()
            if child == 0:
                with operation_lock(job, name='launch.lock'), operation_lock(job):
                    write_admission(job, request, 'apply')
                    write_state(job, 'queued-apply')
                    os._exit(73)
            _, result = os.waitpid(child, 0)
            self.assertEqual(os.waitstatus_to_exitcode(result), 73)
            self.assertTrue(status(profile, job.name)['recover_available'])
            with operation_lock(job, name='launch.lock'), operation_lock(job):
                _admit_operation(job, request, 'recover')
            validate_admission(job, read_private(job / 'request.json'), 'recover')

    def test_live_coordinator_keeps_unrecorded_launch_unavailable(self):
        from optional.lifeos_release_manager.cli import status
        with tempfile.TemporaryDirectory() as temp:
            profile, job, request = self.recovery_fixture(Path(temp))
            write_admission(job, request, 'apply')
            write_state(job, 'queued-apply')
            with operation_lock(job, name='launch.lock'):
                self.assertFalse(status(profile, job.name)['recover_available'])

    def test_late_apply_worker_preserves_the_recovery_grant(self):
        from optional.lifeos_release_manager.release_worker import execute
        with tempfile.TemporaryDirectory() as temp:
            profile, job, request = self.recovery_fixture(Path(temp))
            directory = profile / '.lifeos-memory-admin'
            directory.mkdir(mode=0o700)
            grant = directory / ('b' * 32 + '.json')
            publish(grant, b'Synthetic recovery grant')
            request['memory_authorization'] = str(grant)
            publish(job / 'request.json', json.dumps(request).encode())
            write_admission(job, request, 'recover')
            write_state(job, 'queued-recover')
            with self.assertRaisesRegex(ValueError, 'admitted request'):
                execute(job, 'apply')
            self.assertTrue(grant.exists(), 'A stale worker revokes the successor grant')
            self.assertEqual(grant.read_bytes(), b'Synthetic recovery grant')
            validate_admission(job, read_private(job / 'request.json'), 'recover')

    def test_admitted_worker_revokes_its_grant_on_artifact_refusal(self):
        from optional.lifeos_release_manager.release_worker import execute
        with tempfile.TemporaryDirectory() as temp:
            profile, job, request = self.recovery_fixture(Path(temp))
            directory = profile / '.lifeos-memory-admin'
            directory.mkdir(mode=0o700)
            grant = directory / ('b' * 32 + '.json')
            publish(grant, b'Synthetic admitted grant')
            request['memory_authorization'] = str(grant)
            publish(job / 'request.json', json.dumps(request).encode())
            write_admission(job, request, 'apply')
            write_state(job, 'queued-apply')
            with self.assertRaises(KeyError):
                execute(job, 'apply')
            self.assertFalse(grant.exists())

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

    @unittest.skipUnless(os.environ.get('LIFEOS_QUALIFICATION_BUILD'), 'A sealed current package is required')
    def test_fresh_recovery_keeps_one_lease_namespace_after_bridge_publication(self):
        import shutil
        from optional.lifeos_release_manager.release_worker import recovery_bridge
        from optional.lifeos_release_manager.release_stage import load_bridge
        from optional.lifeos_release_manager.release_services import fresh_services
        from optional.lifeos_release_manager.release_catalog import extract_package
        build = json.loads(Path(os.environ['LIFEOS_QUALIFICATION_BUILD']).read_bytes())
        with tempfile.TemporaryDirectory(dir=Path(build['package']).parent) as temp:
            root = Path(temp)
            profile = root / '.hermes'
            job = profile / '.lifeos-releases' / ('a' * 32)
            job.mkdir(parents=True, mode=0o700)
            extract_package(build['archive'], job / 'package')
            active = profile / 'plugins/lifeos-hook-bridge'
            shutil.copytree(job / 'package/lifeos_hook_bridge', active, copy_function=os.link)
            certificate = {**build, 'format': 1, 'status': 'QUALIFIED', 'program_commit': build['head'], 'test_fixture_only': True}
            request = {'identifier': job.name, 'profile': str(profile), 'certificate': certificate}
            publish(job / 'request.json', json.dumps(request).encode())
            write_state(job, 'ready')
            seal_plan(job, request, {'fresh': True})
            candidate = load_bridge(job / 'package/lifeos_hook_bridge')
            selected = recovery_bridge(job, profile)
            with selected.memory_module('installation_lock').installation_lock(profile) as lease:
                controller = fresh_services(candidate, profile, root / '.claude', installation_lease=lease)
                self.assertEqual(controller.status()['state'], 'none')
            self.assertIs(selected.memory_module('installation_lock'), candidate.memory_module('installation_lock'))

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

    def test_candidate_seals_preparation_without_early_apply_admission(self):
        with tempfile.TemporaryDirectory() as temp:
            job, request = self.fixture(Path(temp))
            write_state(job, 'preparing')
            seal_plan(job, request, {'fresh': True}, preparing=True)
            self.assertEqual(read_private(job / 'status.json')['state'], 'preparing')
            with self.assertRaises(ValueError):
                action_state(job, 'apply')
            write_state(job, 'ready')
            write_admission(job, read_private(job / 'request.json'), 'apply')

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
