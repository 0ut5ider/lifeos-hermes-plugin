# ABOUTME: Exercises native thinking-chain summary plans and private incremental cache publication.
# ABOUTME: Refuses changed sources, revoked writers, and generated text excluded by owner policy.
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import unittest
import test_memory_manual_state as fixture
from lifeos_hook_bridge.memory_service import MemoryService

CACHE = 'LIFEOS/MEMORY/STATE/algorithm-tab-summary.json'
RULES = 'LIFEOS/USER/CONFIG/OPERATIONAL_RULES.md'


class MemoryAlgorithmSummaryTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixture.MemoryManualStateTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.owner = self.fixture.fixture
        self.root = self.fixture.root
        self.configuration = self.owner.configuration
        self.service = MemoryService(self.configuration)
        source = Path(os.environ['LIFEOS_MEMORY_SOURCE'])
        (self.root / 'LIFEOS/PULSE').symlink_to(source / 'LIFEOS/PULSE')
        hooks = self.root / 'hooks'
        if hooks.is_symlink():
            public = hooks.resolve()
            hooks.unlink()
            shutil.copytree(public, hooks)
        algorithm = self.root / 'LIFEOS/ALGORITHM'
        algorithm.mkdir()
        (algorithm / 'LATEST').write_text('3.2.1\n')
        (algorithm / 'v3.2.1.md').write_text('# The Algorithm 3.2.1\n\nSynthetic doctrine explanation.\n')
        (algorithm / 'changelog.md').write_text('# Synthetic algorithm history\n')
        self.rules = self.root / RULES
        self.rules.write_text('# Synthetic operating rules\n\nSyntheticAlgorithmSummarySource.\n')
        self.cache = self.root / CACHE

    def call(self, operation, **arguments):
        return self.service.native(self.owner.context, operation, arguments)

    def prepare(self):
        result = self.call('algorithm_summary_prepare')
        self.assertTrue(result['ok'], result)
        return result

    def value(self, prepared):
        plan = prepared['plan']
        value = json.loads(json.dumps(plan['store']))
        card = next(row for row in plan['files'] if row['id'] == 'operational-rules')
        value['files'][card['id']] = {'hash': card['hash'], 'generated_at': datetime.now(timezone.utc).isoformat(),
            'markdown': 'Synthetic explanation of the current operating rules.'}
        return value

    def test_native_plan_preserves_complete_source_hashes_and_native_levels(self):
        prepared = self.prepare()
        plan = prepared['plan']
        card = next(row for row in plan['files'] if row['id'] == 'operational-rules')
        self.assertEqual(card['hash'], hashlib.sha256(self.rules.read_bytes()).hexdigest())
        self.assertIn('SyntheticAlgorithmSummarySource', card['user'])
        self.assertEqual(card['level'], 'low')
        self.assertEqual(plan['overview']['level'], 'high')
        self.assertIn('SyntheticAlgorithmSummarySource', plan['overview']['user'])
        self.assertEqual(plan['store'], {'overview': None, 'files': {}})
        self.assertFalse(self.cache.exists())

    def test_incremental_native_cache_is_private_and_returns_next_signature(self):
        prepared = self.prepare()
        value = self.value(prepared)
        result = self.call('algorithm_summary_publish', signature=prepared['signature'], value=value)
        self.assertTrue(result['ok'], result)
        self.assertEqual(json.loads(self.cache.read_text()), value)
        self.assertEqual(self.cache.stat().st_mode & 0o777, 0o600)
        self.assertNotEqual(result['signature'], prepared['signature'])
        self.assertTrue(self.call('algorithm_summary_check', signature=result['signature'])['ok'])
        self.assertFalse(self.call('algorithm_summary_check', signature=prepared['signature'])['ok'])

    def test_wrong_hash_private_output_and_removed_cards_cannot_replace_cache(self):
        prepared = self.prepare()
        value = self.value(prepared)
        for change in ('hash', 'private', 'extra'):
            candidate = json.loads(json.dumps(value))
            if change == 'hash': candidate['files']['operational-rules']['hash'] = '0' * 64
            elif change == 'private': candidate['files']['operational-rules']['markdown'] = '<private>SyntheticHiddenSummary</private>'
            else: candidate['files']['operational-rules']['extra'] = 'undeclared'
            result = self.call('algorithm_summary_publish', signature=prepared['signature'], value=candidate)
            self.assertFalse(result['ok'], result)
            self.assertFalse(self.cache.exists())
        result = self.call('algorithm_summary_publish', signature=prepared['signature'], value=value)
        self.assertTrue(result['ok'], result)
        before = self.cache.read_bytes()
        self.assertFalse(self.call('algorithm_summary_publish', signature=result['signature'],
            value={'overview': None, 'files': {}})['ok'])
        self.assertEqual(self.cache.read_bytes(), before)

    def test_source_metadata_private_source_and_read_only_permission_refuse(self):
        prepared = self.prepare()
        info = self.rules.stat()
        os.utime(self.rules, ns=(info.st_atime_ns, info.st_mtime_ns + 1000000))
        self.assertFalse(self.call('algorithm_summary_check', signature=prepared['signature'])['ok'])
        self.rules.write_text('<private>SyntheticAlgorithmHidden</private>')
        self.assertFalse(self.call('algorithm_summary_prepare')['ok'])
        self.rules.write_text('Synthetic safe rules')
        self.configuration.update(lambda value: value['destinations']['chat-a:200'].update(write=[]))
        self.assertFalse(self.call('algorithm_summary_prepare')['ok'])
        self.assertFalse(self.cache.exists())
