# ABOUTME: Executes selected scheduled native jobs through an authenticated local owner.
# ABOUTME: Verifies denied grants, process isolation, private publication, and repeat runs.
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

from lifeos_hook_bridge.memory_context import route_identity
from lifeos_hook_bridge.memory_owner_jobs import OwnerJobs
from lifeos_hook_bridge.memory_runtime import MemoryAdmissionError, MemoryRuntime
from lifeos_hook_bridge.memory_transaction import publish
import test_memory_session_harvest as harvest_fixture
import test_memory_proposal_gc as gc_fixture


class MemoryOwnerJobsTests(unittest.TestCase):
    def setUp(self):
        self.fixture = harvest_fixture.MemorySessionHarvestTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.configuration = self.fixture.fixture.configuration
        self.route = {'provider': 'synthetic', 'model': 'synthetic-flashnext',
            'base_url': 'http://127.0.0.1:12345/v1', 'api_mode': 'chat_completions'}
        self.mapping = {'pin': 'none', **{tier: {'provider': self.route['provider'],
            'model': self.route['model'], 'effort': effort}
            for tier, effort in (('haiku', 'low'), ('sonnet', 'medium'), ('opus', 'xhigh'), ('fable', 'xhigh'))}}
        self.grant = {'visibility': 'private', 'participants': ['owner'],
            'read': ['principal', 'assistant', 'project'], 'write': ['principal', 'assistant', 'project'],
            'projects': ['*'], 'model_routes': [route_identity(**self.route)]}
        def bind(value):
            value['ownership_enabled'] = True
            value['accounts'][f'terminal:{os.getuid()}'] = 'owner'
            value['destinations']['terminal:' + str(self.configuration.path.parent)] = self.grant
        self.configuration.update(bind)
        # Capture the synthetic foreground transcript under the final policy.
        runtime = MemoryRuntime(self.configuration.path)
        with self.fixture.fixture.fixture.memory._transaction() as connection:
            state = runtime._stamp(self.configuration.load(), self.fixture.context, connection)
        publish(runtime.state_path, json.dumps({self.fixture.session: state}).encode())
        self.jobs = OwnerJobs(self.configuration.path)
        self.addCleanup(self.jobs.runtime.clear)

    def run_job(self, name='memory-consolidation'):
        return self.jobs.run(name, route=self.route, mapping=self.mapping)

    def test_actual_consolidation_publishes_one_private_learning_and_preserves_repeat(self):
        first = self.run_job()
        self.assertEqual(first['status'], 'completed', first)
        self.assertIn('Harvested 1 learning', first['output'])
        notes = self.fixture.notes()
        self.assertEqual(len(notes), 1)
        self.assertIn(self.fixture.content, notes[0].read_text())
        self.assertEqual(notes[0].stat().st_mode & 0o777, 0o600)
        before = notes[0].read_bytes(), notes[0].stat().st_mtime_ns
        second = self.run_job()
        self.assertEqual(second['status'], 'completed', second)
        self.assertEqual(self.fixture.notes(), notes)
        self.assertEqual((notes[0].read_bytes(), notes[0].stat().st_mtime_ns), before)

    def test_removed_local_account_cannot_borrow_a_discord_or_retained_context(self):
        self.configuration.update(lambda value: value['accounts'].pop(f'terminal:{os.getuid()}'))
        with self.assertRaises(MemoryAdmissionError):
            self.run_job()
        self.assertEqual(self.fixture.notes(), [])

    def test_disabled_ownership_cannot_fall_back_to_unmanaged_commands(self):
        self.configuration.update(lambda value: value.update(ownership_enabled=False))
        with self.assertRaises(MemoryAdmissionError):
            self.run_job()
        self.assertEqual(self.fixture.notes(), [])

    def test_read_only_job_refuses_before_any_consolidation(self):
        self.configuration.update(lambda value: value['destinations']['terminal:' + str(self.configuration.path.parent)].update(write=[]))
        with self.assertRaises(MemoryAdmissionError):
            self.run_job()
        self.assertEqual(self.fixture.notes(), [])

    def test_unknown_route_refuses_before_any_consolidation(self):
        self.route['base_url'] = ''
        with self.assertRaises(MemoryAdmissionError):
            self.run_job()
        self.assertEqual(self.fixture.notes(), [])

    def test_job_name_cannot_run_an_arbitrary_program(self):
        with self.assertRaises(ValueError):
            self.run_job('memory-consolidation; touch /tmp/forbidden')
        self.assertEqual(self.fixture.notes(), [])

    def test_unbounded_or_invalid_deadlines_refuse_before_native_writes(self):
        for timeout in (float('inf'), float('nan'), 0, -1, True, 541):
            with self.subTest(timeout=timeout), self.assertRaises(ValueError):
                self.jobs.run('memory-consolidation', route=self.route, mapping=self.mapping, timeout=timeout)
        self.assertEqual(self.fixture.notes(), [])

    def test_native_environment_uses_selected_home_and_actual_local_author(self):
        result = self.run_job()
        self.assertEqual(result['status'], 'completed', result)
        context = self.jobs.runtime.context()
        self.assertEqual(context.transport, 'terminal')
        self.assertEqual(context.author, str(os.getuid()))
        self.assertEqual(context.destination, str(self.configuration.path.parent))
        states = json.loads(self.jobs.runtime.state_path.read_text())
        self.assertEqual(states[context.session_id]['context']['author'], str(os.getuid()))

    def process(self, mode):
        environment = dict(os.environ, HERMES_SESSION_PLATFORM='discord', HERMES_SESSION_USER_ID='forged-owner',
            HERMES_CRON_SESSION='1', HERMES_CRON_AUTO_DELIVER_PLATFORM='discord',
            LIFEOS_MEMORY_CONTEXT='{"transport":"discord","author":"forged-owner"}',
            LIFEOS_MEMORY_INTERNAL='1', LIFEOS_MODEL_TIER_MAP='{}')
        result = subprocess.run([sys.executable, str(Path(__file__).with_name('memory_owner_jobs_process.py')),
            str(self.configuration.path), json.dumps(self.route), json.dumps(self.mapping), mode],
            env=environment, capture_output=True, text=True, timeout=40)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        return json.loads(result.stdout)

    def test_actual_children_replace_inherited_author_and_keep_configured_tiers(self):
        result = self.process('observe')
        self.assertEqual(result['result']['status'], 'completed', result)
        self.assertEqual(len(result['observed']), 2)
        for observed in result['observed']:
            self.assertEqual(observed['context']['transport'], 'terminal')
            self.assertEqual(observed['context']['author'], str(os.getuid()))
            self.assertEqual(observed['scheduled_metadata'], [])
            self.assertEqual(observed['mapping'], self.mapping)
            self.assertEqual(observed['home'], str(self.fixture.root.parent))

    def test_revocation_after_actual_commit_withholds_output_and_keeps_learning(self):
        result = self.process('revoke')
        self.assertEqual(result['result'], {'status': 'authority-refused'})
        self.assertNotIn(self.fixture.content, json.dumps(result))
        self.assertEqual(len(self.fixture.notes()), 1)
        self.assertIn(self.fixture.content, self.fixture.notes()[0].read_text())

    def test_actual_cleanup_uses_the_same_owner_job_admission(self):
        fixture = gc_fixture.MemoryProposalGCTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        # Use this job's current configuration for the cleanup's native connector.
        fixture.configuration = self.configuration
        connector = fixture.root / 'LIFEOS/USER/CONFIG/memory-access.json'
        declaration = json.loads(connector.read_text())
        declaration['command'][-1] = str(self.configuration.path)
        publish(connector, json.dumps(declaration).encode())
        self.configuration.update(lambda value: value.update(root=str(fixture.root)))
        result = self.run_job('proposal-gc')
        self.assertEqual(result['status'], 'completed', result)
        self.assertNotIn('Synthetic private cleanup marker', fixture.target.read_text())
        self.assertEqual(fixture.target.read_text().count('Keep the distinct synthetic rule.'), 1)
        self.assertEqual(fixture.target.stat().st_mode & 0o777, 0o600)


if __name__ == '__main__':
    unittest.main()
