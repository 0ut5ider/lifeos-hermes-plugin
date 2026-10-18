# ABOUTME: Checks the account process scan that finds Hermes source consumers outside stopped services.
# ABOUTME: Starts real child processes that reference a disposable source through their environment or arguments.
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

from optional.lifeos_release_manager.consumer_scan import parent, process_names, source_consumers, start_time


class ConsumerScanTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        self.source = self.root / 'hermes-agent'
        self.source.mkdir()
        self.state = self.root / 'installs/0123456789abcdef'
        self.state.mkdir(parents=True)

    def start(self, *, environment=None, arguments=(), cwd=None):
        process = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)', *arguments],
                                   env={**os.environ, **(environment or {})}, cwd=cwd)
        self.addCleanup(process.wait)
        self.addCleanup(process.kill)
        deadline = time.monotonic() + 5
        while not Path('/proc', str(process.pid), 'cmdline').read_bytes() and time.monotonic() < deadline:
            time.sleep(0.01)
        return process.pid

    def scan(self, **options):
        return {item['pid'] for item in source_consumers(self.source, self.state, **options)}

    def test_process_importing_the_source_through_its_path_is_found(self):
        pid = self.start(environment={'PYTHONPATH': str(self.source) + ':/elsewhere'})
        self.assertIn(pid, self.scan())

    def test_process_running_from_the_environment_generation_is_found(self):
        pid = self.start(arguments=(str(self.state / 'environments/abc/venv/bin/python'),))
        self.assertIn(pid, self.scan())

    def test_process_working_in_the_source_is_found(self):
        pid = self.start(cwd=self.source)
        self.assertIn(pid, self.scan())

    def test_process_started_by_the_stock_launcher_is_found(self):
        # The stock launcher passes the checkout inside Python code, quoted, and need not re-execute.
        for quote in ("'", '"'):
            code = 'import sys, time; sys.path.insert(0, ' + quote + str(self.source) + quote + '); time.sleep(60)'
            process = subprocess.Popen([sys.executable, '-I', '-c', code, 'dashboard'], cwd=self.root)
            self.addCleanup(process.wait)
            self.addCleanup(process.kill)
            deadline = time.monotonic() + 5
            while not Path('/proc', str(process.pid), 'cmdline').read_bytes() and time.monotonic() < deadline:
                time.sleep(0.01)
            with self.subTest(quote=quote):
                self.assertIn(process.pid, self.scan())
        sibling = 'import time; print(' + repr(str(self.source) + '-other') + '); time.sleep(60)'
        pid = self.start(arguments=(sibling,), cwd=self.root)
        self.assertNotIn(pid, self.scan())

    def test_unrelated_process_and_sibling_paths_are_ignored(self):
        sibling = self.root / 'hermes-agent-other'
        sibling.mkdir()
        pid = self.start(environment={'PYTHONPATH': str(sibling)})
        self.assertNotIn(pid, self.scan())

    def test_excluded_processes_and_this_process_are_ignored(self):
        pid = self.start(environment={'PYTHONPATH': str(self.source)})
        self.assertNotIn(pid, self.scan(excluded_pids={pid}))
        os.environ['LIFEOS_SCAN_SELF'] = str(self.source)
        self.addCleanup(os.environ.pop, 'LIFEOS_SCAN_SELF')
        self.assertNotIn(os.getpid(), self.scan())

    def test_a_dashboard_that_runs_the_scan_reports_itself(self):
        # The dashboard serves the review, so it must appear as the hand-started consumer that its unit replaces.
        code = ('import os, sys; sys.path.insert(0, sys.argv[3]); '
                'from optional.lifeos_release_manager.consumer_scan import source_consumers; '
                'print([item["role"] for item in source_consumers(sys.argv[1], sys.argv[2]) if item["pid"] == os.getpid()])')
        root = Path(__file__).resolve().parents[1]
        for role, expected in (('dashboard', "['dashboard']"), ('chat', '[]')):
            result = subprocess.run([sys.executable, '-c', code, str(self.source), str(self.state), str(root), role],
                                    env={**os.environ, 'PYTHONPATH': str(self.source)}, capture_output=True, text=True, timeout=30)
            with self.subTest(role=role):
                self.assertEqual(result.stdout.strip(), expected, result.stderr)

    def test_result_names_the_command_without_its_arguments_or_environment(self):
        pid = self.start(environment={'PYTHONPATH': str(self.source), 'SECRET_TOKEN': 'do-not-report'})
        item = next(item for item in source_consumers(self.source, self.state) if item['pid'] == pid)
        self.assertEqual(item['command'], Path(sys.executable).name)
        self.assertEqual(item['role'], 'other')
        self.assertIsInstance(item['start_time'], int)
        self.assertNotIn('do-not-report', repr(item))


