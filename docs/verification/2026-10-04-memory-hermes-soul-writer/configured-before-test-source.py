# ABOUTME: Characterizes the native standalone Hermes soul and workspace publisher.
# ABOUTME: Uses an isolated program copy so source anchoring reads synthetic owner files.
import json
from pathlib import Path
import shutil
import subprocess
import unittest

import test_memory_state_evidence as evidence_fixture
from test_memory_native import SOURCE


class MemoryHermesSoulWriterTests(unittest.TestCase):
    def setUp(self):
        self.fixture = evidence_fixture.MemoryStateEvidenceTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        self.home = self.fixture.fixture.fixture.fixture.home
        tools = self.root / 'LIFEOS/TOOLS'
        tools.unlink()
        tools.mkdir()
        for child in (SOURCE / 'LIFEOS/TOOLS').iterdir():
            if child.name == 'RenderHermesSoul.ts':
                shutil.copyfile(child, tools / child.name)
            else:
                (tools / child.name).symlink_to(child, target_is_directory=child.is_dir())
        self.identity = self.root / 'LIFEOS/USER/DIGITAL_ASSISTANT/DA_IDENTITY.md'
        self.identity.write_text('# Synthetic assistant\n## Personality\nSynthetic personality for the fixture.\n'
            '## Relationship\nSynthetic shared work pact.\n## Writing Style\nUse concrete source evidence.\n')
        (self.root / 'LIFEOS/USER/PRINCIPAL/PRINCIPAL_IDENTITY.md').write_text(
            '# Synthetic principal\n## Quick Reference\n- Role: Synthetic test operator\n'
            '## Worldview\nSynthetic worldview.\n')
        (self.root / 'LIFEOS/USER/TELOS/PRINCIPAL_TELOS.md').write_text(
            '## Missions\n- Synthetic mission\n## Active Goals (2026)\n- Synthetic goal\n')
        (self.root / 'LIFEOS/USER/PROJECTS.md').write_text('| **SyntheticProject** | synthetic |\n')
        self.profile = self.fixture.fixture.fixture.configuration.path.parent
        self.workspace = self.home / 'hermes-workspace'
        self.fixture.fixture.fixture.configuration.update(
            lambda value: value.update(hermes_workspace=str(self.workspace)))
        self.soul = self.profile / 'SOUL.md'
        self.context = self.workspace / '.hermes.md'

    def call(self, *args, context=True, profile=None, workspace=None):
        env = self.fixture.fixture.environment(context=context)
        env.update(HERMES_HOME=str(self.profile if profile is None else profile),
                   HERMES_WORKSPACE=str(self.workspace if workspace is None else workspace))
        return subprocess.run(['bun', '--no-install', str(self.root / 'LIFEOS/TOOLS/RenderHermesSoul.ts'), *args],
            env=env, capture_output=True, text=True, timeout=40)

    def successful(self, *args):
        result = self.call(*args)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        return result

    def previous(self):
        self.profile.mkdir(exist_ok=True)
        self.workspace.mkdir()
        self.soul.write_text('Synthetic previous soul\n')
        self.context.write_text('Synthetic previous workspace\n')
        return self.soul.read_bytes(), self.context.read_bytes()

    def test_owner_native_render_and_check_preserve_synthetic_content(self):
        printed = self.successful('--stdout')
        self.assertIn('Synthetic personality', printed.stdout)
        self.assertFalse(self.soul.exists())
        self.successful()
        self.assertEqual(self.soul.read_text(), printed.stdout)
        self.assertIn('SyntheticProject', self.soul.read_text())
        self.assertIn('soul digest', self.context.read_text())
        self.successful('--check')

    def test_missing_context_cannot_publish_or_print_source_body(self):
        before = self.previous()
        result = self.call(context=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((self.soul.read_bytes(), self.context.read_bytes()), before)
        self.assertNotIn('Synthetic personality', self.call('--stdout', context=False).stdout)

    def test_read_only_owner_preserves_both_previous_outputs(self):
        before = self.previous()
        self.fixture.fixture.fixture.configuration.update(lambda value: value['destinations']['chat-a:200'].update(write=[]))
        self.call()
        self.assertEqual((self.soul.read_bytes(), self.context.read_bytes()), before)

    def test_private_identity_cannot_reach_the_soul(self):
        self.identity.write_text('# Synthetic assistant\n## Personality\n<private>SyntheticPrivateSoulBody</private>\n')
        self.assertNotIn('SyntheticPrivateSoulBody', self.call('--stdout').stdout)

    def test_foreign_identity_source_refuses_without_replacing_outputs(self):
        before = self.previous()
        foreign = self.home / 'foreign-soul-identity.md'
        foreign.write_text('# Synthetic assistant\n## Personality\nSyntheticForeignSoulBody\n')
        self.identity.unlink(); self.identity.symlink_to(foreign)
        result = self.call()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((self.soul.read_bytes(), self.context.read_bytes()), before)

    def test_successful_outputs_have_private_permissions(self):
        self.successful()
        self.assertEqual(self.soul.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.context.stat().st_mode & 0o777, 0o600)

    def test_arbitrary_profile_or_workspace_destinations_are_not_created(self):
        for profile, workspace in ((self.home / 'foreign-profile', self.workspace),
                                   (self.profile, self.home / 'foreign-workspace')):
            with self.subTest(profile=profile, workspace=workspace):
                self.assertNotEqual(self.call(profile=profile, workspace=workspace).returncode, 0)
                self.assertFalse((profile / 'SOUL.md').exists())
                self.assertFalse((workspace / '.hermes.md').exists())
