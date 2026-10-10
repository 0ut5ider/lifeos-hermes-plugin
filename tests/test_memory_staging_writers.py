# ABOUTME: Verifies that native staging rejection and promotion obey current owner authority.
# ABOUTME: Uses actual native commands and isolated staged files for deletion and publication checks.
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

import test_memory_staging as staging_fixture


class MemoryStagingWriterTests(unittest.TestCase):
    def setUp(self):
        self.fixture = staging_fixture.MemoryStagingTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def probe(self, mode, signature=''):
        helper = Path(__file__).with_name('memory_staging_authority_process.py')
        return subprocess.run([sys.executable,str(helper),str(self.fixture.fixture.configuration.path),
            self.fixture.selector,signature,mode],capture_output=True,text=True,
            env=dict(os.environ,PYTHONPATH=str(Path(__file__).resolve().parents[1])),timeout=40)

    def refused(self,response):
        self.assertEqual(response.returncode,0,response.stderr)
        self.assertEqual(response.stderr,'')
        result=json.loads(response.stdout)
        self.assertFalse(result['ok'],result)
        return result

    def test_unbound_native_rejection_cannot_remove_staging(self):
        before = self.fixture.staged.read_bytes()
        result = self.fixture.native_call('reject', self.fixture.selector, context=False)
        self.assertNotEqual(result.returncode, 0, result)
        self.assertEqual(self.fixture.staged.read_bytes(), before)
        self.assertNotIn('Synthetic staged note', result.stdout + result.stderr)

    def test_managed_rejection_returns_a_governed_receipt_and_preserves_the_state(self):
        state = self.fixture.knowledge / '.harvest-state.json'
        state.write_text(json.dumps({'lastHarvest': '2026-10-01T00:00:00Z',
            'harvestedPaths': ['synthetic-source.md'], 'totalHarvested': 0}))
        before = state.read_bytes()
        result = self.fixture.native_call('reject', self.fixture.selector, '--request-id', 'reject-managed')
        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = json.loads(result.stdout)['receipt']
        self.assertEqual(receipt['status'], 'committed', receipt)
        self.assertEqual(receipt['notes_rejected'], 1)
        self.assertEqual(receipt['writer'], 'chat-a:100')
        self.assertFalse(self.fixture.staged.exists())
        self.assertEqual(state.read_bytes(), before)
        retry = self.fixture.native_call('reject', self.fixture.selector, '--request-id', 'reject-managed')
        self.assertEqual(retry.returncode, 0, retry.stderr)
        self.assertEqual(json.loads(retry.stdout)['receipt'], receipt)

    def test_standalone_rejection_retains_the_native_command_behavior(self):
        result = self.fixture.native_call('reject', self.fixture.selector, managed=False, context=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.fixture.staged.exists())
        self.assertIn('rejected:', result.stdout)

    def test_admitted_caller_cannot_reject_after_connector_loss(self):
        before = self.fixture.staged.read_bytes()
        result = self.fixture.native_call('reject', self.fixture.selector, managed=False, context=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.fixture.staged.read_bytes(), before)

    def test_revoked_native_owner_cannot_remove_staging(self):
        self.fixture.fixture.configuration.update(lambda value: value['accounts'].pop('chat-a:100'))
        result = self.fixture.native_call('reject', self.fixture.selector)
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(self.fixture.staged.exists())

    def test_rejection_refuses_a_link_to_another_owner_path(self):
        other=self.fixture.native.home/'synthetic-outside-note.md'
        other.write_text(self.fixture.staged.read_text())
        self.fixture.staged.unlink()
        self.fixture.staged.symlink_to(other)
        result=self.fixture.native_call('reject',self.fixture.selector)
        self.assertNotEqual(result.returncode,0)
        self.assertTrue(self.fixture.staged.is_symlink())
        self.assertTrue(other.exists())

    def test_rejection_refuses_a_hard_link_or_group_writable_source(self):
        original=self.fixture.staged.read_bytes()
        other=self.fixture.staged.with_name('synthetic-hardlink.md')
        os.link(self.fixture.staged,other)
        result=self.fixture.native_call('reject',self.fixture.selector)
        self.assertNotEqual(result.returncode,0)
        self.assertEqual(self.fixture.staged.read_bytes(),original)
        other.unlink()
        self.fixture.staged.chmod(0o660)
        result=self.fixture.native_call('reject',self.fixture.selector)
        self.assertNotEqual(result.returncode,0)
        self.assertEqual(self.fixture.staged.read_bytes(),original)

    def test_native_promotion_refuses_authority_revoked_after_index_rendering(self):
        plan = json.loads(self.fixture.native_call('promote', self.fixture.selector).stdout)
        self.refused(self.probe('authority',plan['signature']))
        self.assertTrue(self.fixture.staged.exists())
        self.assertFalse(self.fixture.target.exists())

    def test_promotion_refuses_staging_changed_during_the_final_render(self):
        plan=json.loads(self.fixture.native_call('promote',self.fixture.selector).stdout)
        self.refused(self.probe('source',plan['signature']))
        self.assertIn('Synthetic concurrent staging edit',self.fixture.staged.read_text())
        self.assertFalse(self.fixture.target.exists())

    def test_promotion_preserves_harvest_state_changed_during_the_final_render(self):
        plan=json.loads(self.fixture.native_call('promote',self.fixture.selector).stdout)
        self.refused(self.probe('state',plan['signature']))
        self.assertEqual(json.loads((self.fixture.knowledge/'.harvest-state.json').read_text())['totalHarvested'],17)
        self.assertTrue(self.fixture.staged.exists())
        self.assertFalse(self.fixture.target.exists())

    def test_rejection_refuses_authority_changed_after_selection(self):
        self.refused(self.probe('reject-authority'))
        self.assertTrue(self.fixture.staged.exists())

    def test_rejection_preserves_a_note_changed_after_selection(self):
        result=self.refused(self.probe('reject-source'))
        self.assertEqual(result['receipt']['status'],'conflict',result)
        self.assertIn('Synthetic concurrent staging edit',self.fixture.staged.read_text())

    def test_interrupted_bulk_rejection_restores_every_staged_note(self):
        other=self.fixture.staged.with_name('synthetic-second-note.md')
        other.write_text(self.fixture.staged.read_text().replace('CurrentMarker','SecondMarker'))
        before={path:path.read_bytes() for path in (self.fixture.staged,other)}
        response=self.probe('reject-interrupt')
        self.assertEqual(response.returncode,73,response.stderr)
        self.assertEqual(response.stderr,'')
        from test_memory_native import OWNER
        self.fixture.native.memory.read_hot(OWNER,'principal')
        for path,data in before.items():self.assertEqual(path.read_bytes(),data)
        retry=self.fixture.native_call('reject','--all','--request-id','reject-authority')
        self.assertEqual(retry.returncode,0,retry.stderr)
        receipt=json.loads(retry.stdout)['receipt']
        self.assertEqual(receipt['notes_rejected'],2,receipt)
        self.assertFalse(self.fixture.staged.exists())
        self.assertFalse(other.exists())
