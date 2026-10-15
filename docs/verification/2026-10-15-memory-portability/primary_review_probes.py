# ABOUTME: Reproduces portability boundary defects using synthetic profile files.
# ABOUTME: Records real export and return results without changing shared product code.
import json
from pathlib import Path
import sys
import unittest
from types import SimpleNamespace

from ruamel.yaml import YAML
from lifeos_hook_bridge.memory_import_sources import upload_bundle
from lifeos_hook_bridge.memory_return import MemoryReturn
import test_memory_export as fixture

OUT=Path(__file__).parent
RESULTS={}

class ReturnConfigurationReview(unittest.TestCase):
    def test_aliases_do_not_change_unrelated_settings(self):
        operation=MemoryReturn.__new__(MemoryReturn)
        operation.importer=SimpleNamespace(installed=Path('/synthetic/native'))
        source=b'''model: synthetic-model
other_selection: &shared [lifeos, other]
other_entry: &entry {enabled: true, custom: keep}
plugins:
  enabled: *shared
  entries:
    lifeos: *entry
    other: *entry
memory:
  provider: lifeos-hook-bridge
'''
        before=YAML(typ='safe').load(source)
        output=operation._configuration(source)
        after=YAML(typ='safe').load(output)
        RESULTS['aliases']={'before':before,'after':after,'output':output.decode()}
        self.assertEqual(after['other_selection'],before['other_selection'])
        self.assertEqual(after['other_entry'],before['other_entry'])
        self.assertEqual(after['plugins']['entries']['other'],before['plugins']['entries']['other'])

class ExportReview(unittest.TestCase):
    def setUp(self):
        self.fixture=fixture.MemoryExportTests();self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)

    def test_retained_export_can_be_imported_as_a_portable_source(self):
        source='Synthetic retained source. '+('a'*70000)
        (self.fixture.fixture.sources/'MEMORY.md').write_text(source)
        review,saved=self.fixture.prepare()
        choices=[{'id':item['id'],'action':'retain','required':False,'reason':'Keep complete source outside active memory.'} for item in review['items']]
        plan=self.fixture.operation().plan(self.fixture.snapshot,saved['signature'],choices,account='dashboard:owner')
        result=self.fixture.operation().apply(self.fixture.snapshot,saved['signature'],plan['signature'],account='dashboard:owner')
        bundle=json.loads(self.fixture.operation().download(self.fixture.snapshot,saved['signature'],account='dashboard:owner'))
        RESULTS['retained_export']={'source_bytes':len(source.encode()),'export_state':result['state'],
            'bundle_bytes':len((self.fixture.snapshot/'portable-memory.json').read_bytes())}
        try:upload_bundle(self.fixture.profile,{'label':'Synthetic round trip','bundle':bundle})
        except ValueError as error:
            RESULTS['retained_export']['import_error']=str(error)
            raise

    def test_accepted_bundle_total_fits_portable_upload(self):
        entries=['Synthetic source '+str(index)+'. '+('a'*29970) for index in range(20)]
        (self.fixture.fixture.sources/'MEMORY.md').write_text('\n§\n'.join(entries))
        review,saved=self.fixture.prepare()
        choices=[{'id':item['id'],'action':'retain','required':False,'reason':'Retain the complete source.'} for item in review['items']]
        plan=self.fixture.operation().plan(self.fixture.snapshot,saved['signature'],choices,account='dashboard:owner')
        result=self.fixture.operation().apply(self.fixture.snapshot,saved['signature'],plan['signature'],account='dashboard:owner')
        raw=self.fixture.operation().download(self.fixture.snapshot,saved['signature'],account='dashboard:owner')
        RESULTS['bundle_total']={'item_content_max':max(len(item['content']) for item in review['items']),
            'item_content_total':sum(len(item['content']) for item in review['items']),
            'export_state':result['state'],'bundle_bytes':len(raw)}
        try:upload_bundle(self.fixture.profile,{'label':'Synthetic size round trip','bundle':json.loads(raw)})
        except ValueError as error:
            RESULTS['bundle_total']['import_error']=str(error)
            raise

    def test_edit_to_later_output_is_preserved_during_export(self):
        review,saved=self.fixture.prepare()
        plan=self.fixture.operation().plan(self.fixture.snapshot,saved['signature'],self.fixture.decisions(review),account='dashboard:owner')
        first=self.fixture.snapshot/'hermes/MEMORY.md'
        later=self.fixture.snapshot/'hermes/USER.md'
        marker=b'Synthetic later owner edit.'
        edited=False
        def trace(frame,event,arg):
            nonlocal edited
            if (not edited and event=='return' and frame.f_code.co_name=='publish'
                    and frame.f_code.co_filename.endswith('/memory_transaction.py')
                    and frame.f_locals.get('path')==first):
                later.write_bytes(marker)
                edited=True
            return trace
        try:
            sys.settrace(trace)
            result=self.fixture.operation().apply(self.fixture.snapshot,saved['signature'],plan['signature'],account='dashboard:owner')
        finally:sys.settrace(None)
        RESULTS['later_output']={'edit_injected':edited,'state':result['state'],'actual':later.read_text(),'expected':marker.decode()}
        self.assertTrue(edited)
        self.assertEqual(later.read_bytes(),marker)


def tearDownModule():
    (OUT/'probe-results.json').write_text(json.dumps(RESULTS,indent=2)+'\n')
