# ABOUTME: Exercises fixed native LocalIntelligence run sidecars under current owner authority.
# ABOUTME: Preserves later log edits and refuses private or retired process output.
import json
import subprocess
import sys
from pathlib import Path
from dataclasses import asdict
import unittest
from datetime import datetime, timezone
import test_memory_local_refresh as fixture


class MemoryLocalRefreshRunTests(unittest.TestCase):
    setUp = fixture.MemoryLocalRefreshTests.setUp
    call = fixture.MemoryLocalRefreshTests.call

    def start(self):
        self.run_id = datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z').replace(':', '-').replace('.', '-') + '_1234abcd'
        self.directory = self.root / 'LIFEOS/USER/CUSTOMIZATIONS/SKILLS/LocalIntelligence/runs'
        return self.call('local_run_start', run_id=self.run_id)

    def finish(self, started, content='Synthetic refresh summary\n', exit_code=0):
        return self.call('local_run_finish', run_id=self.run_id, signature=started['signature'], content=content, exit_code=exit_code)

    def test_native_run_sidecars_are_private_and_keep_actual_exit_code(self):
        started = self.start()
        self.assertTrue(started['ok'], started)
        marker = self.directory / (self.run_id + '.log.started')
        log = self.directory / (self.run_id + '.log')
        self.assertEqual(log.read_bytes(), b'')
        datetime.fromisoformat(marker.read_text().replace('Z', '+00:00'))
        self.assertTrue(self.finish(started, exit_code=1)['ok'])
        self.assertEqual(log.read_text(), 'Synthetic refresh summary\n\n[exit] code=1\n')
        self.assertEqual([file.stat().st_mode & 0o777 for file in (marker, log)], [0o600, 0o600])

    def test_later_log_edits_and_revoked_writer_remain_intact(self):
        started = self.start()
        self.assertTrue(started['ok'], started)
        log = self.directory / (self.run_id + '.log')
        log.write_text('Synthetic later owner edit')
        self.assertFalse(self.finish(started)['ok'])
        self.assertEqual(log.read_text(), 'Synthetic later owner edit')
        self.configuration.update(lambda value: value['destinations']['chat-a:200'].update(write=[]))
        self.assertFalse(self.start()['ok'])

    def test_private_and_retired_output_cannot_enter_run_log(self):
        started = self.start()
        self.assertTrue(started['ok'], started)
        self.assertFalse(self.finish(started, '<private>SyntheticHiddenRun</private>')['ok'])
        self.assertEqual((self.directory / (self.run_id + '.log')).read_bytes(), b'')

    def test_current_retired_claim_cannot_enter_new_run_log(self):
        from test_memory_native import OWNER
        memory = self.owner.fixture.memory
        saved = memory.remember(OWNER, category='principal', content='RULE: Synthetic retired local log claim',
            title='', project='', request_id='local-run-retired-save')
        memory.forget(OWNER, saved['reference'], 'local-run-retired-forget')
        started = self.start()
        self.assertTrue(started['ok'], started)
        self.assertFalse(self.finish(started, 'RULE: Synthetic retired local log claim')['ok'])
        self.assertEqual((self.directory / (self.run_id + '.log')).read_bytes(), b'')

    def test_actual_partial_run_publication_recovers_prior_absence(self):
        run_id = '2026-10-09T00-00-00-000Z_1234abcd'
        result = subprocess.run([sys.executable, str(Path(__file__).with_name('memory_local_runs_process.py')),
            str(self.configuration.path), 'interrupt', json.dumps(asdict(self.owner.context)), run_id],
            capture_output=True, text=True, timeout=30)
        self.assertEqual((result.returncode, result.stderr), (73, ''), result.stdout)
        directory = self.root / 'LIFEOS/USER/CUSTOMIZATIONS/SKILLS/LocalIntelligence/runs'
        self.assertTrue((directory / (run_id + '.log')).exists())
        self.assertFalse((directory / (run_id + '.log.started')).exists())
        self.assertTrue(self.start()['ok'])
        self.assertFalse((directory / (run_id + '.log')).exists())
        self.assertFalse((directory / (run_id + '.log.started')).exists())

    def test_partial_run_recovery_preserves_actual_later_owner_edit(self):
        run_id = '2026-10-09T00-00-00-000Z_1234abcd'
        result = subprocess.run([sys.executable, str(Path(__file__).with_name('memory_local_runs_process.py')),
            str(self.configuration.path), 'later', json.dumps(asdict(self.owner.context)), run_id],
            capture_output=True, text=True, timeout=30)
        self.assertEqual((result.returncode, result.stderr), (73, ''), result.stdout)
        directory = self.root / 'LIFEOS/USER/CUSTOMIZATIONS/SKILLS/LocalIntelligence/runs'
        self.assertFalse(self.start()['ok'])
        self.assertEqual((directory / (run_id + '.log')).read_text(), 'Synthetic later diagnostic edit')

    def test_arbitrary_run_identifier_refuses_without_files(self):
        for run_id in ('../outside', '', [], '2026-10-09T00-00-00-000Z_1234ABCD'):
            with self.subTest(run_id=run_id):
                self.assertFalse(self.call('local_run_start', run_id=run_id)['ok'])
        self.assertFalse((self.root / 'LIFEOS/USER/CUSTOMIZATIONS/SKILLS/LocalIntelligence/runs').exists())
