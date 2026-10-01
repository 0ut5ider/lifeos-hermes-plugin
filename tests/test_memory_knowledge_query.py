# ABOUTME: Tests the native Knowledge query surface against governed current notes.
# ABOUTME: Checks owner controls, excluded metadata, alternate roots, and standalone output.
from dataclasses import asdict
import json
import os
import subprocess
import unittest

import test_memory_delegation as delegation
from test_memory_native import OWNER


class MemoryKnowledgeQueryTests(unittest.TestCase):
    def setUp(self):
        self.fixture=delegation.MemoryDelegationTests();self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.native=self.fixture.fixture
        self.reference=self.native.remember('SyntheticKnowledgeCurrentMarker','knowledge-current','project')['reference']
        self.module=self.fixture.root/'LIFEOS/TOOLS/KnowledgeQuery.ts'

    def call(self,*args,context=True,managed=True):
        if not managed:(self.fixture.root/'LIFEOS/USER/CONFIG/memory-access.json').unlink()
        environment=dict(os.environ,HOME=str(self.native.home),BUN_CONFIG_NO_AUTO_INSTALL='1')
        environment.pop('LIFEOS_MEMORY_INTERNAL',None);environment.pop('LIFEOS_MEMORY_CONTEXT',None)
        if context:environment['LIFEOS_MEMORY_CONTEXT']=json.dumps(asdict(self.fixture.context))
        return subprocess.run(['bun','--no-install',str(self.module),*args],env=environment,
                              capture_output=True,text=True,timeout=30)

    def test_unmanaged_filters_and_json_preserve_native_metadata(self):
        result=self.call('--json','--type','research','--text','Synthetic lab','--dir','Research',managed=False)
        self.assertEqual(result.returncode,0,result.stderr);self.assertEqual(result.stderr,'')
        rows=json.loads(result.stdout)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['title'],'Synthetic lab routing')
        self.assertEqual(rows[0]['slug'],'synthetic-lab-routing')
        self.assertEqual(rows[0]['dir'],'Research')
        self.assertEqual(rows[0]['type'],'research')

    def test_managed_owner_preserves_native_query_filters_and_output(self):
        result=self.call('--json','--type','research','--text','Synthetic lab','--dir','Research')
        self.assertEqual(result.returncode,0,result.stderr);self.assertEqual(result.stderr,'')
        self.assertEqual(len(json.loads(result.stdout)),1)
        self.assertEqual(json.loads(result.stdout)[0]['slug'],'synthetic-lab-routing')
        self.assertEqual(self.call('--count','--type','idea').stdout,'0\n')
        self.assertEqual(self.call('--slugs','--all').stdout,'synthetic-lab-routing\n')
        table=self.call('--type','research')
        self.assertEqual(table.returncode,0,table.stderr)
        self.assertIn('1 match',table.stdout);self.assertIn('Synthetic lab routing',table.stdout)

    def test_missing_context_refuses_before_metadata_output(self):
        result=self.call('--json',context=False)
        self.assertNotEqual(result.returncode,0)
        self.assertNotIn('Synthetic lab routing',result.stdout+result.stderr)

    def test_revoked_account_cannot_query_note_metadata(self):
        self.fixture.configuration.update(lambda config:config['accounts'].pop('chat-a:100'))
        result=self.call('--json')
        self.assertNotEqual(result.returncode,0)
        self.assertNotIn('Synthetic lab routing',result.stdout+result.stderr)

    def test_forgotten_fact_does_not_leave_a_queryable_note(self):
        self.native.memory.forget(OWNER,self.reference,'knowledge-forget')
        result=self.call('--json')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout),[])

    def test_corrected_note_is_still_queryable(self):
        self.native.memory.correct(OWNER,self.reference,'SyntheticKnowledgeReplacementMarker','knowledge-correct')
        result=self.call('--json')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(len(json.loads(result.stdout)),1)

    def test_unregistered_note_is_not_in_the_managed_query(self):
        self.native.memory._native('add',item={'type':'knowledge','entity_type':'research',
            'name':'SyntheticUnregisteredTitle','content':'SyntheticUnregisteredKnowledgeMarker'})
        result=self.call('--json','--text','SyntheticUnregisteredTitle')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout),[])

    def test_retired_note_title_is_not_queryable(self):
        saved=self.native.remember('RULE: Synthetic lab routing','knowledge-title','principal')['reference']
        self.native.memory.forget(OWNER,saved,'knowledge-retire-title')
        result=self.call('--json')
        self.assertNotEqual(result.returncode,0)
        self.assertNotIn('Synthetic lab routing',result.stdout+result.stderr)

    def test_directory_argument_cannot_select_files_outside_knowledge(self):
        foreign=self.fixture.root/'LIFEOS/MEMORY/foreign';foreign.mkdir()
        (foreign/'secret.md').write_text('---\ntitle: SyntheticForeignMetadata\ntype: research\n---\nSyntheticForeignBody')
        result=self.call('--json','--dir','../foreign')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout),[])

    def test_project_only_grant_cannot_query_unclassified_metadata(self):
        self.fixture.configuration.update(lambda config:config['destinations']['chat-a:200'].update(
            read=['project'],projects=['lab']))
        result=self.call('--json')
        self.assertNotEqual(result.returncode,0)
        self.assertNotIn('Synthetic lab routing',result.stdout+result.stderr)


if __name__=='__main__':unittest.main()
