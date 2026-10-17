# ABOUTME: Checks that a stopped memory workflow keeps a private record of why it stopped.
# ABOUTME: Covers the fresh-agent probe refusal text and the detached worker's failure record.
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from optional.lifeos_release_manager.release_catalog import ReleaseRejected


class ProbeFailureTests(unittest.TestCase):
    def test_probe_refusal_keeps_the_probe_message(self):
        from optional.lifeos_release_manager.memory_workflow import probe_failure
        stderr = ('Traceback (most recent call last):\n  File "<string>", line 6, in <module>\n'
                  'lifeos_memory_return_probe.memory_access.MemoryUnavailable: The fresh Hermes agent cannot '
                  'verify the reviewed built-in memory (ProviderNotConfiguredError)\n')
        error = probe_failure(stderr)
        self.assertIsInstance(error, ReleaseRejected)
        self.assertEqual(str(error), 'The fresh Hermes agent cannot verify the reviewed built-in memory '
                                     '(ProviderNotConfiguredError)')

    def test_failed_probe_output_tail_stays_in_a_private_job_file(self):
        from optional.lifeos_release_manager.memory_workflow import PROBE_OUTPUT_LINES, record_probe_output
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'probe-output.txt'
            lines = ['line %d' % number for number in range(PROBE_OUTPUT_LINES + 5)]
            record_probe_output(path, '\n'.join(lines) + '\n')
            self.assertEqual(path.read_text().splitlines(), lines[-PROBE_OUTPUT_LINES:])
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_unrecognized_probe_output_stays_generic(self):
        from optional.lifeos_release_manager.memory_workflow import probe_failure
        for stderr in ('', 'Segmentation fault\n', 'ValueError: synthetic secret value\n'):
            with self.subTest(stderr=stderr):
                self.assertEqual(str(probe_failure(stderr)),
                                 'The actual fresh Hermes agent does not verify the reviewed memory')


class ProbeBytecodeTests(unittest.TestCase):
    def test_isolated_probe_writes_no_bytecode_into_the_retained_bridge(self):
        from optional.lifeos_release_manager.memory_workflow import PROBE_CODE
        with tempfile.TemporaryDirectory() as directory:
            bridge = Path(directory) / 'bridge'
            bridge.mkdir()
            (bridge / 'helper.py').write_text('VALUE = 1\n')
            (bridge / 'memory_transition_probe.py').write_text(
                'from .helper import VALUE\n\ndef verify_builtin(expected):\n    return {"value": VALUE}\n')
            result = subprocess.run([sys.executable, '-I', '-c', 'import sys\n' + PROBE_CODE, str(bridge)],
                                    input='{}', capture_output=True, text=True, timeout=60)
            self.assertEqual((result.returncode, result.stderr), (0, ''))
            self.assertEqual(json.loads(result.stdout), {'value': 1})
            self.assertEqual(list(bridge.rglob('__pycache__')), [])


class WorkerFailureTests(unittest.TestCase):
    def test_stopped_worker_records_the_refusal_in_its_private_job(self):
        with tempfile.TemporaryDirectory() as directory:
            job = Path(directory) / '.lifeos-portability' / ('a' * 32)
            job.mkdir(parents=True, mode=0o700)
            worker = Path('optional/lifeos_release_manager/memory_workflow_worker.py').resolve()
            result = subprocess.run([sys.executable, '-B', str(worker), str(job), 'apply'],
                                    capture_output=True, text=True, timeout=60)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(result.stderr, 'The memory workflow stopped. The owner can review its private recovery state.\n')
            failure = json.loads((job / 'worker-failure.json').read_text())
            self.assertTrue(failure['exception'])
            self.assertTrue(failure['frames'])
            self.assertEqual((job / 'worker-failure.json').stat().st_mode & 0o077, 0)


if __name__ == '__main__':
    unittest.main()
