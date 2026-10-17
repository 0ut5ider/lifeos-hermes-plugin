# ABOUTME: Exercises the installation command through its real parser and private profile state.
# ABOUTME: Verifies that status and invalid requests cannot replace the active integration.
import argparse
from contextlib import redirect_stdout
import io
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
import tempfile
import unittest

from optional.lifeos_release_manager import register
from optional.lifeos_release_manager.cli import configure, run, status, write_state


class ReleaseManagerCommandTests(unittest.TestCase):
    def test_changed_retained_worker_refuses_before_admission_or_launch(self):
        from test_release_stage import ReleaseStageTests
        from optional.lifeos_release_manager.cli import launch
        from optional.lifeos_release_manager.release_programs import publish
        from optional.lifeos_release_manager.release_catalog import ReleaseRejected
        for action in ('apply', 'recover', 'restore'):
            with self.subTest(action=action), tempfile.TemporaryDirectory() as temp:
                profile = Path(temp)
                job = profile / '.lifeos-releases' / ('a' * 32)
                job.mkdir(parents=True, mode=0o700)
                package, certificate, marker, _ = ReleaseStageTests().package(job)
                shutil.copytree(package / 'optional/lifeos_release_manager', job / 'worker')
                (job / 'worker/manager.py').write_text('Changed retained worker')
                request = {'profile': str(profile), 'identifier': job.name, 'certificate': certificate}
                publish(job / 'request.json', json.dumps(request).encode())
                write_state(job, 'ready')
                with self.assertRaisesRegex(ReleaseRejected, 'release program differs'):
                    launch(profile, job.name, action)
                self.assertEqual(json.loads((job / 'status.json').read_bytes())['state'], 'ready')
                self.assertFalse((job / 'admission.json').exists())
                self.assertFalse((job / 'worker-launch.json').exists())

    def test_exact_release_version_does_not_enable_hermes_global_version(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('--version', action='store_true')
        commands = parser.add_subparsers(dest='command')
        configure(commands.add_parser('lifeos-release'))
        args = parser.parse_args(['lifeos-release', 'prepare', '--version', '0.4.0'])
        self.assertFalse(args.version)
        self.assertEqual(args.release_version, '0.4.0')

    def test_preparation_uses_the_qualified_candidate_worker(self):
        from optional.lifeos_release_manager import cli
        from optional.lifeos_release_manager.release_stage import sha
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            profile = home / '.hermes'
            profile.mkdir(mode=0o700)
            (profile / 'config.yaml').write_text('Preserve active configuration')
            job = profile / 'job'
            worker = job / 'worker'
            worker.mkdir(parents=True, mode=0o700)
            program = worker / 'release_worker.py'
            program.write_text('import json,os,sys\nfrom pathlib import Path\n'
                'job=Path(sys.argv[1])\nassert sys.argv[2:]==["--action","prepare"]\n'
                '(job/"candidate-planner.json").write_text(json.dumps({"home":os.environ["HOME"],'
                '"profile":os.environ["HERMES_HOME"],"python":sys.executable}))\n')
            files = {'release_worker.py': sha(program)}
            request = {'profile': str(profile), 'account_home': str(home),
                       'runtime': {'python': sys.executable, 'source': str(home / 'source')}}
            cli.prepare_plan(job, request, files)
            self.assertEqual(json.loads((job / 'candidate-planner.json').read_bytes()),
                             {'home': str(home), 'profile': str(profile), 'python': sys.executable})
            self.assertEqual((profile / 'config.yaml').read_text(), 'Preserve active configuration')
            (job / 'candidate-planner.json').unlink()
            program.write_text('raise SystemExit("Unqualified replacement")\n')
            with self.assertRaises(ValueError):
                cli.prepare_plan(job, request, files)
            self.assertFalse((job / 'candidate-planner.json').exists())

    def test_status_includes_preparation_before_the_request_exists(self):
        with tempfile.TemporaryDirectory() as temp:
            profile = Path(temp)
            job = profile / '.lifeos-releases' / ('a' * 32)
            job.mkdir(parents=True, mode=0o700)
            write_state(job, 'preparing')
            from optional.lifeos_release_manager.release_operation import process_stamp
            from optional.lifeos_release_manager.release_programs import publish
            publish(job / 'preparation-worker.json', json.dumps({'pid': os.getpid(),
                'start_time': process_stamp(os.getpid())}).encode())
            self.assertEqual(status(profile)['operations'], [{'identifier': job.name, 'state': 'preparing'}])
            write_state(job, 'preparation_failed', error='Preparation did not change the active installation.')
            self.assertEqual(status(profile, job.name)['state'], 'preparation_failed')

    def test_registers_release_management_without_loading_the_runtime_bridge(self):
        commands = {}
        skills = {}
        class Context:
            def register_cli_command(self, name, **entry):
                commands[name] = entry
            def register_skill(self, name, path, description='', frontmatter=None):
                skills[name] = Path(path)
        register(Context())
        parser = argparse.ArgumentParser()
        commands['lifeos-release']['setup_fn'](parser)
        self.assertEqual(parser.parse_args(['status']).action, 'status')
        self.assertEqual(parser.parse_args(['prepare', '--version', '0.4.0']).release_version, '0.4.0')
        self.assertTrue(skills['lifeos-release'].is_file())

    def test_status_reports_no_operations_and_does_not_create_release_state(self):
        from hermes_constants import set_hermes_home_override, reset_hermes_home_override
        with tempfile.TemporaryDirectory() as temp:
            profile = Path(temp)
            token = set_hermes_home_override(profile)
            try:
                parser = argparse.ArgumentParser()
                configure(parser)
                output = io.StringIO()
                with redirect_stdout(output):
                    self.assertEqual(run(parser.parse_args(['status'])), 0)
                self.assertEqual(json.loads(output.getvalue())['operations'], [])
                self.assertFalse((profile / '.lifeos-releases').exists())
            finally:
                reset_hermes_home_override(token)

    def test_compatibility_reports_the_running_hermes_without_creating_release_state(self):
        from hermes_constants import set_hermes_home_override, reset_hermes_home_override
        from lifeos_hook_bridge.install_source import SUPPORTED_HERMES_COMMIT
        from optional.lifeos_release_manager.host_compatibility import running_source
        with tempfile.TemporaryDirectory() as temp:
            profile = Path(temp)
            token = set_hermes_home_override(profile)
            try:
                parser = argparse.ArgumentParser()
                configure(parser)
                output = io.StringIO()
                with redirect_stdout(output):
                    code = run(parser.parse_args(['compatibility']))
                value = json.loads(output.getvalue())
                self.assertEqual(code, 0 if value['compatible'] or value['installed'] else 1)
                self.assertEqual(value['detected']['source'], str(running_source()))
                self.assertEqual(value['detected']['profile'], str(profile))
                self.assertEqual(value['supported'], [{'label': 'v0.21.7', 'commit': SUPPORTED_HERMES_COMMIT}])
                self.assertEqual(list(profile.iterdir()), [])
            finally:
                reset_hermes_home_override(token)

    def test_invalid_operation_identifier_refuses_without_reading_an_external_file(self):
        from hermes_constants import set_hermes_home_override, reset_hermes_home_override
        with tempfile.TemporaryDirectory() as temp:
            profile = Path(temp)
            token = set_hermes_home_override(profile)
            try:
                parser = argparse.ArgumentParser()
                configure(parser)
                output = io.StringIO()
                with redirect_stdout(output):
                    self.assertEqual(run(parser.parse_args(['status', '../outside'])), 1)
                self.assertEqual(json.loads(output.getvalue())['status'], 'rejected')
            finally:
                reset_hermes_home_override(token)

    def test_detached_worker_uses_a_new_session_and_reaps(self):
        from optional.lifeos_release_manager.cli import spawn_worker
        from optional.lifeos_release_manager.release_operation import record_worker, worker_running
        with tempfile.TemporaryDirectory() as temp:
            job = Path(temp)
            result = job / 'result.json'
            code = ('import json,os,time;from pathlib import Path;'
                    'Path("result.json").write_text(json.dumps({"pid":os.getpid(),"session":os.getsid(0)}));'
                    'time.sleep(0.3)')
            pid = spawn_worker(job, [sys.executable, '-B', '-c', code], dict(os.environ), job)
            record_worker(job, pid)
            deadline = time.monotonic() + 10
            while not result.exists() and time.monotonic() < deadline:
                time.sleep(0.01)
            values = json.loads(result.read_bytes())
            self.assertEqual(values, {'pid': pid, 'session': pid})
            self.assertNotEqual(values['session'], os.getsid(0))
            while worker_running(job) and time.monotonic() < deadline:
                time.sleep(0.01)
            self.assertFalse(worker_running(job))
            self.assertEqual((job / 'worker.stderr').read_bytes(), b'')
