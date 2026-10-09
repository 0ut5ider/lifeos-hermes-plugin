# ABOUTME: Checks exact source identity and recovery around native Algorithm summary publication.
# ABOUTME: Preserves later owner edits and rejects invalid or excluded generated cache fields.
from dataclasses import asdict
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import unittest
import test_memory_algorithm_summary as fixture
from test_memory_native import OWNER


class MemoryAlgorithmSummaryEdgeTests(unittest.TestCase):
    setUp = fixture.MemoryAlgorithmSummaryTests.setUp
    call = fixture.MemoryAlgorithmSummaryTests.call
    prepare = fixture.MemoryAlgorithmSummaryTests.prepare
    value = fixture.MemoryAlgorithmSummaryTests.value

    def test_full_source_bytes_and_inode_replacement_invalidate_native_plan(self):
        for mode in ('bytes', 'inode'):
            with self.subTest(mode=mode):
                prepared = self.prepare()
                info = self.rules.stat()
                if mode == 'bytes':
                    content = self.rules.read_text().replace('SummarySource', 'SummaryChange')
                    self.rules.write_text(content)
                    os.utime(self.rules, ns=(info.st_atime_ns, info.st_mtime_ns))
                else:
                    replacement = self.rules.with_suffix('.replacement')
                    replacement.write_bytes(self.rules.read_bytes())
                    os.utime(replacement, ns=(info.st_atime_ns, info.st_mtime_ns))
                    replacement.replace(self.rules)
                self.assertFalse(self.call('algorithm_summary_check', signature=prepared['signature'])['ok'])
                self.assertFalse(self.cache.exists())

    def test_linked_invalid_utf8_and_oversized_cache_preserve_prior_bytes(self):
        self.cache.parent.mkdir(parents=True, exist_ok=True)
        for mode in ('symlink', 'hardlink', 'utf8', 'oversize'):
            with self.subTest(mode=mode):
                self.cache.unlink(missing_ok=True)
                outside = self.owner.fixture.home / 'synthetic-algorithm-cache'
                outside.write_text('{"overview":null,"files":{}}')
                if mode == 'symlink':
                    self.cache.symlink_to(outside)
                elif mode == 'hardlink':
                    os.link(outside, self.cache)
                elif mode == 'utf8':
                    self.cache.write_bytes(b'{"overview":null,"files":{}}\xff')
                else:
                    self.cache.write_text(' ' * (256 * 1024 + 1))
                before = self.cache.read_bytes()
                self.assertFalse(self.call('algorithm_summary_prepare')['ok'])
                self.assertEqual(self.cache.read_bytes(), before)

    def test_unknown_cards_invalid_timestamps_empty_output_and_wrong_overview_refuse(self):
        prepared = self.prepare()
        for mode in ('unknown', 'timestamp', 'naive', 'empty', 'overview'):
            with self.subTest(mode=mode):
                value = self.value(prepared)
                card = value['files']['operational-rules']
                if mode == 'unknown':
                    value['files']['undeclared'] = card
                elif mode == 'timestamp':
                    card['generated_at'] = 'not-a-time'
                elif mode == 'naive':
                    card['generated_at'] = '2026-10-09T12:00:00'
                elif mode == 'empty':
                    card['markdown'] = ' '
                else:
                    value['overview'] = {'generated_at': datetime.now(timezone.utc).isoformat(),
                        'chain_hash': '0' * 64, 'level': 'high', 'markdown': 'Synthetic overview.'}
                self.assertFalse(self.call('algorithm_summary_publish', signature=prepared['signature'], value=value)['ok'])
                self.assertFalse(self.cache.exists())

    def test_new_retirement_invalidates_the_prepared_signature(self):
        prepared = self.prepare()
        memory = self.owner.fixture.memory
        saved = memory.remember(OWNER, category='principal', content='SyntheticAlgorithmNewRetirement',
            title='Synthetic Algorithm retirement', project='', request_id='algorithm-new-retirement')
        memory.forget(OWNER, saved['reference'], 'algorithm-forget-new')
        self.assertFalse(self.call('algorithm_summary_publish', signature=prepared['signature'], value=self.value(prepared))['ok'])
        self.assertFalse(self.cache.exists())

    def test_actual_post_render_changes_and_process_death_preserve_recovery(self):
        original = self.rules.read_bytes()
        for mode in ('source', 'destination', 'authority', 'projection-source', 'projection-authority', 'interrupt'):
            with self.subTest(mode=mode):
                result = subprocess.run([os.environ.get('PYTHON', '/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python'),
                    str(Path(__file__).with_name('memory_algorithm_summary_process.py')), str(self.configuration.path), mode,
                    json.dumps(asdict(self.owner.context))], capture_output=True, text=True, timeout=60)
                self.assertEqual(result.stderr, '')
                if mode == 'interrupt':
                    self.assertEqual(result.returncode, 73, result.stdout)
                    self.assertTrue(self.cache.exists())
                    self.prepare()
                    self.assertFalse(self.cache.exists())
                else:
                    self.assertEqual(result.returncode, 0, result.stdout)
                    self.assertFalse(json.loads(result.stdout)['ok'])
                    if mode == 'destination':
                        self.assertEqual(self.cache.read_text(), '{"overview":null,"files":{}}')
                        self.cache.unlink()
                    else:
                        self.assertFalse(self.cache.exists())
                self.rules.write_bytes(original)
                if mode.endswith('authority'):
                    self.configuration.update(lambda value: value['accounts'].update({'chat-a:100': 'owner'}))

    def test_recovery_preserves_later_owner_cache_after_actual_process_death(self):
        self.cache.parent.mkdir(parents=True, exist_ok=True)
        prior = '{"overview":null,"files":{}}'
        self.cache.write_text(prior)
        result = subprocess.run([os.environ.get('PYTHON', '/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python'),
            str(Path(__file__).with_name('memory_algorithm_summary_process.py')), str(self.configuration.path), 'interrupt',
            json.dumps(asdict(self.owner.context))], capture_output=True, text=True, timeout=60)
        self.assertEqual((result.returncode, result.stderr), (73, ''), result.stdout)
        later = '{"overview": null, "files": {}}\n'
        self.cache.write_text(later)
        recovered = self.call('algorithm_summary_prepare')
        self.assertFalse(recovered['ok'], recovered)
        self.assertIn('preserves a later artifact edit', recovered['message'])
        self.assertEqual(self.cache.read_text(), later)
