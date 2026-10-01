# ABOUTME: Checks governed Cortex evidence without losing native health decisions.
# ABOUTME: Runs real collectors and assessments against isolated reviewer diagnostics.

from dataclasses import asdict
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import unittest

import test_memory_delegation as delegation_fixture
from test_memory_native import OWNER


class MemoryCortexHealthTests(unittest.TestCase):
    def setUp(self):
        self.fixture = delegation_fixture.MemoryDelegationTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        self.obs = self.root / 'LIFEOS/MEMORY/OBSERVABILITY'
        self.obs.mkdir(parents=True, exist_ok=True)
        self.now = datetime.now(timezone.utc).isoformat()

    def reviewer(self, error):
        (self.obs / 'reviewer-runs.jsonl').write_text(json.dumps({'ts': self.now, 'ok': False,
            'parse_ok': False, 'runId': '2026-09-30T23-55-00-000Z', 'error': error}) + '\n')

    def call(self, *, context=True, root=None):
        source = str(self.root / 'LIFEOS/TOOLS/CortexHealth.ts')
        code = ('const m=await import(' + json.dumps(source) + '); try {'
                'const evidence=m.collectCortexEvidence({root:' + json.dumps(str(root or self.root)) + '});'
                'console.log(JSON.stringify({evidence, assessment:m.assessCortexEvidence(evidence)}));'
                '} catch {console.log(JSON.stringify({unavailable:true}));}')
        environment = dict(os.environ, HOME=str(self.fixture.fixture.home), BUN_CONFIG_NO_AUTO_INSTALL='1')
        environment.pop('LIFEOS_MEMORY_INTERNAL', None)
        environment.pop('LIFEOS_MEMORY_CONTEXT', None)
        if context:
            environment['LIFEOS_MEMORY_CONTEXT'] = json.dumps(asdict(self.fixture.context))
        result = subprocess.run(['bun', '--no-install', '-e', code], env=environment, cwd=self.root,
                                capture_output=True, text=True, timeout=45)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        return json.loads(result.stdout)

    def test_owner_failed_reviewer_remains_critical_and_preserves_current_error(self):
        self.reviewer('Synthetic current parse failure')
        result = self.call()
        self.assertEqual(result['evidence']['reviewer']['status'], 'parse-failed')
        self.assertEqual(result['assessment']['overall'], 'critical')
        self.assertIn('Synthetic current parse failure', json.dumps(result))

    def test_unmanaged_reviewer_retains_native_error(self):
        (self.root / 'LIFEOS/USER/CONFIG/memory-access.json').unlink()
        self.reviewer('Synthetic unmanaged Cortex error')
        self.assertIn('Synthetic unmanaged Cortex error', json.dumps(self.call(context=False)))

    def test_missing_context_refuses_all_cortex_evidence(self):
        self.reviewer('Synthetic private Cortex error')
        self.assertEqual(self.call(context=False), {'unavailable': True})

    def test_retired_error_is_excluded_without_losing_critical_status(self):
        saved = self.fixture.fixture.remember('RULE: Synthetic retired Cortex error', 'cortex', 'principal')
        self.fixture.fixture.memory.forget(OWNER, saved['reference'], 'forget-cortex')
        self.now = datetime.now(timezone.utc).isoformat()
        self.reviewer('Synthetic retired Cortex error')
        result = self.call()
        self.assertNotIn('Synthetic retired Cortex error', json.dumps(result))
        self.assertEqual(result['evidence']['reviewer']['status'], 'parse-failed')
        self.assertEqual(result['assessment']['overall'], 'critical')

    def test_malformed_reviewer_preserves_parse_failure_and_line_numbers(self):
        self.reviewer('Synthetic valid predecessor')
        with (self.obs / 'reviewer-runs.jsonl').open('a') as stream:
            stream.write('{malformed\n')
        result = self.call()
        self.assertEqual(result['evidence']['reviewer']['status'], 'parse-failed')
        self.assertIn('malformed JSONL lines: 2', json.dumps(result))
        self.assertEqual(result['assessment']['overall'], 'critical')

    def test_explicit_other_root_cannot_bypass_managed_memory(self):
        self.reviewer('Synthetic bound Cortex error')
        other = self.fixture.fixture.home / 'other'
        (other / 'LIFEOS/MEMORY/OBSERVABILITY').mkdir(parents=True)
        (other / 'LIFEOS/MEMORY/OBSERVABILITY/reviewer-runs.jsonl').write_text(json.dumps(
            {'ts': self.now, 'ok': False, 'error': 'Synthetic alternate root error'}) + '\n')
        self.assertEqual(self.call(root=other), {'unavailable': True})

    def test_reviewer_redirect_cannot_read_configuration(self):
        secret = self.root / 'LIFEOS/USER/CONFIG/synthetic-cortex-secret.json'
        secret.write_text(json.dumps({'ts': self.now, 'ok': False, 'error': 'Synthetic Cortex secret'}) + '\n')
        (self.obs / 'reviewer-runs.jsonl').symlink_to(secret)
        self.assertEqual(self.call(), {'unavailable': True})
