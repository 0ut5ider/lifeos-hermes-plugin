# ABOUTME: Checks reviewed reverse exports against actual native facts and Hermes memory files.
# ABOUTME: Exercises capacity, retirement, destination edits, and recoverable private artifacts.
from pathlib import Path
import unittest

import test_memory_import as fixture


class MemoryExportTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixture.MemoryImportTests();self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.profile=self.fixture.profile
        self.configuration=self.fixture.configuration
        self.native=self.fixture.fixture.memory
        self.scope=fixture.fixture.OWNER
        (self.fixture.sources/'MEMORY.md').write_text('Synthetic preserved Hermes entry.')
        self.saved=self.native.remember(self.scope,category='project',content='Synthetic newer LifeOS fact.',
            title='Synthetic export fact',project='lab',request_id='export-fact')
        self.snapshot=self.fixture.fixture.home/'export-review'

    def operation(self):
        from lifeos_hook_bridge.memory_export import MemoryExport
        return MemoryExport(self.configuration)

    def prepare(self):
        review=self.operation().preview(account='dashboard:owner')
        saved=self.operation().prepare(self.snapshot,review['signature'],account='dashboard:owner')
        return review,saved

    def decisions(self, review):
        return [{'id':item['id'],'action':'export','required':True,'file':'MEMORY.md',
            'content':item['content']} for item in review['items']]

    def test_export_preserves_current_facts_origins_and_original_sources_without_switching(self):
        review,saved=self.prepare()
        self.assertEqual(len(review['items']),2)
        plan=self.operation().plan(self.snapshot,saved['signature'],self.decisions(review),account='dashboard:owner')
        self.assertTrue(plan['ready_for_return'])
        result=self.operation().apply(self.snapshot,saved['signature'],plan['signature'],account='dashboard:owner')
        self.assertEqual(result['state'],'exported')
        target=self.snapshot/'hermes/MEMORY.md'
        self.assertEqual(target.read_text(),'Synthetic preserved Hermes entry.\n§\nSynthetic newer LifeOS fact.')
        self.assertEqual(target.stat().st_mode & 0o777,0o600)
        self.assertEqual((self.fixture.sources/'MEMORY.md').read_text(),'Synthetic preserved Hermes entry.')
        self.assertEqual(result,self.operation().apply(self.snapshot,saved['signature'],plan['signature'],account='dashboard:owner'))
        self.assertEqual(plan['items'][1]['source']['reference'],self.saved['reference'])
        self.assertEqual(self.native.get(self.scope,self.saved['reference'])['status'],'ok')
        self.assertFalse(self.configuration.load()['ownership_enabled'])

    def test_capacity_refuses_without_truncation_and_retained_overflow_stays_in_bundle(self):
        (self.profile/'config.yaml').write_text('memory:\n  memory_char_limit: 40\n')
        review,saved=self.prepare()
        with self.assertRaisesRegex(ValueError,'capacity'):
            self.operation().plan(self.snapshot,saved['signature'],self.decisions(review),account='dashboard:owner')
        decisions=self.decisions(review)
        decisions[1]={'id':review['items'][1]['id'],'action':'retain','required':False,'reason':'Keep outside active Hermes memory.'}
        plan=self.operation().plan(self.snapshot,saved['signature'],decisions,account='dashboard:owner')
        self.assertTrue(plan['ready_for_return'])
        self.assertEqual(plan['items'][1]['source']['content'],'Synthetic newer LifeOS fact.')
        self.assertEqual(plan['files']['MEMORY.md'],'Synthetic preserved Hermes entry.')

    def test_later_native_correction_or_destination_edit_refuses_export(self):
        review,saved=self.prepare()
        plan=self.operation().plan(self.snapshot,saved['signature'],self.decisions(review),account='dashboard:owner')
        self.native.correct(self.scope,self.saved['reference'],'Synthetic later correction.','correct-export')
        from lifeos_hook_bridge.memory_access import MemoryUnavailable
        with self.assertRaises(MemoryUnavailable):
            self.operation().apply(self.snapshot,saved['signature'],plan['signature'],account='dashboard:owner')
        self.assertFalse((self.snapshot/'hermes').exists())

    def test_required_retained_item_blocks_return_and_unsafe_delimiter_is_refused(self):
        review,saved=self.prepare()
        decisions=self.decisions(review)
        decisions[1]={'id':review['items'][1]['id'],'action':'retain','required':True,'reason':'Review later.'}
        plan=self.operation().plan(self.snapshot,saved['signature'],decisions,account='dashboard:owner')
        self.assertFalse(plan['ready_for_return'])
        self.snapshot=self.fixture.fixture.home/'delimiter-review'
        review,saved=self.prepare()
        decisions=self.decisions(review);decisions[0]['content']='Synthetic first\n§\nSynthetic injected second'
        with self.assertRaises(ValueError):
            self.operation().plan(self.snapshot,saved['signature'],decisions,account='dashboard:owner')

    def test_retired_claim_in_preserved_hermes_memory_cannot_be_reactivated_by_export(self):
        content='Synthetic preserved Hermes entry.'
        saved=self.native.remember(self.scope,category='project',content=content,title='Retired source',project='lab',request_id='retired-export')
        self.native.forget(self.scope,saved['reference'],'forget-export')
        review,snapshot=self.prepare()
        self.assertTrue(review['items'][0]['retired_claim'])
        with self.assertRaises(ValueError):
            self.operation().plan(self.snapshot,snapshot['signature'],self.decisions(review),account='dashboard:owner')

    def test_portable_bundle_import_includes_retained_facts_with_provenance_and_literal_delimiters(self):
        import json
        from lifeos_hook_bridge.memory_import_sources import upload_bundle, directory
        from lifeos_hook_bridge.memory_import import MemoryImport
        literal='Synthetic retained first\n§\nSynthetic retained second'
        corrected=self.native.correct(self.scope,self.saved['reference'],literal,'literal-export')
        review,saved=self.prepare()
        decisions=[{'id':item['id'],'action':'retain','required':False,'reason':'Retain full source.'} for item in review['items']]
        plan=self.operation().plan(self.snapshot,saved['signature'],decisions,account='dashboard:owner')
        self.operation().apply(self.snapshot,saved['signature'],plan['signature'],account='dashboard:owner')
        bundle=json.loads(self.operation().download(self.snapshot,saved['signature'],account='dashboard:owner'))
        source=upload_bundle(self.profile,{'label':'Synthetic portable source','bundle':bundle})
        operation=MemoryImport(self.configuration,source_directory=directory(self.profile,source['identifier'],source=True))
        imported=operation.preview(account='dashboard:owner')
        self.assertEqual(len(imported['sources']),1)
        chunks=imported['sources'][0]['chunks']
        self.assertEqual(len(chunks),2)
        self.assertEqual(chunks[1]['content'],literal)
        self.assertEqual(chunks[1]['source_reference'],corrected['reference'])
        snapshot=self.fixture.fixture.home/'portable-import'
        captured=operation.prepare(snapshot,imported['signature'],account='dashboard:owner')
        choices=[{'id':item['id'],'action':'import','required':True,'category':'project','project':'lab',
            'content':item['content'],'title':'Synthetic bundle import'} for item in chunks]
        planned=operation.plan(snapshot,captured['snapshot_signature'],choices,account='dashboard:owner')
        result=operation.apply(snapshot,captured['snapshot_signature'],planned['signature'],account='dashboard:owner')
        self.assertEqual(result['state'],'published',result)
        self.assertEqual(result['items'][1]['receipt']['reference'],corrected['reference'])
        self.assertEqual((snapshot/'sources/portable-memory.json').read_bytes(),(directory(self.profile,source['identifier'],source=True)/'portable-memory.json').read_bytes())

    def test_portable_round_trip_retains_large_original_hermes_occurrences(self):
        import json
        from lifeos_hook_bridge.memory_import_sources import upload_bundle, directory
        from lifeos_hook_bridge.memory_import import MemoryImport
        text='Synthetic original '+('x'*70000)
        (self.fixture.sources/'MEMORY.md').write_text(text)
        review,saved=self.prepare()
        choices=[{'id':item['id'],'action':'retain','required':False,'reason':'Preserve full source.'} for item in review['items']]
        plan=self.operation().plan(self.snapshot,saved['signature'],choices,account='dashboard:owner')
        self.operation().apply(self.snapshot,saved['signature'],plan['signature'],account='dashboard:owner')
        bundle=self.operation().download(self.snapshot,saved['signature'],account='dashboard:owner')
        staged=upload_bundle(self.profile,{'label':'Synthetic large occurrence','bundle':json.loads(bundle)})
        operation=MemoryImport(self.configuration,source_directory=directory(self.profile,staged['identifier'],source=True))
        self.assertEqual(operation.preview(account='dashboard:owner')['sources'][0]['chunks'][0]['content'],text)

    def test_later_edit_to_second_output_is_preserved_during_publication(self):
        import sys
        from lifeos_hook_bridge.memory_access import MemoryConflict
        review,saved=self.prepare()
        plan=self.operation().plan(self.snapshot,saved['signature'],self.decisions(review),account='dashboard:owner')
        first=self.snapshot/'hermes/MEMORY.md';later=self.snapshot/'hermes/USER.md'
        marker=b'Synthetic later owner export edit.'
        def trace(frame,event,arg):
            if (event=='return' and frame.f_code.co_name=='publish' and frame.f_code.co_filename.endswith('/memory_transaction.py')
                    and frame.f_locals.get('path')==first):
                later.write_bytes(marker);later.chmod(0o600)
            return trace
        try:
            sys.settrace(trace)
            with self.assertRaises(MemoryConflict):
                self.operation().apply(self.snapshot,saved['signature'],plan['signature'],account='dashboard:owner')
        finally:sys.settrace(None)
        self.assertEqual(later.read_bytes(),marker)
        self.assertFalse((self.snapshot/'export-receipt.json').exists())

    def test_export_keeps_the_original_import_receipt_provenance(self):
        from lifeos_hook_bridge.memory_import import MemoryImport
        importer=MemoryImport(self.configuration)
        review=importer.preview(account='dashboard:owner')
        destination=self.fixture.fixture.home/'origin-import'
        saved=importer.prepare(destination,review['signature'],account='dashboard:owner')
        chunk=review['sources'][0]['chunks'][0]
        plan=importer.plan(destination,saved['snapshot_signature'],[{'id':chunk['id'],'action':'import','required':True,
            'category':'project','project':'lab','content':chunk['content'],'title':'Synthetic original source'}],account='dashboard:owner')
        result=importer.apply(destination,saved['snapshot_signature'],plan['signature'],account='dashboard:owner')
        receipt=result['items'][0]['receipt']
        exported=self.operation().preview(account='dashboard:owner')
        item=next(item for item in exported['items'] if item['reference']==receipt['reference'])
        self.assertIn({'reference':receipt['reference'],'source':receipt['source']},item['origin']['receipts'])
