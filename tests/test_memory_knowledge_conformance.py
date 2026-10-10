# ABOUTME: Exercises the native SessionEnd Knowledge conformance handler with synthetic owner grants.
# ABOUTME: Verifies current-note diagnostics, finding events, refusal, and standalone behavior.
from dataclasses import asdict
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import unittest

from test_memory_native import OWNER
from lifeos_hook_bridge.memory_service import MemoryService
import test_memory_knowledge_lint as lint_fixture


class MemoryKnowledgeConformanceTests(unittest.TestCase):
    def setUp(self):
        self.lint=lint_fixture.MemoryKnowledgeLintTests()
        self.lint.setUp()
        self.addCleanup(self.lint.doCleanups)
        self.fixture=self.lint.fixture
        self.root=self.lint.root
        self.events=self.root/'LIFEOS/MEMORY/STATE/events.jsonl'

    def call(self,*,context=True,source=None):
        environment=dict(os.environ,HOME=str(self.fixture.fixture.home),LIFEOS_DIR=str(self.root/'LIFEOS'),
            BUN_CONFIG_NO_AUTO_INSTALL='1',CLAUDE_SESSION_ID='synthetic-conformance-control')
        environment.pop('LIFEOS_MEMORY_CONTEXT',None)
        environment.pop('LIFEOS_MEMORY_INTERNAL',None)
        if context:environment['LIFEOS_MEMORY_CONTEXT']=json.dumps(asdict(self.fixture.context))
        script=(source or self.root)/'hooks/handlers/KnowledgeConformance.ts'
        return subprocess.run(['bun','--no-install',str(script)],env=environment,capture_output=True,text=True,timeout=40)

    def event(self):
        return json.loads(self.events.read_text().splitlines()[-1])

    def test_native_diagnostic_and_event_match_original_registered_note_checks(self):
        original=self.call(source=self.lint.control)
        self.assertEqual(original.returncode,0,original.stderr)
        event=self.event()
        actual=self.call()
        self.assertEqual(actual.returncode,0,actual.stderr)
        self.assertEqual(actual.stdout,'')
        normalize=lambda text:re.sub(r'\(\d+ms,','(elapsed,',text)
        self.assertEqual(normalize(actual.stderr),normalize(original.stderr))
        current=self.event()
        for record in (event,current):
            record.pop('timestamp')
            record.pop('session_id')
        self.assertEqual(current,event)

    def test_unbound_handler_cannot_publish_or_report_private_note_counts(self):
        result=self.call(context=False)
        self.assertNotEqual(result.returncode,0,result)
        self.assertFalse(self.events.exists())
        self.assertNotIn('2 notes',result.stderr)
        self.assertNotIn('off-schema',result.stderr)

    def test_unregistered_notes_are_excluded_from_events_and_counts(self):
        unknown=self.lint.first.with_name('synthetic-unregistered-conformance.md')
        unknown.write_text(self.lint.first.read_text())
        result=self.call()
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(self.event()['total'],2)
        self.assertTrue(unknown.exists())

    def test_forgotten_notes_are_excluded_from_events_and_counts(self):
        self.fixture.fixture.memory.forget(OWNER,self.lint.reference,'synthetic-forget-conformance')
        result=self.call()
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(self.event()['total'],1)

    def test_read_only_owner_cannot_publish_a_finding_set(self):
        self.fixture.configuration.update(lambda value:value['destinations']['chat-a:200'].update(write=[]))
        result=self.call()
        self.assertNotEqual(result.returncode,0,result)
        self.assertFalse(self.events.exists())

    def test_standalone_keeps_event_publication_without_a_connector(self):
        (self.root/'LIFEOS/USER/CONFIG/memory-access.json').unlink()
        result=self.call(context=False)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(self.event()['total'],2)

    def probe(self,mode):
        return subprocess.run([sys.executable,str(Path(__file__).with_name('memory_knowledge_conformance_process.py')),
            str(self.fixture.configuration.path),mode],capture_output=True,text=True,timeout=40,
            env=dict(os.environ,PYTHONPATH=str(Path(__file__).resolve().parents[1])))

    def test_authority_changes_after_render_withhold_events_and_report(self):
        result=self.probe('authority')
        self.assertEqual(result.returncode,0,result.stderr)
        response=json.loads(result.stdout)
        self.assertTrue(response['rendered'])
        self.assertFalse(response['result']['ok'])
        self.assertNotIn('stderr',response['result'])
        self.assertFalse(self.events.exists())

    def test_source_changes_after_render_do_not_publish_a_stale_event(self):
        result=self.probe('source')
        self.assertEqual(result.returncode,0,result.stderr)
        response=json.loads(result.stdout)
        self.assertTrue(response['rendered'])
        self.assertFalse(response['result']['ok'])
        self.assertFalse(self.events.exists())

    def test_later_event_history_survives_a_publication_conflict(self):
        before=b'{"type":"SyntheticOriginalEvent"}\n'
        self.events.write_bytes(before)
        result=self.probe('history')
        self.assertEqual(result.returncode,0,result.stderr)
        response=json.loads(result.stdout)
        self.assertFalse(response['result']['ok'],response)
        self.assertEqual(self.events.read_bytes(),before+b'{"type":"SyntheticConcurrentEvent"}\n')

    def test_interrupted_event_publication_recovers_the_original_history(self):
        before=b'{"type":"SyntheticOriginalEvent"}\n'
        self.events.write_bytes(before)
        result=self.probe('interrupt')
        self.assertEqual(result.returncode,73,result.stderr)
        self.assertNotEqual(self.events.read_bytes(),before)
        self.fixture.fixture.memory.read_hot(OWNER,'principal')
        self.assertEqual(self.events.read_bytes(),before)

    def test_retry_does_not_append_duplicate_finding_events(self):
        service=MemoryService(self.fixture.configuration)
        arguments={'request_id':'synthetic-idempotent-conformance'}
        first=service.native(self.fixture.context,'knowledge_conformance',arguments)
        self.assertTrue(first['ok'],first)
        before=self.events.read_bytes()
        second=service.native(self.fixture.context,'knowledge_conformance',arguments)
        self.assertTrue(second['ok'],second)
        self.assertEqual(first,second)
        self.assertEqual(self.events.read_bytes(),before)
        self.assertEqual(self.event()['session_id'],self.fixture.context.session_id)
        self.assertRegex(self.event()['timestamp'],r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$')
        self.assertEqual(self.events.stat().st_mode&0o777,0o600)

    def test_empty_current_archive_publishes_a_clear_finding_set(self):
        with self.fixture.fixture.memory._transaction() as connection:
            references=[{'id':row['id'],'revision':row['revision']} for row in connection.execute('SELECT * FROM records')]
        for index,reference in enumerate(references):
            self.fixture.fixture.memory.forget(OWNER,reference,'synthetic-empty-conformance-'+str(index))
        result=self.call()
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(self.event()['total'],0)
        self.assertEqual(self.event()['findings'],[])
        self.assertTrue(self.event()['ok'])

    def test_missing_archive_skips_without_publishing_a_clear_finding_set(self):
        with self.fixture.fixture.memory._transaction() as connection:
            connection.execute('DELETE FROM records')
        shutil.rmtree(self.root/'LIFEOS/MEMORY/KNOWLEDGE')
        result=self.call()
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(result.stderr,'')
        self.assertFalse(self.events.exists())

    def test_standalone_unreadable_note_preserves_the_original_violation(self):
        (self.root/'LIFEOS/USER/CONFIG/memory-access.json').unlink()
        self.lint.first.chmod(0)
        original=self.call(source=self.lint.control,context=False)
        self.assertEqual(original.returncode,0,original.stderr)
        event=self.event()
        actual=self.call(context=False)
        self.assertEqual(actual.returncode,0,actual.stderr)
        current=self.event()
        for record in (event,current):
            record.pop('timestamp')
            record.pop('session_id')
        self.assertEqual(current,event)


if __name__=='__main__':unittest.main()
