# ABOUTME: Tests alternate native Cortex reads under managed caller authority.
# ABOUTME: Checks current fact projection, roots, retirement, and standalone behavior.
from dataclasses import asdict
import json
import os
from pathlib import Path
import subprocess
import unittest

import test_memory_delegation as delegation
from test_memory_native import OWNER


class MemoryCanonicalTests(unittest.TestCase):
    def setUp(self):
        self.fixture=delegation.MemoryDelegationTests();self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.native=self.fixture.fixture
        self.reference=self.native.remember('SyntheticCanonicalCurrentMarker','canonical-current','project')['reference']
        self.root=self.fixture.root/'LIFEOS/MEMORY'
        self.module=self.fixture.root/'LIFEOS/TOOLS/Cortex.ts'

    def call(self,command='export',*,context=True,root=None,query='SyntheticCanonicalCurrentMarker SyntheticCanonicalReplacementMarker'):
        chosen=str(root or self.root)
        program='import {runCortex} from '+json.dumps(str(self.module))+';\n' \
            +'const status=await runCortex(["search",'+json.dumps(query)+',"--memory-root",'+json.dumps(chosen)+']);\n' \
            +'const id=status.envelope.data?.items?.[0]?.id;\n' \
            +'const result=await runCortex(['+json.dumps(command)+',...(id?[id]:[]),"--memory-root",'+json.dumps(chosen)+']);\n' \
            +'console.log(JSON.stringify({status,result}));'
        environment=dict(os.environ,HOME=str(self.native.home),BUN_CONFIG_NO_AUTO_INSTALL='1')
        environment.pop('LIFEOS_MEMORY_INTERNAL',None);environment.pop('LIFEOS_MEMORY_CONTEXT',None)
        if context:environment['LIFEOS_MEMORY_CONTEXT']=json.dumps(asdict(self.fixture.context))
        process=subprocess.run(['bun','--no-install','-e',program],env=environment,capture_output=True,text=True,timeout=30)
        self.assertEqual(process.returncode,0,process.stderr)
        self.assertEqual(process.stderr,'')
        return json.loads(process.stdout)

    def test_missing_caller_context_cannot_read_managed_canonical_records(self):
        result=self.call(context=False)
        self.assertFalse(result['status']['envelope']['ok'],result)
        self.assertNotIn('SyntheticCanonicalCurrentMarker',json.dumps(result))

    def test_owner_preserves_native_canonical_identity_and_content(self):
        result=self.call()
        self.assertTrue(result['result']['envelope']['ok'],result)
        record=result['result']['envelope']['data']['items'][0]
        self.assertEqual(record['type'],'research')
        self.assertTrue(record['id'].startswith('kb_'))
        self.assertIn('SyntheticCanonicalCurrentMarker',record['content'])
        self.assertEqual(record['provenance']['path'],'KNOWLEDGE/Research/synthetic-lab-routing.md')

    def test_correction_exports_current_fact_without_retired_native_section(self):
        receipt=self.native.memory.correct(OWNER,self.reference,'SyntheticCanonicalReplacementMarker','canonical-correct')
        self.assertEqual(receipt['status'],'committed',receipt)
        result=self.call()
        self.assertTrue(result['result']['envelope']['ok'],result)
        record=result['result']['envelope']['data']['items'][0]
        self.assertIn('SyntheticCanonicalReplacementMarker',record['content'])
        self.assertNotIn('SyntheticCanonicalCurrentMarker',json.dumps(result))

    def test_unregistered_native_fact_is_not_silently_admitted(self):
        self.native.memory._native('add',item={'type':'knowledge','entity_type':'research',
            'name':'SyntheticCanonicalUnregistered','content':'SyntheticCanonicalUnregisteredMarker'})
        result=self.call(query='SyntheticCanonicalUnregisteredMarker')
        self.assertTrue(result['status']['envelope']['ok'],result)
        self.assertEqual(result['status']['envelope']['data']['total'],0)
        self.assertNotIn('SyntheticCanonicalUnregisteredMarker',json.dumps(result))

    def test_native_root_option_does_not_grant_foreign_source_authority(self):
        foreign=self.native.home/'foreign-corpus';foreign.mkdir()
        (foreign/'note.md').write_text('---\nid: foreign\ncreated: 2026-10-01\n---\nSyntheticCanonicalForeignMarker')
        result=self.call(root=foreign)
        self.assertFalse(result['status']['envelope']['ok'],result)
        self.assertNotIn('SyntheticCanonicalForeignMarker',json.dumps(result))

    def test_changed_binding_revokes_native_canonical_reads(self):
        self.fixture.configuration.update(lambda config:config['accounts'].pop('chat-a:100'))
        result=self.call()
        self.assertFalse(result['status']['envelope']['ok'],result)
        self.assertNotIn('SyntheticCanonicalCurrentMarker',json.dumps(result))

    def test_unmanaged_control_retains_native_read_behavior(self):
        (self.fixture.root/'LIFEOS/USER/CONFIG/memory-access.json').unlink()
        result=self.call(context=False)
        self.assertTrue(result['result']['envelope']['ok'],result)
        self.assertIn('SyntheticCanonicalCurrentMarker',json.dumps(result))

    def test_fixed_native_metadata_names_are_not_retired_facts(self):
        saved=self.native.remember('RULE: status','canonical-fixed-field','principal')['reference']
        self.native.memory.forget(OWNER,saved,'canonical-retire-fixed-field')
        result=self.call()
        self.assertTrue(result['result']['envelope']['ok'],result)

    def test_retired_dynamic_title_remains_excluded(self):
        saved=self.native.remember('RULE: Synthetic lab routing','canonical-title','principal')['reference']
        self.native.memory.forget(OWNER,saved,'canonical-retire-title')
        result=self.call()
        self.assertFalse(result['status']['envelope']['ok'],result)
        self.assertNotIn('Synthetic lab routing',json.dumps(result))

    def test_native_type_directory_is_operational_metadata(self):
        saved=self.native.remember('RULE: research','canonical-type-field','principal')['reference']
        self.native.memory.forget(OWNER,saved,'canonical-retire-type-field')
        result=self.call()
        self.assertTrue(result['result']['envelope']['ok'],result)

    def test_forgotten_archive_fact_is_not_exported_from_retained_file(self):
        self.native.memory.forget(OWNER,self.reference,'canonical-forget')
        result=self.call()
        self.assertTrue(result['status']['envelope']['ok'],result)
        self.assertEqual(result['status']['envelope']['data']['total'],0)
        self.assertNotIn('SyntheticCanonicalCurrentMarker',json.dumps(result))

    def test_project_only_context_cannot_collect_unclassified_canonical_metadata(self):
        self.fixture.configuration.update(lambda config:config['destinations']['chat-a:200'].update(
            read=['project'],write=['project'],projects=['lab']))
        result=self.call()
        self.assertFalse(result['status']['envelope']['ok'],result)
        self.assertNotIn('SyntheticCanonicalCurrentMarker',json.dumps(result))

    def test_changed_native_fact_cannot_be_admitted_under_an_old_reference(self):
        record=self.native.memory.get(OWNER,self.reference)
        source=next((self.root/'KNOWLEDGE/Research').glob('*.md'))
        source.write_text(source.read_text().replace(record['content'],'SyntheticCanonicalOutsideMutation'))
        result=self.call()
        self.assertFalse(result['status']['envelope']['ok'],result)
        self.assertNotIn('SyntheticCanonicalOutsideMutation',json.dumps(result))

    def test_native_status_timeline_and_rebuild_use_the_governed_corpus(self):
        record=self.call()['result']['envelope']['data']['items'][0]
        cases=[['status'],['timeline','--anchor',record['id']],['rebuild','--from-canonical'],
               ['get',record['id']],['export',record['id']]]
        program='import {runCortex,validateCortexEnvelope} from '+json.dumps(str(self.module))+';\n' \
            +'const results=[];for(const args of '+json.dumps(cases)+'){\n' \
            +'const result=await runCortex([...args,"--memory-root",'+json.dumps(str(self.root))+']);\n' \
            +'if(validateCortexEnvelope(result.envelope).length)throw new Error("Invalid native envelope");results.push(result);}\n' \
            +'console.log(JSON.stringify(results));'
        environment=dict(os.environ,HOME=str(self.native.home),BUN_CONFIG_NO_AUTO_INSTALL='1',
                         LIFEOS_MEMORY_CONTEXT=json.dumps(asdict(self.fixture.context)))
        environment.pop('LIFEOS_MEMORY_INTERNAL',None)
        process=subprocess.run(['bun','--no-install','-e',program],env=environment,capture_output=True,text=True,timeout=30)
        self.assertEqual(process.returncode,0,process.stderr)
        self.assertEqual(process.stderr,'')
        results=json.loads(process.stdout)
        self.assertTrue(all(result['envelope']['ok'] for result in results),results)
        self.assertEqual(results[0]['envelope']['data']['canonical']['records'],1)
        self.assertEqual(results[1]['envelope']['data']['total'],1)
        self.assertTrue(results[2]['envelope']['data']['equivalent'])
        self.assertEqual(results[3]['envelope']['data']['items'],results[4]['envelope']['data']['items'])

    def test_known_knowledge_root_preserves_native_relative_provenance(self):
        result=self.call(root=self.root/'KNOWLEDGE')
        self.assertTrue(result['result']['envelope']['ok'],result)
        self.assertEqual(result['result']['envelope']['data']['items'][0]['provenance']['path'],
                         'Research/synthetic-lab-routing.md')

    def test_oversized_source_refuses_before_native_fact_read(self):
        from lifeos_hook_bridge.memory_canonical import corpus
        from lifeos_hook_bridge.memory_access import MemoryUnavailable
        source=next((self.root/'KNOWLEDGE/Research').glob('*.md'))
        with source.open('ab') as stream:stream.truncate(8*1024*1024+1)
        with self.assertRaisesRegex(MemoryUnavailable,'native file limit'):
            corpus(self.native.memory,OWNER,str(self.root))

    def test_duplicate_native_ids_refuse_in_managed_and_standalone_corpora(self):
        import re
        self.native.memory.remember(OWNER,category='project',content='SyntheticCanonicalSecondMarker',
                                    title='Synthetic second canonical',project='lab',request_id='canonical-second')
        sources=list((self.root/'KNOWLEDGE/Research').glob('*.md'))
        identifier=re.search(r'^id:.*$',sources[0].read_text(),flags=re.MULTILINE).group()
        for source in sources:
            self.assertEqual(len(re.search(r'^id:.*$',source.read_text(),flags=re.MULTILINE).group()),len(identifier))
            source.write_text(re.sub(r'^id:.*$',identifier,source.read_text(),flags=re.MULTILINE))
        managed=self.call()
        self.assertFalse(managed['status']['envelope']['ok'],managed)
        (self.fixture.root/'LIFEOS/USER/CONFIG/memory-access.json').unlink()
        standalone=self.call(context=False)
        self.assertFalse(standalone['status']['envelope']['ok'],standalone)


if __name__=='__main__':unittest.main()
