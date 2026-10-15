# ABOUTME: Checks that optimization cannot bypass the disposable removal fault injector guards.
# ABOUTME: Executes only non-root refusal paths and never signals a process or reads guest state.
import ast
import os
from pathlib import Path
import subprocess
import sys
import unittest

SCRIPT = Path(__file__).with_name('interrupt_guest_removal.py')


class FaultInjectorTests(unittest.TestCase):
    def test_destructive_targeting_does_not_depend_on_assert(self):
        self.assertFalse(any(isinstance(node, ast.Assert) for node in ast.walk(ast.parse(SCRIPT.read_text()))))

    @unittest.skipIf(os.getuid() == 0, 'The refusal control requires a non-root test process')
    def test_non_root_refuses_before_guest_access_with_optimization(self):
        for option in ([], ['-O'], ['-OO']):
            with self.subTest(option=option):
                result = subprocess.run([sys.executable, *option, str(SCRIPT), 'a' * 32, '--label', 'synthetic-denial'],
                    capture_output=True, text=True, timeout=15)
                self.assertEqual(result.returncode, 1)
                self.assertEqual(result.stdout, '')
                self.assertIn('RuntimeError: Run this disposable fault fixture as root', result.stderr)
                self.assertNotIn('FileNotFoundError', result.stderr)
                self.assertNotIn('AssertionError', result.stderr)
