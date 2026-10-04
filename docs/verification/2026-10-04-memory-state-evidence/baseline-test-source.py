# ABOUTME: Characterizes native state evidence reads, cache writes, and JSON source boundaries.
# ABOUTME: Uses synthetic domain inputs without configuring external integrations.
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import unittest

import test_memory_freshness as freshness_fixture
from test_memory_native import OWNER


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
