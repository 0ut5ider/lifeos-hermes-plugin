# ABOUTME: Exercises the installation command through its real parser and private profile state.
# ABOUTME: Verifies that status and invalid requests cannot replace the active integration.
import argparse
from contextlib import redirect_stdout
import io
import json
import os
import subprocess
import sys
import time
from pathlib import Path
import tempfile
import unittest

from optional.lifeos_release_manager import register
from optional.lifeos_release_manager.cli import configure, run, status, write_state


class ReleaseManagerCommandTests(unittest.TestCase):
    def test_status_includes_preparation_before_the_request_exists(self):
        with tempfile.TemporaryDirectory() as temp:
            profile = Path(temp)
            job = profile / '.lifeos-releases' / ('a' * 32)
            job.mkdir(parents=True, mode=0o700)
            write_state(job, 'preparing')
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
        self.assertEqual(parser.parse_args(['prepare', '--version', '0.4.0']).version, '0.4.0')
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
