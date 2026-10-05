# ABOUTME: Verifies admitted nondefault assistant and principal names in native output.
# ABOUTME: Checks the soul and workspace use the same decoded source names.
import unittest

import test_memory_hermes_soul_writer as soul_fixture


class MemoryHermesSoulNamesTests(unittest.TestCase):
    def test_admitted_names_reach_both_native_artifacts(self):
        fixture = soul_fixture.MemoryHermesSoulWriterTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        fixture.identity.write_text('---\ncore:\n  name: FixtureAssistantName\n'
            '  full_name: Fixture Assistant Fullname\n---\n## Personality\nSynthetic personality.\n')
        (fixture.root / 'LIFEOS/USER/PRINCIPAL/PRINCIPAL_IDENTITY.md').write_text(
            '---\ncore:\n  name: FixturePrincipalName\n---\n## Quick Reference\nSynthetic operator.\n')
        fixture.successful()
        self.assertTrue(fixture.soul.read_text().startswith('# FixtureAssistantName\n'))
        self.assertIn('Fixture Assistant Fullname', fixture.soul.read_text())
        self.assertIn('FixturePrincipalName', fixture.soul.read_text())
        self.assertIn('FixtureAssistantName', fixture.context.read_text())
        self.assertIn('FixturePrincipalName', fixture.context.read_text())
