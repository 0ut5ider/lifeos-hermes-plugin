# ABOUTME: Checks separate native owner research sessions against real admission and retirement state.
# ABOUTME: Preserves parent proof, current grants, and existing child sessions without model requests.
from dataclasses import asdict
import json
import unittest
from lifeos_hook_bridge.memory_runtime import MemoryAdmissionError
import test_memory_owner_jobs as fixture


class OwnerResearchSessionTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixture.MemoryOwnerJobsTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.runtime = self.fixture.jobs.runtime
        self.runtime.admit({'HERMES_SESSION_PLATFORM': 'cli', 'HERMES_SESSION_ID': 'owner-job-synthetic-parent'},
            **self.fixture.route, is_first_turn=True)

    def states(self):
        return json.loads(self.runtime.state_path.read_text())

    def test_child_preserves_parent_proof_and_existing_session(self):
        before = self.states()
        parent = self.runtime.context()
        self.runtime.fork_owner_job('owner-research-synthetic-child', route=self.fixture.route)
        after = self.states()
        self.assertEqual(after['owner-job-synthetic-parent'], before['owner-job-synthetic-parent'])
        child = self.runtime.context()
        self.assertEqual({key: value for key, value in asdict(parent).items() if key != 'session_id'},
            {key: value for key, value in asdict(child).items() if key != 'session_id'})
        with self.assertRaises(MemoryAdmissionError):
            self.runtime.fork_owner_job('owner-research-synthetic-child', route=self.fixture.route)
        self.assertEqual(self.states(), after)

    def test_changed_grant_and_unapproved_route_cannot_create_child(self):
        before = self.states()
        with self.assertRaises(MemoryAdmissionError):
            self.runtime.fork_owner_job('owner-research-wrong-route', route={**self.fixture.route, 'model': 'unapproved'})
        self.assertEqual(self.states(), before)
        self.fixture.configuration.update(lambda value:
            value['destinations']['terminal:' + str(self.fixture.configuration.path.parent)].update(write=[]))
        with self.assertRaises(MemoryAdmissionError):
            self.runtime.fork_owner_job('owner-research-read-only', route=self.fixture.route)
        self.assertEqual(self.states(), before)

    def test_new_retirement_refuses_child_without_refreshing_parent(self):
        from test_memory_native import OWNER
        memory = self.fixture.fixture.fixture.fixture.memory
        saved = memory.remember(OWNER, category='principal', content='RULE: Synthetic research retirement boundary',
            title='', project='', request_id='research-retired-save')
        memory.forget(OWNER, saved['reference'], 'research-retired-forget')
        before = self.states()
        with self.assertRaises(MemoryAdmissionError):
            self.runtime.fork_owner_job('owner-research-after-retirement', route=self.fixture.route)
        self.assertEqual(self.states(), before)
