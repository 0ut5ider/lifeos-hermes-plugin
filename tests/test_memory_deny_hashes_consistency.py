# ABOUTME: Verifies actual post-render conflicts and interrupted hash publication recovery.
# ABOUTME: Keeps later source and environment edits while withholding stale token output.
import json
from pathlib import Path
import subprocess
import sys
import unittest

import test_memory_deny_hashes as hash_fixture


class MemoryDenyHashesConsistencyTests(unittest.TestCase):
    def setUp(self):
        self.fixture = hash_fixture.MemoryDenyHashesTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def process(self, mode):
        import os
        result = subprocess.run([sys.executable, str(Path(__file__).with_name('memory_deny_hashes_process.py')),
            str(self.fixture.fixture.configuration.path), mode],
            env=dict(os.environ), capture_output=True, text=True, timeout=40)
        self.assertEqual(result.stderr, '')
        return result

    def previous(self):
        self.fixture.output.parent.mkdir(parents=True, exist_ok=True)
        self.fixture.output.write_text('{"synthetic_previous":"preserved"}\n')
        return self.fixture.env.read_bytes(), self.fixture.output.read_bytes()

    def test_actual_post_render_changes_refuse_and_preserve_later_edits(self):
        configuration = self.fixture.fixture.configuration
        baseline = configuration.load()
        self.previous()
        for mode in ('source', 'private', 'authority', 'environment', 'environment_large', 'marker'):
            with self.subTest(mode=mode):
                configuration.update(lambda value: value.update(baseline))
                self.fixture.identity.write_text('# Synthetic principal\nFixtureSurname FixtureGivenname\n')
                (self.fixture.root / 'skills/_LIFEOS').mkdir(exist_ok=True)
                self.fixture.env.write_text('SYNTHETIC_KEEP=fixture\n')
                before = self.fixture.env.read_bytes(), self.fixture.output.read_bytes()
                result = self.process(mode)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertFalse(json.loads(result.stdout)['ok'])
                self.assertNotIn('fixturesurname fixturegivenname', result.stdout)
                self.assertEqual(self.fixture.output.read_bytes(), before[1])
                if mode.startswith('environment'):
                    self.assertIn(b'SYNTHETIC_LATER=', self.fixture.env.read_bytes())
                else:
                    self.assertEqual(self.fixture.env.read_bytes(), before[0])
                self.assertFalse((self.fixture.root / 'LIFEOS/MEMORY/STATE/memory-operation.json').exists())

    def test_actual_interruption_restores_environment_and_previous_hashes(self):
        before = self.previous()
        self.assertEqual(self.process('interrupt').returncode, 73)
        self.assertNotEqual(self.fixture.env.read_bytes(), before[0])
        self.assertEqual(self.fixture.output.read_bytes(), before[1])
        self.fixture.successful('--dry-run')
        self.assertEqual((self.fixture.env.read_bytes(), self.fixture.output.read_bytes()), before)

    def test_actual_interruption_removes_new_hash_destination(self):
        before = self.fixture.env.read_bytes()
        self.assertEqual(self.process('interrupt').returncode, 73)
        self.fixture.successful('--dry-run')
        self.assertEqual(self.fixture.env.read_bytes(), before)
        self.assertFalse(self.fixture.output.exists())
