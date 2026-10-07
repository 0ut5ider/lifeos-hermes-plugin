# ABOUTME: Characterizes native private-token derivation with synthetic source and output files.
# ABOUTME: Checks managed owner admission before source disclosure or hash and salt publication.
import json
from pathlib import Path
import subprocess
import unittest

import test_memory_delegation as delegation_fixture


class MemoryDenyHashesTests(unittest.TestCase):
    def setUp(self):
        self.fixture = delegation_fixture.MemoryDelegationTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        self.identity = self.root / 'LIFEOS/USER/PRINCIPAL/PRINCIPAL_IDENTITY.md'
        self.identity.write_text('# Synthetic principal\nFixtureSurname FixtureGivenname\n')
        self.output = self.root / 'LIFEOS/USER/SECURITY/DENY_HASHES.json'
        self.env = self.root / '.env'
        self.env.write_text('SYNTHETIC_KEEP=fixture\n')
        (self.root / 'skills/_LIFEOS').mkdir(parents=True)

    def call(self, *args, context=True):
        import os
        environment = dict(os.environ, HOME=str(self.fixture.fixture.home), BUN_CONFIG_NO_AUTO_INSTALL='1')
        environment.pop('LIFEOS_MEMORY_INTERNAL', None)
        environment.pop('LIFEOS_MEMORY_CONTEXT', None)
        if context:
            from dataclasses import asdict
            environment['LIFEOS_MEMORY_CONTEXT'] = json.dumps(asdict(self.fixture.context))
        return subprocess.run(['bun', '--no-install', str(self.root / 'LIFEOS/TOOLS/DeriveDenyHashes.ts'), *args],
            env=environment, capture_output=True, text=True, timeout=40)

    def successful(self, *args):
        result = self.call(*args)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        return result

    def test_owner_retains_native_token_extraction_and_hash_payload(self):
        result = self.successful('--dry-run', '--show-tokens')
        self.assertIn('fixturesurname fixturegivenname', result.stdout)
        self.assertFalse(self.output.exists())
        before = self.env.read_bytes()
        result = self.successful()
        self.assertNotIn('fixturesurname fixturegivenname', result.stdout)
        self.assertTrue(self.env.read_bytes().startswith(before))
        payload = json.loads(self.output.read_text())
        self.assertEqual(payload['version'], 1)
        self.assertEqual(payload['algo'], 'sha256-salted-trunc24')
        self.assertEqual(payload['count'], len(payload['hashes']))
        self.assertTrue(payload['hashes'])
        self.assertTrue(all(len(value) == 24 for value in payload['hashes']))
        before = (self.env.read_bytes(), self.output.read_bytes())
        self.successful()
        self.assertEqual((self.env.read_bytes(), self.output.read_bytes()), before)

    def test_missing_context_cannot_show_tokens_or_publish(self):
        before = self.env.read_bytes()
        self.assertNotEqual(self.call('--dry-run', '--show-tokens', context=False).returncode, 0)
        self.assertNotIn('fixturesurname fixturegivenname', self.call('--show-tokens', context=False).stdout)
        self.assertEqual(self.env.read_bytes(), before)
        self.assertFalse(self.output.exists())

    def test_read_only_owner_can_review_without_hash_or_salt_writes(self):
        self.fixture.configuration.update(lambda value: value['destinations']['chat-a:200'].update(write=[]))
        before = self.env.read_bytes()
        self.successful('--dry-run')
        self.assertNotEqual(self.call().returncode, 0)
        self.assertEqual(self.env.read_bytes(), before)
        self.assertFalse(self.output.exists())

    def test_private_source_cannot_reach_token_review(self):
        self.identity.write_text('# Synthetic principal\n<private>FixtureSurname FixtureGivenname</private>\n')
        self.assertNotIn('fixturesurname fixturegivenname', self.call('--dry-run', '--show-tokens').stdout)

    def test_foreign_source_path_refuses_without_output(self):
        foreign = self.fixture.fixture.home / 'foreign-deny-source.md'
        foreign.write_text('ForeignFixtureSurname ForeignFixtureGivenname\n')
        self.identity.unlink(); self.identity.symlink_to(foreign)
        result = self.call('--show-tokens')
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('foreignfixturesurname foreignfixturegivenname', result.stdout)
        self.assertFalse(self.output.exists())
        self.assertEqual(self.env.read_text(), 'SYNTHETIC_KEEP=fixture\n')

    def test_hash_and_salt_publication_have_private_permissions(self):
        self.successful()
        self.assertEqual(self.env.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.output.stat().st_mode & 0o777, 0o600)

    def test_public_install_skip_retains_environment_and_creates_no_marker(self):
        (self.root / 'skills/_LIFEOS').rmdir()
        before = self.env.read_bytes()
        self.assertIn('skipping hash write', self.successful().stdout)
        self.assertFalse(self.output.exists())
        self.assertEqual(self.env.read_bytes(), before)
        self.assertFalse((self.root / 'skills/_LIFEOS').exists())
