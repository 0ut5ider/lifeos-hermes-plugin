# ABOUTME: Tests reviewed import admission at actual ownership service and backup boundaries.
# ABOUTME: Requires current native references before a prepared store can replace built-in memory.
import unittest

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
                    'category':'preference' if source['path'].endswith('USER.md') else 'project',
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
