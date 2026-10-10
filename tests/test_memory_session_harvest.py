# ABOUTME: Exercises session consolidation against admitted synthetic Hermes transcripts.
# ABOUTME: Verifies owner permissions, private capture boundaries, and retained-content retirement.
from dataclasses import asdict
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unittest

import test_memory_delegation as delegation
from test_memory_native import OWNER
from lifeos_hook_bridge.memory_runtime import MemoryRuntime
from lifeos_hook_bridge.memory_transaction import publish


class MemorySessionHarvestTests(unittest.TestCase):
    def setUp(self):
        self.fixture = delegation.MemoryDelegationTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        self.transcripts = self.root / 'LIFEOS/MEMORY/STATE/hermes-transcripts'
        self.transcripts.mkdir(parents=True, mode=0o700)
        self.context = self.fixture.context
        self.session = self.context.session_id
        self.transcript = self.transcripts / (self.session + '.jsonl')
        self.content = 'Actually, I meant to use the synthetic safe port for this lab.'
        self.write_transcript(self.content)
        runtime = MemoryRuntime(self.fixture.configuration.path)
        with self.fixture.fixture.memory._transaction() as connection:
            state = runtime._stamp(self.fixture.configuration.load(), self.context, connection)
        publish(runtime.state_path, json.dumps({self.session:state}).encode())

    def write_transcript(self, content):
        row = {'type':'user','sessionId':self.session,'timestamp':'2026-10-08T12:00:00+00:00',
               'message':{'role':'user','content':content}}
        publish(self.transcript, (json.dumps(row) + '\n').encode())

    def call(self, *flags, context=True):
        environment = dict(os.environ, HOME=str(self.fixture.fixture.home), BUN_CONFIG_NO_AUTO_INSTALL='1')
        environment.pop('LIFEOS_MEMORY_INTERNAL', None)
        environment.pop('LIFEOS_MEMORY_CONTEXT', None)
        if context:
            environment['LIFEOS_MEMORY_CONTEXT'] = json.dumps(asdict(self.context))
        return subprocess.run(['bun', '--no-install', str(self.root / 'LIFEOS/TOOLS/SessionHarvester.ts'), *flags],
            env=environment, capture_output=True, text=True, timeout=40)

    def notes(self):
        return sorted((self.root / 'LIFEOS/MEMORY/LEARNING').rglob('*.md'))

    def test_unmanaged_claude_transcript_keeps_native_extraction(self):
        (self.root / 'LIFEOS/USER/CONFIG/memory-access.json').unlink()
        slug = str(self.root).replace('/', '-').replace('.', '-')
        projects = self.root / 'projects' / slug
        projects.mkdir(parents=True)
        shutil.copyfile(self.transcript, projects / self.transcript.name)
        result = self.call('--recent', '20', context=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Harvested 1 learning', result.stdout)
        self.assertIn(self.content, self.notes()[0].read_text())

    def test_managed_default_harvests_hermes_transcripts_privately(self):
        result = self.call('--recent', '20')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(self.notes()), 1)
        text = self.notes()[0].read_text()
        self.assertIn(self.content, text)
        self.assertIn('source=hermes', text)
        self.assertEqual(self.notes()[0].stat().st_mode & 0o777, 0o600)

    def test_missing_context_refuses_before_native_processing(self):
        result = self.call('--recent', '20', context=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn(self.content, result.stdout)
        self.assertEqual(self.notes(), [])

    def test_revoked_owner_refuses_session_consolidation(self):
        self.fixture.configuration.update(lambda value: value['accounts'].pop('chat-a:100'))
        result = self.call('--recent', '20')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.notes(), [])

    def test_unknown_transcript_without_admitted_session_is_not_harvested(self):
        publish(self.fixture.configuration.path.parent / 'lifeos-memory-contexts.json', b'{}')
        result = self.call('--recent', '20')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.notes(), [])

    def test_dry_run_preserves_memory(self):
        result = self.call('--recent', '20', '--dry-run')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('1', result.stdout)
        self.assertEqual(self.notes(), [])

    def test_private_capture_span_never_reaches_a_learning_file(self):
        self.write_transcript(self.content + ' <private>Synthetic withheld token marker</private>')
        result = self.call('--recent', '20')
        self.assertEqual(result.returncode, 0, result.stderr)
        text = self.notes()[0].read_text()
        self.assertIn(self.content, text)
        self.assertNotIn('Synthetic withheld token marker', text)

    def test_retired_history_cannot_reappear_as_a_learning(self):
        memory = self.fixture.fixture.memory
        saved = memory.remember(OWNER, category='principal', content='RULE: synthetic safe port',
            title='', project='', request_id='harvest-retired')
        memory.forget(OWNER, saved['reference'], 'harvest-forget')
        result = self.call('--recent', '20')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.notes(), [])

    def test_repeated_consolidation_preserves_the_same_file_and_operation(self):
        first = self.call('--recent', '20')
        self.assertEqual(first.returncode, 0, first.stderr)
        files = self.notes()
        before = [(path.read_bytes(), path.stat().st_mtime_ns) for path in files]
        again = self.call('--recent', '20')
        self.assertEqual(again.returncode, 0, again.stderr)
        self.assertEqual(self.notes(), files)
        self.assertEqual([(path.read_bytes(), path.stat().st_mtime_ns) for path in files], before)

    def test_mining_writes_one_private_candidate_with_hermes_provenance(self):
        self.write_transcript('We decided to use the synthetic safe port. The decision is to keep that port for the lab service.')
        result = self.call('--mine', '--recent', '20')
        self.assertEqual(result.returncode, 0, result.stderr)
        queue = sorted((self.root / 'LIFEOS/MEMORY/KNOWLEDGE/_harvest-queue').glob('*.json'))
        self.assertEqual(len(queue), 1)
        self.assertEqual(json.loads(queue[0].read_text())['provenance']['source'], 'hermes')
        self.assertEqual(queue[0].stat().st_mode & 0o777, 0o600)
        again = self.call('--mine', '--recent', '20')
        self.assertEqual(again.returncode, 0, again.stderr)
        self.assertEqual(sorted(queue[0].parent.glob('*.json')), queue)

    def test_unmanaged_mining_keeps_native_candidate_provenance(self):
        (self.root / 'LIFEOS/USER/CONFIG/memory-access.json').unlink()
        self.write_transcript('We decided to use the synthetic safe port. The decision is to keep that port for the lab service.')
        slug = str(self.root).replace('/', '-').replace('.', '-')
        projects = self.root / 'projects' / slug
        projects.mkdir(parents=True)
        shutil.copyfile(self.transcript, projects / self.transcript.name)
        result = self.call('--mine', '--recent', '20', context=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        queue = sorted((self.root / 'LIFEOS/MEMORY/KNOWLEDGE/_harvest-queue').glob('*.json'))
        self.assertEqual(len(queue), 1)
        self.assertEqual(json.loads(queue[0].read_text())['provenance']['source'], 'claude')

    def test_restricted_owner_write_grant_refuses_consolidation(self):
        self.fixture.configuration.update(lambda value: value['destinations']['chat-a:200'].update(write=['project']))
        result = self.call('--recent', '20')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.notes(), [])

    def test_arbitrary_archive_override_refuses_without_reading_the_archive(self):
        result = self.call('--projects-dir', str(self.fixture.fixture.home / 'foreign-archive'))
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.notes(), [])

    def test_transcript_symbolic_link_refuses_before_consolidation(self):
        foreign = self.fixture.fixture.home / 'foreign-transcript.jsonl'
        foreign.write_bytes(self.transcript.read_bytes())
        self.transcript.unlink()
        self.transcript.symlink_to(foreign)
        result = self.call('--recent', '20')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.notes(), [])

    def process(self, mode):
        return subprocess.run([sys.executable, str(Path(__file__).with_name('memory_session_harvest_process.py')),
            str(self.fixture.configuration.path), mode], env=dict(os.environ, HOME=str(self.fixture.fixture.home),
                PYTHONPATH=str(Path(__file__).resolve().parents[1])), capture_output=True, text=True, timeout=40)

    def test_source_change_after_native_render_refuses_publication(self):
        result = self.process('source')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(json.loads(result.stdout)['ok'])
        self.assertEqual(self.notes(), [])

    def test_owner_revocation_after_native_render_refuses_publication(self):
        result = self.process('authority')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(json.loads(result.stdout)['ok'])
        self.assertEqual(self.notes(), [])

    def test_process_death_recovers_before_fresh_consolidation(self):
        result = self.process('interrupt')
        self.assertEqual(result.returncode, 73, result.stderr)
        self.assertEqual(len(self.notes()), 1)
        memory = self.fixture.fixture.memory
        self.assertTrue(memory.transaction.journal.exists())
        with memory._transaction():
            self.assertEqual(self.notes(), [])
        self.assertFalse(memory.transaction.journal.exists())
        fresh = self.call('--recent', '20')
        self.assertEqual(fresh.returncode, 0, fresh.stderr)
        self.assertEqual(len(self.notes()), 1)
