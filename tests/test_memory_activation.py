# ABOUTME: Tests reviewed import admission at actual ownership service and backup boundaries.
# ABOUTME: Requires current native references before a prepared store can replace built-in memory.
import unittest
import json
import os
from pathlib import Path
import subprocess
import sys

import test_ownership_setup as setup_fixture
from lifeos_hook_bridge.memory_access import MemoryUnavailable


class MemoryActivationTests(unittest.TestCase):
    def setUp(self):
        self.setup=setup_fixture.OwnershipSetupTests();self.setup.setUp()
        self.addCleanup(self.setup.doCleanups)
        self.configuration=self.setup.configuration
        from lifeos_hook_bridge.memory_import import MemoryImport
        self.importer=MemoryImport(self.configuration)
        review=self.importer.preview(account='dashboard:owner')
        self.snapshot=self.setup.backup.fixture.fixture.home/'import-review'
        self.captured=self.importer.prepare(self.snapshot,review['signature'],account='dashboard:owner')
        decisions=[{'id':item['id'],'action':'import','required':True,
                    'category':'principal' if source['path'].endswith('USER.md') else 'project',
                    'project':'lab','title':'Synthetic activation review','content':item['content']}
                   for source in review['sources'] for item in source['chunks'] if item['content']]
        self.plan=self.importer.plan(self.snapshot,self.captured['snapshot_signature'],decisions,account='dashboard:owner')

    def operation(self):
        from lifeos_hook_bridge.memory_activation import MemoryActivation
        return MemoryActivation(self.configuration,units=self.setup.services.units)

    def publish(self):
        return self.importer.apply(self.snapshot,self.captured['snapshot_signature'],self.plan['signature'],account='dashboard:owner')

    def prepare(self):
        return self.operation().prepare(self.snapshot,self.captured['snapshot_signature'],self.plan['signature'],
            self.setup.backup.destination,account='dashboard:owner')

    def test_activation_requires_published_import_and_current_required_references(self):
        with self.assertRaises(MemoryUnavailable):self.prepare()
        publication=self.publish();review=self.prepare()
        self.assertEqual(review['state'],'ready')
        item=publication['items'][0]
        self.importer.memory.correct(setup_fixture.native_fixture.OWNER,item['receipt']['reference'],
            'Synthetic correction after ownership review','activation-later')
        before=self.setup.pids()
        with self.assertRaises(MemoryUnavailable):
            self.operation().apply(review['signature'],account='dashboard:owner')
        self.assertEqual(before,self.setup.pids())
        self.assertFalse(self.configuration.load()['ownership_enabled'])

    def test_activation_uses_real_backup_and_services_and_preserves_original_sources(self):
        publication=self.publish();review=self.prepare()
        profile=self.configuration.path.parent
        before={name:(profile/'memories'/name).read_bytes() for name in ('MEMORY.md','USER.md')}
        result=self.operation().apply(review['signature'],account='dashboard:owner')
        self.assertEqual(result['state'],'configured')
        self.assertFalse(result['application_verified'])
        self.assertTrue(self.configuration.load()['ownership_enabled'])
        self.assertTrue(all(pid!='0' for pid in self.setup.pids().values()))
        for name,data in before.items():self.assertEqual((profile/'memories'/name).read_bytes(),data)
        self.assertEqual(len(publication['items']),2)

    def test_fresh_claim_prepares_missing_connector_without_selecting_it(self):
        path=Path(self.configuration.load()['root'])/'LIFEOS/USER/CONFIG/memory-access.json'
        path.unlink();self.publish();review=self.prepare()
        self.assertEqual(review['state'],'ready');self.assertFalse(path.exists())
        result=self.operation().apply(review['signature'],account='dashboard:owner')
        self.assertEqual(result['state'],'configured');self.assertTrue(path.is_file())
        from lifeos_hook_bridge.memory_administration import _connector
        _connector(self.configuration,self.configuration.load())
        returned=self.operation().recover(account='dashboard:owner')
        self.assertEqual(returned['state'],'returned');self.assertFalse(path.exists())
        self.assertFalse(self.configuration.load()['ownership_enabled'])

    def test_fresh_claim_keeps_later_connector_edits_before_application(self):
        path=Path(self.configuration.load()['root'])/'LIFEOS/USER/CONFIG/memory-access.json'
        path.unlink();self.publish();review=self.prepare();path.write_text('Synthetic later owner connector')
        before=self.setup.pids()
        with self.assertRaises(MemoryUnavailable):self.operation().apply(review['signature'],account='dashboard:owner')
        self.assertEqual(path.read_text(),'Synthetic later owner connector');self.assertEqual(self.setup.pids(),before)

    def test_exit_after_connector_publication_restores_original_absence(self):
        path=Path(self.configuration.load()['root']).parent/'.config/LIFEOS/USER/CONFIG/memory-access.json'
        path.unlink();self.publish();review=self.prepare()
        code='''import json,os,sys
from pathlib import Path
from lifeos_hook_bridge.memory_service import MemoryConfiguration
from lifeos_hook_bridge.memory_activation import MemoryActivation
settings=json.load(sys.stdin)
def trace(frame,event,argument):
 if event=='return' and frame.f_code.co_name=='publish' and frame.f_locals.get('path')==Path(settings['connector']):os._exit(73)
 return trace
sys.settrace(trace)
MemoryActivation(MemoryConfiguration(Path(settings['configuration'])),units=settings['units']).apply(settings['signature'],account='dashboard:owner')
'''
        settings={'configuration':str(self.configuration.path),'units':self.setup.services.units,
            'connector':str(path),'signature':review['signature']}
        result=subprocess.run([sys.executable,'-c',code],input=json.dumps(settings),text=True,capture_output=True,
            env=os.environ.copy(),timeout=30)
        self.assertEqual(result.returncode,73,result.stdout+result.stderr);self.assertEqual(result.stdout+result.stderr,'')
        self.assertTrue(path.is_file());self.assertFalse(self.configuration.load()['ownership_enabled'])
        returned=self.operation().recover(account='dashboard:owner')
        self.assertEqual(returned['state'],'returned');self.assertFalse(path.exists())
        self.assertTrue(all(pid!='0' for pid in self.setup.pids().values()))

    def test_connector_edit_after_ownership_publication_cannot_report_configured(self):
        path=Path(self.configuration.load()['root']).parent/'.config/LIFEOS/USER/CONFIG/memory-access.json'
        path.unlink();self.publish();review=self.prepare();edited=False
        def trace(frame,event,argument):
            nonlocal edited
            if (not edited and event=='return' and frame.f_code.co_name=='publish'
                    and frame.f_locals.get('path')==self.configuration.path):
                edited=True;path.write_text('Synthetic later connector edit')
            return trace
        sys.settrace(trace)
        try:
            with self.assertRaises(MemoryUnavailable):self.operation().apply(review['signature'],account='dashboard:owner')
        finally:sys.settrace(None)
        self.assertTrue(edited);self.assertEqual(path.read_text(),'Synthetic later connector edit')
