# ABOUTME: Verifies portability review fixes and boundary variants with synthetic profiles.
# ABOUTME: Saves measured provenance, file identity, and bundle accounting results.
import base64
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

from ruamel.yaml import YAML
from lifeos_hook_bridge.memory_access import MemoryConflict
from lifeos_hook_bridge.memory_import import MemoryImport
from lifeos_hook_bridge.memory_import_sources import directory, upload, upload_bundle
from lifeos_hook_bridge.memory_return import MemoryReturn
import test_memory_export as fixture

OUT=Path(__file__).parent
RESULTS={}

class ConfigurationClosure(unittest.TestCase):
    def test_disabled_list_and_entries_map_aliases_preserve_unrelated_values(self):
        operation=MemoryReturn.__new__(MemoryReturn)
        operation.importer=SimpleNamespace(installed=Path('/synthetic/native'))
        source=b'''unrelated_disabled: &disabled [unrelated-disabled]
unrelated_entries: &entries
  lifeos: {enabled: true, custom: keep-lifeos}
  lifeos-hook-bridge: {enabled: true, custom: keep-bridge}
  other: {enabled: true, custom: keep-other}
plugins:
  enabled: [lifeos, lifeos-hook-bridge, other]
  disabled: *disabled
  entries: *entries
memory:
  provider: lifeos-hook-bridge
'''
        before=YAML(typ='safe').load(source)
        after=YAML(typ='safe').load(operation._configuration(source))
        for key in ('unrelated_disabled','unrelated_entries'):
            self.assertEqual(before[key],after[key])
        self.assertEqual(after['plugins']['entries']['other'],before['plugins']['entries']['other'])
        self.assertFalse(after['plugins']['entries']['lifeos']['enabled'])
        self.assertFalse(after['plugins']['entries']['lifeos-hook-bridge']['enabled'])
        self.assertEqual(after['plugins']['disabled'],['unrelated-disabled','lifeos','lifeos-hook-bridge'])
        RESULTS['alias_map_and_disabled']={'before':before,'after':after}

    def test_merged_entry_does_not_change_its_source(self):
        operation=MemoryReturn.__new__(MemoryReturn)
        operation.importer=SimpleNamespace(installed=Path('/synthetic/native'))
        source=b'''unrelated_entry: &defaults {enabled: true, custom: keep}
plugins:
  entries:
    lifeos:
      <<: *defaults
    other: *defaults
memory:
  provider: lifeos-hook-bridge
'''
        before=YAML(typ='safe').load(source)
        after=YAML(typ='safe').load(operation._configuration(source))
        self.assertEqual(before['unrelated_entry'],after['unrelated_entry'])
        self.assertEqual(before['plugins']['entries']['other'],after['plugins']['entries']['other'])
        self.assertFalse(after['plugins']['entries']['lifeos']['enabled'])
        RESULTS['merged_entry']={'before':before,'after':after}