class DashboardOptionTests(unittest.TestCase):
    def options(self, *arguments):
        from optional.lifeos_release_manager.consumer_scan import dashboard_options
        process = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)', *arguments])
        self.addCleanup(process.wait)
        self.addCleanup(process.kill)
        deadline = time.monotonic() + 5
        while not Path('/proc', str(process.pid), 'cmdline').read_bytes() and time.monotonic() < deadline:
            time.sleep(0.01)
        return dashboard_options(process.pid)

    def test_only_the_address_options_after_the_dashboard_command_are_read(self):
        self.assertEqual(self.options('dashboard', '--host', '0.0.0.0', '--port', '9200', '--skip-build'),
                         {'host': '0.0.0.0', 'port': 9200})
        self.assertEqual(self.options('dashboard', '--host=::1', '--port=8080'), {'host': '::1', 'port': 8080})
        self.assertEqual(self.options('--host', '0.0.0.0', 'dashboard'), {})
        self.assertEqual(self.options('dashboard', '--no-open'), {})
        self.assertEqual(self.options('--name', 'dashboard', '--host', '0.0.0.0'), {})
        # serve runs the same server headless.
        self.assertEqual(self.options('serve', '--host', '0.0.0.0', '--port', '9200'), {'host': '0.0.0.0', 'port': 9200})
        # The defaults are the address of a unit without options.
        self.assertEqual(self.options('dashboard', '--host', '127.0.0.1', '--port', '9119'), {})

    def test_unusable_address_options_refuse(self):
        from optional.lifeos_release_manager.release_catalog import ReleaseRejected
        for arguments in (('dashboard', '--port', '0'), ('dashboard', '--port', 'http'), ('dashboard', '--host', 'a b'),
                          ('dashboard', '--host'), ('dashboard', '--host', '$(id)'),
                          ('dashboard', '--ho', '0.0.0.0'), ('serve', '--por=9200')):
            with self.subTest(arguments=arguments), self.assertRaisesRegex(ReleaseRejected, 'address'):
                self.options(*arguments)


class ProcessIdentityTests(unittest.TestCase):
    def test_start_time_and_parent_come_from_the_kernel_process_record(self):
        from optional.lifeos_release_manager.release_operation import process_stamp
        process = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])
        self.addCleanup(process.wait)
        self.addCleanup(process.kill)
        self.assertEqual(parent(process.pid), os.getpid())
        self.assertGreaterEqual(start_time(process.pid), start_time(os.getpid()))
        self.assertEqual(str(start_time(process.pid)), process_stamp(process.pid))
        with self.assertRaises(FileNotFoundError):
            start_time(2 ** 22 + 1)

    def test_process_names_list_each_command_with_its_process_id(self):
        self.assertEqual(process_names([{'command': 'hermes', 'pid': 12}, {'command': 'python3', 'pid': 7}]),
                         'hermes (12), python3 (7)')


if __name__ == '__main__':
    unittest.main()


class ConsumerRoleTests(unittest.TestCase):
    def test_hermes_command_lines_are_classified_without_exporting_them(self):
        from optional.lifeos_release_manager.consumer_scan import _role
        self.assertEqual(_role(b'/home/o/.hermes/hermes-agent/.hermes/bin/hermes\0dashboard\0--no-open\0'), 'dashboard')
        self.assertEqual(_role(b'python\0-m\0hermes_cli.main\0serve\0'), 'dashboard')
        self.assertEqual(_role(b'hermes\0gateway\0run\0'), 'gateway')
        self.assertEqual(_role(b'hermes\0chat\0'), 'other')
        self.assertEqual(_role(b'hermes\0gateway\0status\0'), 'other')
        # A command word that is the value of an option names no command.
        self.assertEqual(_role(b'hermes\0lifeos-release\0prepare\0--name\0dashboard\0'), 'other')
        self.assertEqual(_role(b'hermes\0chat\0--title\0gateway\0run\0'), 'other')
        self.assertEqual(_role(b'hermes\0-p\0default\0serve\0--port\09119\0'), 'dashboard')
