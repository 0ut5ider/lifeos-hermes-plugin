# ABOUTME: Exercises native distill marking against synthetic digest sources.
# ABOUTME: Requires owner publication, current source policy, and private fixed destinations.
import json
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

    def test_private_digest_is_refused(self):
        self.digest.write_text('<private>Synthetic hidden digest.</private>\n')
        self.assertNotEqual(self.call().returncode, 0)
        self.assertFalse(self.state.exists())
