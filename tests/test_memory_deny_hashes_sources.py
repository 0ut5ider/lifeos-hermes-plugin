# ABOUTME: Checks the exact deny corpus namespace and current source-review admission.
# ABOUTME: Preserves generic reader limits and the native operator allowlist behavior.
import os
from pathlib import Path
import unittest

import test_memory_deny_hashes as hash_fixture
from test_memory_native import OWNER
from lifeos_hook_bridge.memory_service import MemoryService
from lifeos_hook_bridge.memory_source_review import preview, approve


class MemoryDenyHashesSourcesTests(unittest.TestCase):
    def setUp(self):
        self.fixture = hash_fixture.MemoryDenyHashesTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.memory = self.fixture.fixture.fixture.memory
        self.service = MemoryService(self.fixture.fixture.configuration)
        self.scope = self.service.scope(self.fixture.fixture.context)

    def source(self, relative, content):
        path = self.fixture.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    def test_deny_namespace_does_not_expand_generic_reader(self):
        for relative in ('LIFEOS/USER/PRINCIPAL/RESUME.md', 'LIFEOS/USER/CONTACTS.md',
                'LIFEOS/USER/GEAR.md', 'LIFEOS/MEMORY/_NETWORK/assets.json',
                'LIFEOS/MEMORY/_NETWORK/topology-snapshot-fixture.md',
                'LIFEOS/USER/CONFIG/denyhash-allowlist.txt'):
            with self.subTest(relative=relative):
                path = self.source(relative, '{}\n' if relative.endswith('.json') else 'Synthetic fixture text\n')
                result = self.service.native(self.fixture.fixture.context, 'read_source', {'path': str(path)})
                self.assertFalse(result['ok'])

    def test_old_resume_requires_exact_review_after_retirement(self):
        saved = self.memory.remember(OWNER, category='assistant', content='RULE: SyntheticUnrelatedHashRetirement',
            title='Synthetic hash retirement', project='general', request_id='hash-retire')
        self.assertEqual(saved['status'], 'committed', saved)
        self.assertEqual(self.memory.forget(OWNER, saved['reference'], 'hash-forget')['status'], 'committed')
        relative = 'LIFEOS/USER/PRINCIPAL/RESUME.md'
        path = self.source(relative, 'FixtureReviewname FixtureReviewsurname\n')
        os.utime(path, (1, 1))
        self.assertNotIn('fixturereviewname fixturereviewsurname', self.fixture.successful('--dry-run', '--show-tokens').stdout)
        current = preview(self.memory, self.scope, [relative])
        self.assertTrue(current['sources'][0]['accepted'], current)
        self.assertEqual(approve(self.memory, self.scope, [relative], current['signature'])['status'], 'committed')
        self.assertIn('fixturereviewname fixturereviewsurname', self.fixture.successful('--dry-run', '--show-tokens').stdout)

    def test_operator_allowlist_keeps_native_token_rules(self):
        self.source('LIFEOS/USER/CONFIG/denyhash-allowlist.txt', 'fixturesurname\nfixturegivenname\n')
        self.assertNotIn('fixturesurname fixturegivenname', self.fixture.successful('--dry-run', '--show-tokens').stdout)
