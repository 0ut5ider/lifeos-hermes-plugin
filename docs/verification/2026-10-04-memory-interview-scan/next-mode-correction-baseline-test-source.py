# ABOUTME: Characterizes native interview scan output from synthetic owner sources.
# ABOUTME: Checks admitted section scoring, source redirects, and current setup boundaries.
import json
from pathlib import Path
import subprocess
import unittest

import test_memory_state_evidence as evidence_fixture


class MemoryInterviewScanTests(unittest.TestCase):
    def setUp(self):
        self.fixture = evidence_fixture.MemoryStateEvidenceTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        self.identity = self.root / 'LIFEOS/USER/DIGITAL_ASSISTANT/DA_IDENTITY.md'
        self.identity.write_text('---\nname: SyntheticScanName\n---\n# Synthetic assistant\n')
        self.projects = self.root / 'LIFEOS/USER/PROJECTS.md'
        self.projects.write_text('# Synthetic projects\nSynthetic project setup\n')
        self.env = self.root / '.env'
        self.env.write_text('SYNTHETIC_OPTIONAL_SETUP=ready\n')
        self.env.chmod(0o600)
        self.pulse = self.root / 'LIFEOS/PULSE/PULSE.toml'
        self.pulse.parent.mkdir()
        self.pulse.write_text('[synthetic]\nvoice = false\n')
        self.work = self.root / 'LIFEOS/USER/WORK/config.yaml'
        self.work.parent.mkdir()
        self.work.write_text('synthetic_config: ready\n')

    def call(self, *args, context=True):
        return subprocess.run(['bun', '--no-install', str(self.root / 'LIFEOS/TOOLS/InterviewScan.ts'), *args],
            env=self.fixture.fixture.environment(context=context), capture_output=True, text=True, timeout=60)

    def successful(self, *args):
        result = self.call(*args)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        return result

    def target(self, name):
        return json.loads(self.successful('--file', name).stdout)

    def test_owner_scan_keeps_native_json_and_output_modes(self):
        value = json.loads(self.successful('--json').stdout)
        self.assertEqual(value['count'], len(value['targets']))
        self.assertGreater(value['count'], 20)
        self.assertEqual(self.target('DA_IDENTITY')['content_length'], len(self.identity.read_text()))
        self.assertIn('Interview Gap Report', self.successful().stdout)
        self.assertIn('Questions for', self.successful('--next').stdout)
        self.assertFalse((self.root / 'LIFEOS/USER/CACHE').exists())

    def test_private_identity_cannot_influence_scoring(self):
        self.identity.write_text('<private>' + 'Synthetic private identity content ' * 30 + '</private>')
        value = self.target('DA_IDENTITY')
        self.assertEqual(value['content_length'], 0)
        self.assertEqual(value['completeness_score'], 0)

    def test_private_unified_telos_cannot_influence_scoring(self):
        (self.root / 'LIFEOS/USER/TELOS/TELOS.md').write_text('## Mission\n<private>' + 'Synthetic private mission ' * 30 + '</private>\n')
        self.assertEqual(self.target('Mission')['content_length'], 0)

    def test_foreign_identity_source_refuses_scoring(self):
        foreign = self.fixture.fixture.fixture.fixture.home / 'foreign-scan-identity.md'
        foreign.write_text('Synthetic foreign identity ' * 30)
        self.identity.unlink(); self.identity.symlink_to(foreign)
        self.assertNotEqual(self.call('--file', 'DA_IDENTITY').returncode, 0)

    def test_foreign_setup_sources_refuse_scoring(self):
        for path, name in ((self.env, '.env/credentials'), (self.pulse, 'PULSE.toml/voice'), (self.work, 'WORK/config')):
            with self.subTest(name=name):
                before = path.read_text()
                foreign = self.fixture.fixture.fixture.fixture.home / ('foreign-' + path.name)
                foreign.write_text('Synthetic foreign setup ' * 30)
                path.unlink(); path.symlink_to(foreign)
                result = self.call('--file', name)
                self.assertNotEqual(result.returncode, 0)
                path.unlink(); path.write_text(before)

    def test_old_identity_after_retirement_requires_exact_source_review(self):
        self.fixture.retire_work()
        self.assertEqual(self.target('DA_IDENTITY')['content_length'], 0)

    def test_missing_context_refuses_scoring(self):
        self.assertNotEqual(self.call('--json', context=False).returncode, 0)

    def test_read_only_owner_can_scan_without_publishing(self):
        self.fixture.fixture.fixture.configuration.update(lambda c: c['destinations']['chat-a:200'].update(write=[]))
        value = json.loads(self.successful('--json').stdout)
        self.assertGreater(value['count'], 20)
        self.assertFalse((self.root / 'LIFEOS/USER/CACHE').exists())

    def test_invalid_target_preserves_native_exit_status(self):
        result = self.call('--file', 'SyntheticUnsupportedTarget')
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, '')
        self.assertIn('Not found: SyntheticUnsupportedTarget', result.stderr)
