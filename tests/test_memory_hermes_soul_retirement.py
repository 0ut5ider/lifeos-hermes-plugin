# ABOUTME: Verifies native soul rendering after actual memory retirement.
# ABOUTME: Checks decoded retired names without losing unrelated admitted identity content.
import unittest

import test_memory_hermes_soul_writer as soul_fixture
from test_memory_native import OWNER


class MemoryHermesSoulRetirementTests(unittest.TestCase):
    def setUp(self):
        self.fixture = soul_fixture.MemoryHermesSoulWriterTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.memory = self.fixture.fixture.fixture.fixture.fixture.memory

    def retire(self, content):
        saved = self.memory.remember(OWNER, category='assistant', content=content,
            title='Synthetic retired soul claim', project='general', request_id='soul-retired-name')
        self.assertEqual(saved['status'], 'committed', saved)
        result = self.memory.forget(OWNER, saved['reference'], 'soul-forget-name')
        self.assertEqual(result['status'], 'committed', result)
        for path in (self.fixture.root / 'LIFEOS/USER').rglob('*.md'):
            path.write_text(path.read_text())
        constitution = self.fixture.root / 'LIFEOS/LIFEOS_SYSTEM_PROMPT.md'
        constitution.write_text(constitution.read_text())

    def test_unrelated_retirement_preserves_current_native_soul(self):
        self.retire('RULE: SyntheticUnrelatedSoulRetirement')
        self.assertIn('Synthetic personality', self.fixture.successful('--stdout').stdout)

    def test_decoded_retired_full_name_is_excluded(self):
        self.retire('RULE: FixtureRetiredSoulName')
        self.fixture.identity.write_text('---\ncore:\n  full_name: "\\u0046ixtureRetiredSoulName"\n---\n'
            '# Synthetic assistant\n## Personality\nSynthetic personality for the fixture.\n')
        result = self.fixture.successful('--stdout')
        self.assertNotIn('FixtureRetiredSoulName', result.stdout)
        self.assertNotIn('Synthetic personality', result.stdout)
