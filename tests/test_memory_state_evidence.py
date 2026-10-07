# ABOUTME: Characterizes native state evidence reads, cache writes, and JSON source boundaries.
# ABOUTME: Uses synthetic domain inputs without configuring external integrations.
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

import test_memory_freshness as freshness_fixture
from test_memory_native import OWNER
from lifeos_hook_bridge.memory_source_review import preview, approve


class MemoryStateEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.fixture = freshness_fixture.MemoryFreshnessTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        self.cache = self.root / 'LIFEOS/USER/CACHE/state-evidence.json'
        self.day = datetime.now(timezone.utc).date().isoformat()
        self.source('LIFEOS/USER/HEALTH/DATA/oura/' + self.day + '.json',
            {'metrics': {'sleep_duration_h': 7.5, 'steps': 321}})
        self.source('LIFEOS/USER/HEALTH/current.json',
            {'sources': {'apple': {'status': 'SYNTHETIC_CURRENT_SOURCE_NOTE'}}})
        self.source('LIFEOS/USER/CONDUIT/daily/' + self.day + '.json',
            {'totalMinutes': 60, 'creationMinutes': 20,
             'blocks': [{'label': 'Synthetic editor', 'minutes': 20}]})
        self.work = self.source('LIFEOS/MEMORY/STATE/work.json',
            {'sessions': {'synthetic': {'sessionName': 'Synthetic Current Work',
                                      'phase': 'BUILD', 'updatedAt': self.day + 'T00:00:00Z'}}})
        self.source('LIFEOS/USER/FINANCES/expenses.json',
            {'meta': {'updated': self.day}, 'subscriptions': [
                {'cycle': 'monthly', 'amount': 12, 'status': 'active'},
                {'cycle': 'annual', 'amount': 120, 'status': 'active'}]})

    def source(self, relative, value):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value))
        return path

    def call(self, *args, context=True):
        return subprocess.run(['bun', '--no-install', str(self.root / 'LIFEOS/TOOLS/StateEvidence.ts'), *args],
            env=self.fixture.environment(context=context), capture_output=True, text=True, timeout=30)

    def successful(self, *args):
        result = self.call(*args)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        return result

    def library(self, function, *args, context=True):
        program = 'const m=await import(process.argv[1]);console.log(JSON.stringify(m[process.argv[2]](...JSON.parse(process.argv[3]))));'
        return subprocess.run(['bun', '--no-install', '-e', program, str(self.root / 'LIFEOS/TOOLS/StateEvidence.ts'),
            function, json.dumps(args)], env=self.fixture.environment(context=context),
            capture_output=True, text=True, timeout=30)

    def previous(self):
        self.cache.parent.mkdir(parents=True, exist_ok=True)
        self.cache.write_text('{"synthetic_previous":"preserved"}')
        return self.cache.read_bytes()

    def test_owner_preserves_native_domain_metrics_and_source_notes(self):
        health = json.loads(self.successful('--domain', 'health').stdout)
        self.assertEqual(health['metrics']['sleep_h_avg_7d'], 7.5)
        self.assertEqual(health['metrics']['steps_avg_30d'], 321)
        self.assertEqual(next(s for s in health['sources'] if s['id'] == 'apple')['reason'],
                         'SYNTHETIC_CURRENT_SOURCE_NOTE')
        activity = json.loads(self.successful('--domain', 'activity').stdout)
        self.assertEqual(activity['metrics']['creation_ratio_7d'], 0.333)
        self.assertEqual(activity['metrics']['top_apps_7d'], [{'label': 'Synthetic editor', 'minutes': 20}])
        work = json.loads(self.successful('--domain', 'work').stdout)
        self.assertEqual(work['metrics']['recent_session_names'], ['Synthetic Current Work'])
        money = json.loads(self.successful('--domain', 'money').stdout)
        self.assertEqual(money['metrics']['monthly_recurring_total'], 22)
        self.assertFalse(self.cache.parent.exists())

    def test_cli_payload_matches_the_published_cache(self):
        payload = json.loads(self.successful('--json').stdout)
        self.assertEqual(payload, json.loads(self.cache.read_text()))
        self.assertEqual(set(payload['domains']), {'health', 'activity', 'work', 'money'})

    def test_missing_context_refuses_all_domain_reads(self):
        for domain in ('health', 'activity', 'work', 'money'):
            with self.subTest(domain=domain):
                result = self.call('--domain', domain, context=False)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn('SYNTHETIC_CURRENT_SOURCE_NOTE', result.stdout)
                self.assertNotIn('Synthetic Current Work', result.stdout)
        self.assertFalse(self.cache.parent.exists())

    def test_missing_context_does_not_create_the_cache_directory(self):
        result = self.call(context=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.cache.parent.exists())

    def test_read_only_owner_can_read_without_replacing_previous_cache(self):
        before = self.previous()
        self.fixture.fixture.configuration.update(lambda c: c['destinations']['chat-a:200'].update(write=[]))
        payload = json.loads(self.successful('--json').stdout)
        self.assertEqual(payload['domains']['money']['metrics']['monthly_recurring_total'], 22)
        self.assertEqual(self.cache.read_bytes(), before)

    def test_revoked_owner_cannot_read_source_notes(self):
        self.fixture.fixture.configuration.update(lambda c: c['accounts'].pop('chat-a:100'))
        result = self.call('--domain', 'health')
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('SYNTHETIC_CURRENT_SOURCE_NOTE', result.stdout)

    def retire_work(self):
        memory = self.fixture.memory
        saved = memory.remember(OWNER, category='principal', content='RULE: Synthetic retired evidence work',
            title='', project='', request_id='evidence-retired')
        self.source('LIFEOS/MEMORY/STATE/work.json', {'sessions': {'synthetic': {
            'sessionName': 'Synthetic retired evidence work', 'updatedAt': self.day + 'T00:00:00Z'}}})
        memory.forget(OWNER, saved['reference'], 'evidence-forget')

    def test_retired_work_name_does_not_reach_current_metrics(self):
        self.retire_work()
        result = self.successful('--domain', 'work')
        self.assertNotIn('Synthetic retired evidence work', result.stdout)
        self.assertEqual(json.loads(result.stdout)['metrics']['recent_session_names'], [])

    def test_foreign_source_link_refuses_without_disclosing_foreign_note(self):
        target = self.root / 'LIFEOS/USER/HEALTH/current.json'
        foreign = self.fixture.fixture.fixture.home / 'foreign-health-source.json'
        foreign.write_text('{"sources":{"apple":{"note":"SYNTHETIC_FOREIGN_SOURCE_NOTE"}}}')
        target.unlink(); target.symlink_to(foreign)
        result = self.call('--domain', 'health')
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('SYNTHETIC_FOREIGN_SOURCE_NOTE', result.stdout)

    def test_successful_cache_has_private_permissions(self):
        self.successful('--json')
        self.assertEqual(self.cache.stat().st_mode & 0o777, 0o600)

    def test_foreign_cache_directory_preserves_foreign_bytes(self):
        foreign = self.fixture.fixture.fixture.home / 'foreign-evidence-cache'
        foreign.mkdir()
        path = foreign / 'state-evidence.json'
        path.write_text('{"synthetic_foreign":"preserved"}')
        self.cache.parent.symlink_to(foreign)
        self.call('--json')
        self.assertEqual(path.read_text(), '{"synthetic_foreign":"preserved"}')

    def test_write_library_cannot_publish_to_an_arbitrary_path(self):
        foreign = self.fixture.fixture.fixture.home / 'foreign-evidence-output.json'
        payload = {'schema': 1, 'generated_at': self.day + 'T00:00:00Z',
                   'domains': {d: {'metrics': {}, 'sources': []} for d in ('health', 'activity', 'work', 'money')}}
        result = self.library('writeEvidenceCache', payload, str(foreign))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), False)
        self.assertFalse(foreign.exists())

    def test_stale_file_cache_cannot_restore_a_retired_work_name(self):
        self.source('LIFEOS/MEMORY/STATE/work.json', {'sessions': {'synthetic': {
            'sessionName': 'Synthetic retired evidence work', 'updatedAt': self.day + 'T00:00:00Z'}}})
        self.successful('--json')
        self.assertIn('Synthetic retired evidence work', self.cache.read_text())
        self.retire_work()
        result = self.library('readEvidenceCache')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn('Synthetic retired evidence work', result.stdout)

    def test_json_escaped_private_markup_cannot_reach_source_notes(self):
        path = self.root / 'LIFEOS/USER/HEALTH/current.json'
        path.write_text('{"sources":{"apple":{"status":"\\u003cprivate\\u003eSYNTHETIC_ESCAPED_PRIVATE\\u003c/private\\u003e"}}}')
        result = self.successful('--domain', 'health')
        self.assertNotIn('SYNTHETIC_ESCAPED_PRIVATE', result.stdout)

    def test_json_escaped_retired_name_cannot_reach_current_metrics(self):
        self.retire_work()
        self.work.write_text('{"sessions":{"synthetic":{"sessionName":"\\u0053ynthetic retired evidence work",'
            '"updatedAt":"' + self.day + 'T00:00:00Z"}}}')
        result = self.successful('--domain', 'work')
        self.assertNotIn('Synthetic retired evidence work', result.stdout)

    def process(self, mode, operation='state_evidence_cache_write'):
        result = subprocess.run([sys.executable, str(Path(__file__).with_name('memory_evidence_process.py')),
            str(self.fixture.fixture.configuration.path), mode, operation, 'LIFEOS/USER/HEALTH/current.json'],
            env=self.fixture.environment(), capture_output=True, text=True, timeout=30)
        self.assertEqual(result.stderr, '')
        return result

    def test_source_and_authority_changes_during_read_refuse_delivery(self):
        for mode in ('source', 'authority'):
            with self.subTest(mode=mode):
                result = self.process(mode, 'state_evidence_read')
                self.assertEqual(result.returncode, 0)
                self.assertFalse(json.loads(result.stdout)['ok'])
                self.assertNotIn('SYNTHETIC_CURRENT_SOURCE_NOTE', result.stdout)
                self.assertFalse(self.cache.exists())

    def test_source_change_and_exclusion_preserve_previous_cache_and_later_input(self):
        for mode in ('source', 'source_excluded'):
            with self.subTest(mode=mode):
                before = self.previous()
                result = self.process(mode)
                self.assertEqual(result.returncode, 0)
                self.assertFalse(json.loads(result.stdout)['ok'])
                with self.fixture.memory._transaction():
                    self.assertEqual(self.cache.read_bytes(), before)
                self.assertIn('Synthetic later', (self.root / 'LIFEOS/USER/HEALTH/current.json').read_text())
                self.source('LIFEOS/USER/HEALTH/current.json', {'sources': {}})

    def test_authority_change_preserves_previous_cache(self):
        before = self.previous()
        result = self.process('authority')
        self.assertEqual(result.returncode, 0)
        self.assertFalse(json.loads(result.stdout)['ok'])
        with self.fixture.memory._transaction():
            self.assertEqual(self.cache.read_bytes(), before)

    def test_interrupted_cache_recovers_previous_bytes_or_removes_first_publication(self):
        for existing in (False, True):
            with self.subTest(existing=existing):
                before = self.previous() if existing else None
                result = self.process('interrupt')
                self.assertEqual(result.returncode, 73)
                self.assertTrue(self.cache.exists())
                self.assertTrue(self.fixture.memory.transaction.journal.exists())
                with self.fixture.memory._transaction():
                    if existing:
                        self.assertEqual(self.cache.read_bytes(), before)
                    else:
                        self.assertFalse(self.cache.exists())
                self.assertFalse(self.fixture.memory.transaction.journal.exists())

    def test_source_and_cache_cannot_alias_the_registry(self):
        self.fixture.fixture.fixture.remember('Synthetic evidence registry guard', 'evidence-alias')
        for target in (self.work, self.cache):
            with self.subTest(target=target):
                if target.exists():
                    target.unlink()
                target.parent.mkdir(parents=True, exist_ok=True)
                os.link(self.fixture.memory.database, target)
                result = self.call('--json')
                if target == self.work:
                    self.assertNotEqual(result.returncode, 0)
                else:
                    self.assertEqual(result.returncode, 0)
                self.assertTrue(target.samefile(self.fixture.memory.database))
                target.unlink()

    def test_review_of_old_json_sources_preserves_exact_bytes_and_blocks_decoded_private_or_retired_claims(self):
        paths = ['LIFEOS/USER/HEALTH/current.json']
        self.retire_work()
        self.assertNotIn('SYNTHETIC_CURRENT_SOURCE_NOTE', self.successful('--domain', 'health').stdout)
        before = (self.root / paths[0]).read_bytes()
        snapshot = preview(self.fixture.memory, OWNER, paths)
        self.assertTrue(snapshot['sources'][0]['accepted'])
        self.assertEqual(approve(self.fixture.memory, OWNER, paths, snapshot['signature'])['status'], 'committed')
        self.assertIn('SYNTHETIC_CURRENT_SOURCE_NOTE', self.successful('--domain', 'health').stdout)
        self.assertEqual((self.root / paths[0]).read_bytes(), before)
        for body in ('\\u003cprivate\\u003eSynthetic private evidence\\u003c/private\\u003e',
                     '\\u0053ynthetic retired evidence work'):
            with self.subTest(body=body):
                (self.root / paths[0]).write_text('{"note":"' + body + '"}')
                fresh = preview(self.fixture.memory, OWNER, paths)
                self.assertFalse(fresh['sources'][0]['accepted'])
                self.assertEqual(fresh['sources'][0]['content'], '')
                self.assertEqual(approve(self.fixture.memory, OWNER, paths, fresh['signature'])['status'], 'rejected')

    def test_owner_payload_matches_standalone_at_the_same_calculation_date(self):
        module = str(self.root / 'LIFEOS/TOOLS/StateEvidence.ts')
        program = 'const m=await import(process.argv[1]);console.log(JSON.stringify(m.gatherEvidence(new Date(process.argv[2]))));'
        args = ['bun', '--no-install', '-e', program, module, self.day + 'T12:00:00Z']
        actual = subprocess.run(args, env=self.fixture.environment(), capture_output=True, text=True, timeout=30)
        self.assertEqual(actual.returncode, 0, actual.stderr)
        (self.root / 'LIFEOS/USER/CONFIG/memory-access.json').unlink()
        native = subprocess.run(args, env=self.fixture.environment(context=False), capture_output=True, text=True, timeout=30)
        self.assertEqual(native.returncode, 0, native.stderr)
        self.assertEqual(json.loads(actual.stdout), json.loads(native.stdout))

    def test_missing_or_malformed_feed_keeps_native_unavailable_metrics(self):
        path = self.root / 'LIFEOS/USER/HEALTH/current.json'
        for content in (None, '{broken json', '{"note":"\\ud800"}', '{"note":NaN}'):
            with self.subTest(content=content):
                if content is None:
                    path.unlink()
                else:
                    path.write_text(content)
                payload = json.loads(self.successful('--domain', 'health').stdout)
                self.assertEqual(next(row for row in payload['sources'] if row['id'] == 'apple')['status'], 'unavailable')

    def test_supplied_cache_payload_must_match_current_sources(self):
        before = self.previous()
        payload = json.loads(self.successful('--domain', 'work').stdout)
        evidence = {'schema': 1, 'generated_at': self.day + 'T00:00:00Z',
                    'domains': {domain: payload for domain in ('health', 'activity', 'work', 'money')}}
        result = self.library('writeEvidenceCache', evidence)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), False)
        with self.fixture.memory._transaction():
            self.assertEqual(self.cache.read_bytes(), before)

    def test_restricted_owner_and_missing_connector_cannot_read_or_publish(self):
        before = self.previous()
        self.fixture.fixture.configuration.update(lambda value: value['destinations']['chat-a:200'].update(read=['project']))
        self.assertNotEqual(self.call('--json').returncode, 0)
        self.assertEqual(self.cache.read_bytes(), before)
        self.fixture.fixture.configuration.update(lambda value: value['destinations']['chat-a:200'].update(
            read=['principal', 'assistant', 'project']))
        (self.root / 'LIFEOS/USER/CONFIG/memory-http.json').write_text('{"version":1,"managed":true}')
        (self.root / 'LIFEOS/USER/CONFIG/memory-access.json').unlink()
        self.assertNotEqual(self.call('--json', context=False).returncode, 0)
        self.assertEqual(self.cache.read_bytes(), before)
