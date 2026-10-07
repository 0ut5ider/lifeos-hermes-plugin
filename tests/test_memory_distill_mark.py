# ABOUTME: Exercises native distill marking against synthetic digest sources.
# ABOUTME: Requires owner publication, current source policy, and private fixed destinations.
import json
from pathlib import Path
import subprocess
import sys
import os
import shutil
import unittest

import test_memory_distill as distill_fixture


class MemoryDistillMarkTests(unittest.TestCase):
    def setUp(self):
        self.fixture = distill_fixture.MemoryDistillTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        self.state = self.root / 'LIFEOS/MEMORY/STATE/distill.json'
        self.digest = self.root / 'LIFEOS/MEMORY/DIGESTS/2026-10-04-distill.md'
        self.digest.parent.mkdir(parents=True)
        path = self.fixture.gather()['candidates'][0]['path']
        self.digest.write_text('# Synthetic digest\n\n### Synthetic digest item\n\nSynthetic current distill marker\n\n`' + path + '`\n')

    def call(self, *, context=True, digest=None):
        return self.fixture.call('mark', '--digest', str(digest or self.digest), context=context)

    def test_owner_mark_preserves_native_counts_and_private_state(self):
        before = self.digest.read_bytes()
        result = self.call()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        self.assertEqual(json.loads(result.stdout), {'slugs': 1, 'items': 1})
        state = json.loads(self.state.read_text())
        self.assertEqual(len(state['surfaced_slugs']), 1)
        self.assertEqual(len(state['item_hashes']), 1)
        self.assertEqual(self.state.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.digest.read_bytes(), before)
        repeated = self.call()
        self.assertEqual(repeated.returncode, 0, repeated.stderr)
        self.assertEqual(repeated.stderr, '')
        self.assertEqual(json.loads(repeated.stdout), {'slugs': 0, 'items': 0})

    def test_missing_context_refuses_before_state_publication(self):
        self.assertNotEqual(self.call(context=False).returncode, 0)
        self.assertFalse(self.state.exists())

    def test_read_only_owner_refuses_state_publication(self):
        self.fixture.configuration.update(lambda value: value['destinations']['chat-a:200'].update(write=[]))
        self.assertNotEqual(self.call().returncode, 0)
        self.assertFalse(self.state.exists())

    def test_foreign_digest_source_is_refused(self):
        foreign = self.fixture.fixture.fixture.home / 'foreign-distill.md'
        before = self.digest.read_bytes()
        foreign.write_bytes(before)
        self.assertNotEqual(self.call(digest=foreign).returncode, 0)
        self.assertFalse(self.state.exists())
        self.assertEqual(foreign.read_bytes(), before)

    def test_foreign_state_destination_is_preserved(self):
        self.state.parent.mkdir(parents=True, exist_ok=True)
        foreign = self.fixture.fixture.fixture.home / 'foreign-distill-state.json'
        before = b'{"synthetic_foreign":"preserved"}\n'
        foreign.write_bytes(before)
        self.state.symlink_to(foreign)
        self.assertNotEqual(self.call().returncode, 0)
        self.assertEqual(foreign.read_bytes(), before)

    def test_valid_foreign_state_destination_is_preserved(self):
        self.state.parent.mkdir(parents=True, exist_ok=True)
        foreign = self.fixture.fixture.fixture.home / 'foreign-valid-distill-state.json'
        before = b'{"schema_version":1,"surfaced_slugs":{},"item_hashes":{},"last_run":null}\n'
        foreign.write_bytes(before)
        self.state.symlink_to(foreign)
        self.assertNotEqual(self.call().returncode, 0)
        self.assertEqual(foreign.read_bytes(), before)

    def test_private_digest_is_refused(self):
        self.digest.write_text('<private>Synthetic hidden digest.</private>\n')
        self.assertNotEqual(self.call().returncode, 0)
        self.assertFalse(self.state.exists())

    def process(self, mode):
        result = subprocess.run([sys.executable, str(Path(__file__).with_name('memory_distill_mark_process.py')),
            str(self.fixture.configuration.path), mode], capture_output=True, text=True, timeout=40)
        self.assertEqual(result.stderr, '')
        return result

    def test_actual_later_state_edit_is_preserved(self):
        result = self.process('state')
        self.assertEqual(result.returncode, 0, result.stderr)
        value = json.loads(result.stdout)
        self.assertFalse(value['result']['ok'], value)
        self.assertTrue(value['later_state_preserved'], value)

    def test_actual_later_digest_edit_refuses_state_publication(self):
        result = self.process('digest')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(json.loads(result.stdout)['result']['ok'])
        self.assertEqual(self.digest.read_text(), 'Synthetic later digest edit.\n')
        self.assertFalse(self.state.exists())

    def test_actual_revocation_refuses_state_publication(self):
        result = self.process('authority')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(json.loads(result.stdout)['result']['ok'])
        self.assertFalse(self.state.exists())

    def test_actual_interruption_restores_previous_state_on_readback(self):
        self.state.parent.mkdir(parents=True, exist_ok=True)
        before = b'{"schema_version":1,"surfaced_slugs":{},"item_hashes":{},"last_run":null}\n'
        self.state.write_bytes(before)
        self.assertEqual(self.process('interrupt').returncode, 73)
        self.assertNotEqual(self.state.read_bytes(), before)
        result = self.fixture.call('status')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        self.assertEqual(self.state.read_bytes(), before)

    def test_revocation_after_reservation_preserves_later_state_edit(self):
        result = self.process('reserved-authority')
        self.assertEqual(result.returncode, 0, result.stderr)
        value = json.loads(result.stdout)
        self.assertFalse(value['result']['ok'], value)
        self.assertTrue(value['later_state_preserved'], value)

    def test_forgotten_digest_claim_is_refused(self):
        from test_memory_native import OWNER
        self.fixture.native.forget(OWNER, self.fixture.saved['reference'], 'distill-mark-forget')
        self.assertNotEqual(self.call().returncode, 0)
        self.assertFalse(self.state.exists())

    def test_original_native_mark_matches_counts_and_state_bytes(self):
        result = self.call()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        before = self.state.read_bytes()
        self.state.unlink()
        tools = self.root / 'LIFEOS/TOOLS'
        source = tools.resolve()
        tools.unlink()
        tools.mkdir()
        for path in source.iterdir():
            if path.name != 'KnowledgeDistill.ts':
                (tools / path.name).symlink_to(path)
        control = Path(os.environ['LIFEOS_FRESHNESS_CONTROL_SOURCE']) / 'LIFEOS/TOOLS/KnowledgeDistill.ts'
        shutil.copyfile(control, tools / 'KnowledgeDistill.ts')
        original = self.call()
        self.assertEqual(original.returncode, 0, original.stderr)
        self.assertEqual(original.stderr, '')
        self.assertEqual(original.stdout, result.stdout)
        self.assertEqual(self.state.read_bytes(), before)
