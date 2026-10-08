# ABOUTME: Exercises actual native event appends with synthetic owner contexts and private destinations.
# ABOUTME: Verifies report fidelity, refusal, concurrent writers, and recoverable event publication.
from dataclasses import asdict
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

from lifeos_hook_bridge.memory_service import MemoryService
from test_memory_native import OWNER
import test_memory_knowledge_lint as fixture_module


class MemoryEventsTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixture_module.MemoryKnowledgeLintTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.owner=self.fixture.fixture
        self.root=self.fixture.root
        self.events=self.root/'LIFEOS/MEMORY/STATE/events.jsonl'

    def command(self,event,*,context=True,source=None,path=None):
        module=(source or self.root)/'hooks/lib/events.ts'
        expression='import {appendEvent} from '+json.dumps(str(module))+';appendEvent('+json.dumps(event)
        if path is not None:expression+=','+json.dumps(str(path))
        expression+=');'
        environment=dict(os.environ,HOME=str(self.owner.fixture.home),LIFEOS_DIR=str(self.root/'LIFEOS'),
            BUN_CONFIG_NO_AUTO_INSTALL='1',CLAUDE_SESSION_ID='synthetic-raw-event-session')
        environment.pop('LIFEOS_MEMORY_CONTEXT',None)
        environment.pop('LIFEOS_MEMORY_INTERNAL',None)
        if context:environment['LIFEOS_MEMORY_CONTEXT']=json.dumps(asdict(self.owner.context))
        return ['bun','--no-install','-e',expression],environment

    def call(self,event,**arguments):
        command,environment=self.command(event,**arguments)
        result=subprocess.run(command,env=environment,capture_output=True,text=True,timeout=40)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(result.stdout,'')
        self.assertEqual(result.stderr,'')
        return result

    def test_current_event_matches_original_fields_and_uses_authenticated_session(self):
        value={'type':'SyntheticCheck','source':'SyntheticEmitter','findings':[],'count':3}
        self.call(value,source=self.fixture.control)
        original=json.loads(self.events.read_text().splitlines()[-1])
        self.call(value)
        actual=json.loads(self.events.read_text().splitlines()[-1])
        self.assertEqual(actual['session_id'],self.owner.context.session_id)
        for event in (original,actual):
            self.assertRegex(event.pop('timestamp'),r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$')
            event.pop('session_id')
        self.assertEqual(actual,original)

    def test_unbound_emitter_silently_refuses_without_publishing(self):
        self.call({'type':'SyntheticCheck','source':'SyntheticEmitter'},context=False)
        self.assertFalse(self.events.exists())

    def test_read_only_owner_cannot_append_events(self):
        self.owner.configuration.update(lambda value:value['destinations']['chat-a:200'].update(write=[]))
        self.call({'type':'SyntheticCheck','source':'SyntheticEmitter'})
        self.assertFalse(self.events.exists())

    def test_managed_emitter_cannot_publish_to_another_path(self):
        alternate=self.root/'LIFEOS/MEMORY/STATE/synthetic-other.jsonl'
        self.call({'type':'SyntheticCheck','source':'SyntheticEmitter'},path=alternate)
        self.assertFalse(alternate.exists())

    def test_forgotten_source_text_cannot_reappear_in_an_event(self):
        self.owner.fixture.memory.forget(OWNER,self.fixture.reference,'synthetic-event-forget')
        self.call({'type':'SyntheticCheck','source':'SyntheticEmitter','detail':'Synthetic lint fact'})
        self.assertFalse(self.events.exists())

    def test_symlink_destination_does_not_change_an_external_file(self):
        external=self.root.parent/'synthetic-external-event'
        external.write_bytes(b'Synthetic retained bytes')
        self.events.symlink_to(external)
        self.call({'type':'SyntheticCheck','source':'SyntheticEmitter'})
        self.assertEqual(external.read_bytes(),b'Synthetic retained bytes')

    def test_managed_timestamp_and_session_cannot_be_forged(self):
        self.call({'type':'SyntheticCheck','source':'SyntheticEmitter',
            'timestamp':'synthetic-forged-timestamp','session_id':'synthetic-forged-session'})
        record=json.loads(self.events.read_text())
        self.assertNotEqual(record['timestamp'],'synthetic-forged-timestamp')
        self.assertEqual(record['session_id'],self.owner.context.session_id)

    def test_standalone_emitter_preserves_native_overrides(self):
        (self.root/'LIFEOS/USER/CONFIG/memory-access.json').unlink()
        self.call({'type':'SyntheticCheck','source':'SyntheticEmitter','session_id':'synthetic-override'},context=False)
        self.assertEqual(json.loads(self.events.read_text())['session_id'],'synthetic-override')

    def test_retry_does_not_duplicate_and_preserves_later_entries(self):
        service=MemoryService(self.owner.configuration)
        arguments={'path':str(self.events),'event':{'type':'SyntheticFirst','source':'SyntheticEmitter'},
            'request_id':'synthetic-event-retry'}
        first=service.native(self.owner.context,'event_append',arguments)
        self.assertTrue(first['ok'],first)
        self.call({'type':'SyntheticLater','source':'SyntheticEmitter'})
        before=self.events.read_bytes()
        self.assertEqual(service.native(self.owner.context,'event_append',arguments),first)
        self.assertEqual(self.events.read_bytes(),before)
        self.assertEqual(self.events.stat().st_mode&0o777,0o600)

    def test_actual_concurrent_emitters_preserve_each_event(self):
        children=[]
        for index in range(6):
            command,environment=self.command({'type':'SyntheticConcurrent','source':'SyntheticEmitter','ordinal':index})
            children.append(subprocess.Popen(command,env=environment,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True))
        for child in children:
            output,error=child.communicate(timeout=40)
            self.assertEqual(child.returncode,0,error)
            self.assertEqual(output+error,'')
        records=[json.loads(line) for line in self.events.read_text().splitlines()]
        self.assertEqual(sorted(item['ordinal'] for item in records),list(range(6)))

    def test_actual_event_emitter_waits_for_the_finding_transaction(self):
        result=subprocess.run([sys.executable,str(Path(__file__).with_name('memory_events_concurrent_process.py')),
            str(self.owner.configuration.path)],capture_output=True,text=True,timeout=40,
            env=dict(os.environ,PYTHONPATH=str(Path(__file__).resolve().parents[1])))
        self.assertEqual(result.returncode,0,result.stderr)
        report=json.loads(result.stdout)
        self.assertTrue(report['result']['ok'],report)
        self.assertTrue(report['waiting'],report)
        self.assertEqual(report['child_code'],0,report)
        self.assertEqual(report['output']+report['error'],'')
        self.assertEqual([json.loads(line)['type'] for line in self.events.read_text().splitlines()],
            ['doc.integrity.knowledge_conformance','SyntheticAfterFinding'])

    def test_interrupted_append_recovers_original_history(self):
        before=b'{"type":"SyntheticOriginal"}\n'
        self.events.write_bytes(before)
        result=subprocess.run([sys.executable,str(Path(__file__).with_name('memory_events_process.py')),
            str(self.owner.configuration.path)],capture_output=True,text=True,timeout=40,
            env=dict(os.environ,PYTHONPATH=str(Path(__file__).resolve().parents[1])))
        self.assertEqual(result.returncode,73,result.stderr)
        self.assertNotEqual(self.events.read_bytes(),before)
        self.owner.fixture.memory.read_hot(OWNER,'principal')
        self.assertEqual(self.events.read_bytes(),before)
