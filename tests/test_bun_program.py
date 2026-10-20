# ABOUTME: Checks how native memory finds the Bun program when the dashboard's PATH lacks the account's programs.
# ABOUTME: Uses disposable account homes with real executable files.
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from lifeos_hook_bridge.memory_access import bun_program


class BunProgramTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.home = Path(folder.name)
        self.empty = self.home / 'empty-path'
        self.empty.mkdir()

    def executable(self, path):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('#!/bin/sh\n')
        path.chmod(0o755)
        return path

    def test_path_lookup_comes_first(self):
        on_path = self.executable(self.home / 'tools/bun')
        self.executable(self.home / '.local/bin/bun')
        with mock.patch.dict(os.environ, {'PATH': str(on_path.parent)}):
            self.assertEqual(bun_program(self.home), str(on_path))

    def test_account_program_is_used_when_path_lacks_bun(self):
        account = self.executable(self.home / '.local/bin/bun')
        with mock.patch.dict(os.environ, {'PATH': str(self.empty)}):
            self.assertEqual(bun_program(self.home), str(account))

    def test_missing_bun_keeps_the_bare_name_for_the_error_message(self):
        with mock.patch.dict(os.environ, {'PATH': str(self.empty)}):
            self.assertEqual(bun_program(self.home), 'bun')

    def test_default_home_is_the_account_home_not_home_variable(self):
        import pwd
        with mock.patch.dict(os.environ, {'PATH': str(self.empty), 'HOME': str(self.home)}):
            self.executable(self.home / '.local/bin/bun')
            expected = Path(pwd.getpwuid(os.getuid()).pw_dir) / '.local/bin/bun'
            self.assertEqual(bun_program(), str(expected) if expected.is_file() else 'bun')


if __name__ == '__main__':
    unittest.main()
