# ABOUTME: Checks the bounded native error text that installation and mount failures report.
# ABOUTME: Runs real child processes that fail with known output.
import subprocess
import sys
import unittest
from pathlib import Path

from lifeos_hook_bridge.native_output import failure_detail


class NativeOutputTests(unittest.TestCase):
    def failed(self, program):
        return subprocess.run([sys.executable, '-c', program], text=True, capture_output=True)

    def test_detail_keeps_the_last_error_lines(self):
        result = self.failed('import sys\nprint("ok")\nfor n in range(30): print(f"line {n}", file=sys.stderr)\nsys.exit(4)')
        self.assertEqual(failure_detail(result), '\n'.join(f'line {n}' for n in range(22, 30)))

    def test_detail_uses_standard_output_without_error_text(self):
        result = self.failed('print("only stdout reason")\nraise SystemExit(2)')
        self.assertEqual(failure_detail(result), 'only stdout reason')

    def test_detail_is_bounded(self):
        result = self.failed('import sys\nprint("x" * 5000, file=sys.stderr)\nsys.exit(1)')
        self.assertEqual(len(failure_detail(result)), 1000)

    def test_detail_is_empty_without_output(self):
        self.assertEqual(failure_detail(self.failed('raise SystemExit(1)')), '')

    def test_mount_failure_reports_native_error_text(self):
        from lifeos_hook_bridge.mount_transaction import MountError, _run
        program = 'import sys\nprint("Synthetic mount reason", file=sys.stderr)\nsys.exit(5)'
        with self.assertRaisesRegex(MountError, 'Mount check exited with code 5: Synthetic mount reason$'):
            _run([sys.executable, '-c', program], Path.cwd() / 'child', {}, 'Mount check')

    def test_update_worker_failure_reports_native_error_text(self):
        from lifeos_hook_bridge.update_worker import _run
        program = 'import sys\nprint("Synthetic update reason", file=sys.stderr)\nsys.exit(6)'
        with self.assertRaisesRegex(RuntimeError, 'exited with code 6: Synthetic update reason$'):
            _run([sys.executable, '-c', program], home=Path.cwd())


if __name__ == '__main__':
    unittest.main()