class ExportClosure(unittest.TestCase):
    def setUp(self):
        self.fixture=fixture.MemoryExportTests();self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)

    def retained(self):
        review,saved=self.fixture.prepare()
        choices=[{'id':item['id'],'action':'retain','required':False,'reason':'Retain complete source.'} for item in review['items']]
        plan=self.fixture.operation().plan(self.fixture.snapshot,saved['signature'],choices,account='dashboard:owner')
        self.fixture.operation().apply(self.fixture.snapshot,saved['signature'],plan['signature'],account='dashboard:owner')
        return review,saved,plan,self.fixture.operation().download(self.fixture.snapshot,saved['signature'],account='dashboard:owner')

    def test_large_bundle_upload_snapshot_and_plan_preserve_exact_bytes_and_accounting(self):
        entries=['Synthetic source '+str(index)+'. '+('a'*29970) for index in range(20)]
        (self.fixture.fixture.sources/'MEMORY.md').write_text('\n§\n'.join(entries))
        review,saved,plan,raw=self.retained()
        self.assertGreater(len(raw),1024*1024)
        # Preserve a noncanonical original serialization and its final newline.
        original=json.dumps(json.loads(raw),ensure_ascii=False,separators=(',',':')).encode()+b'\n\n'
        staged=upload_bundle(self.fixture.profile,{'label':'Synthetic exact-byte bundle',
            'bundle_bytes':base64.b64encode(original).decode()})
        source=directory(self.fixture.profile,staged['identifier'],source=True)
        self.assertEqual((source/'portable-memory.json').read_bytes(),original)
        operation=MemoryImport(self.fixture.configuration,source_directory=source)
        imported=operation.preview(account='dashboard:owner')
        destination=self.fixture.fixture.fixture.home/'large-bundle-import-review'
        captured=operation.prepare(destination,imported['signature'],account='dashboard:owner')
        inspected=operation.inspect(destination,captured['snapshot_signature'],account='dashboard:owner')
        self.assertEqual((destination/'sources/portable-memory.json').read_bytes(),original)
        chunks=imported['sources'][0]['chunks']
        self.assertEqual(len(chunks),len(review['items']))
        choices=[{'id':item['id'],'action':'pending','required':False,'reason':'Retain for review.'} for item in chunks]
        planned=operation.plan(destination,captured['snapshot_signature'],choices,account='dashboard:owner')
        self.assertEqual(len(planned['items']),len(chunks))
        for old,new in zip(review['items'],chunks,strict=True):
            self.assertEqual(old['origin'],new['source_origin'])
            self.assertEqual(old['reference'],new['source_reference'])
            self.assertEqual(old['content'],new['content'])
        RESULTS['large_bundle']={'download_bytes':len(raw),'original_uploaded_bytes':len(original),
            'sha256':hashlib.sha256(original).hexdigest(),'item_count':len(chunks),
            'snapshot_exact':True,'inspected_item_count':len(inspected['review']['sources'][0]['chunks']),
            'planned_item_count':len(planned['items']),'provenance_exact':True}

    def test_edit_to_first_output_after_publication_is_detected_before_receipt(self):
        review,saved=self.fixture.prepare()
        plan=self.fixture.operation().plan(self.fixture.snapshot,saved['signature'],self.fixture.decisions(review),account='dashboard:owner')
        first=self.fixture.snapshot/'hermes/MEMORY.md'
        last=self.fixture.snapshot/'portable-memory.json'
        marker=b'Synthetic later edit to already-published first output.'
        injected=False
        def trace(frame,event,arg):
            nonlocal injected
            if (not injected and event=='return' and frame.f_code.co_name=='publish'
                    and frame.f_code.co_filename.endswith('/memory_transaction.py') and frame.f_locals.get('path')==last):
                first.write_bytes(marker);first.chmod(0o600);injected=True
            return trace
        try:
            sys.settrace(trace)
            with self.assertRaisesRegex(MemoryConflict,'verification'):
                self.fixture.operation().apply(self.fixture.snapshot,saved['signature'],plan['signature'],account='dashboard:owner')
        finally:sys.settrace(None)
        self.assertTrue(injected)
        self.assertEqual(first.read_bytes(),marker)
        self.assertFalse((self.fixture.snapshot/'export-receipt.json').exists())
        RESULTS['first_output_edit']={'edit_injected':True,'preserved':True,'success_receipt':False}

    def test_many_bounded_provenance_receipts_remain_importable(self):
        content='Synthetic repeated import source with bounded provenance.'
        for index in range(20):
            source={'kind':'hermes-import','session':'','path':'/synthetic/source/'+('a'*100)+'/MEMORY.md',
                'digest':'a'*64,'occurrence':str(index)+'b'*62,'original_author':'unknown','original_date':'unknown',
                'origin':{'kind':'hermes-files','label':'Synthetic source '+str(index)+' '+('x'*220),
                    'path':'/synthetic/source/'+('b'*100),'digest':'c'*64}}
            result=self.fixture.native.remember(self.fixture.scope,category='project',content=content,
                title='Synthetic repeat import',project='lab',request_id='synthetic-multi-source-'+str(index),source=source)
            self.assertIn(result['status'],('committed','unchanged'))
        review,saved,plan,raw=self.retained()
        selected=next(item for item in review['items'] if item['content']==content)
        origin_bytes=len(json.dumps(selected['origin'],sort_keys=True,indent=2,ensure_ascii=False).encode())+1
        RESULTS['many_origins']={'receipt_count':len(selected['origin']['receipts']),
            'origin_bytes':origin_bytes,'bundle_bytes':len(raw),'export_state':'exported'}
        try:upload_bundle(self.fixture.profile,{'label':'Synthetic repeated import provenance','bundle':json.loads(raw)})
        except ValueError as error:
            RESULTS['many_origins']['import_error']=str(error)
            raise

    def test_imported_native_fact_export_provenance_chain_measurement(self):
        original=b'\xef\xbb\xbf Synthetic source provenance fact.\r\n'
        staged=upload(self.fixture.profile,{'label':'Synthetic source system identity',
            'files':{'MEMORY.md':base64.b64encode(original).decode()}})
        operation=MemoryImport(self.fixture.configuration,source_directory=directory(self.fixture.profile,staged['identifier'],source=True))
        review=operation.preview(account='dashboard:owner')
        destination=self.fixture.fixture.fixture.home/'source-provenance-import'
        saved=operation.prepare(destination,review['signature'],account='dashboard:owner')
        chunk=review['sources'][0]['chunks'][0]
        plan=operation.plan(destination,saved['snapshot_signature'],[{'id':chunk['id'],'action':'import','required':True,
            'category':'project','project':'lab','title':'Synthetic upstream provenance','content':chunk['content']}],account='dashboard:owner')
        result=operation.apply(destination,saved['snapshot_signature'],plan['signature'],account='dashboard:owner')
        self.assertEqual(result['state'],'published')
        receipt=result['items'][0]['receipt']
        exported=self.fixture.operation().preview(account='dashboard:owner')
        item=next(item for item in exported['items'] if item['reference']==receipt['reference'])
        RESULTS['imported_fact_provenance']={'import_receipt_source':receipt['source'],'export_item_origin':item['origin'],
            'original_source_label_present_in_export':staged['identifier'] in json.dumps(item),
            'upstream_digest_present_in_export':hashlib.sha256(original).hexdigest() in json.dumps(item)}
        self.assertEqual(receipt['source']['origin']['label'],'Synthetic source system identity')
        self.assertIn({'reference':receipt['reference'],'source':receipt['source']},item['origin']['receipts'])


def tearDownModule():
    (OUT/'closure-control-results.json').write_text(json.dumps(RESULTS,indent=2)+'\n')
