# ABOUTME: Reviews repeated ownership selection, alias preservation, and cache backup boundaries.
# ABOUTME: Uses synthetic native records and actual service fixtures without changing product code.
import importlib
import os
from pathlib import Path
import sys
import unittest
from ruamel.yaml import YAML
from lifeos_hook_bridge.memory_access import MemoryUnavailable
from lifeos_hook_bridge.profile_backup import create, _exclusion
import test_memory_ownership as ownership_fixture
import test_memory_activation as activation_fixture
from lifeos_hook_bridge.memory_context import host_context
from lifeos_hook_bridge.memory_policy import MemoryPolicy


class AliasControls(unittest.TestCase):
    def setUp(self):
        self.fixture=ownership_fixture.MemoryOwnershipTests();self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        self.configuration=self.fixture.configuration;self.profile=self.configuration.path.parent

    def snapshot(self,text):
        (self.profile/'config.yaml').write_text(text)
        self.fixture.backup=create(self.configuration,self.fixture.fixture.fixture.fixture.home/'review-alias-backup',account='dashboard:owner')

    def test_leaf_aliases_preserve_foreign_values(self):
        native_skills=Path(self.configuration.load()['root'])/'skills';native_skills.mkdir(exist_ok=True)
        self.snapshot('''memory: {memory_enabled: true, user_profile_enabled: true}
foreign_enabled: &enabled [foreign-plugin]
foreign_disabled: &disabled [lifeos, lifeos-hook-bridge, foreign-disabled]
foreign_entry: &entry {enabled: false, marker: synthetic}
foreign_dirs: &directories [/synthetic/unrelated/skills]
plugins:
  enabled: *enabled
  disabled: *disabled
  entries: {lifeos: *entry, unrelated: *entry}
skills: {external_dirs: *directories}
''')
        self.fixture.apply();current=YAML(typ='safe').load((self.profile/'config.yaml').read_text())
        self.assertEqual(current['foreign_enabled'],['foreign-plugin'])
        self.assertEqual(current['foreign_disabled'],['lifeos','lifeos-hook-bridge','foreign-disabled'])
        self.assertFalse(current['foreign_entry']['enabled']);self.assertFalse(current['plugins']['entries']['unrelated']['enabled'])
        self.assertTrue(current['plugins']['entries']['lifeos']['enabled'])
        self.assertEqual(current['foreign_dirs'],['/synthetic/unrelated/skills'])
        self.assertEqual(current['skills']['external_dirs'],['/synthetic/unrelated/skills',str(native_skills)])

    def test_merged_plugin_selection_refuses_without_changes(self):
        self.snapshot('''memory: {memory_enabled: true, user_profile_enabled: true}
foreign: &foreign {enabled: [unrelated]}
plugins: {<<: *foreign}
''')
        before=(self.profile/'config.yaml').read_bytes()
        with self.assertRaises(MemoryUnavailable):self.fixture.preview()
        self.assertEqual((self.profile/'config.yaml').read_bytes(),before)
        self.assertFalse(self.configuration.load()['ownership_enabled'])

    def test_cache_link_is_not_excluded_as_regenerable(self):
        base=self.fixture.fixture.fixture.fixture.home;target=base/'synthetic-cache';target.mkdir()
        link=base/'synthetic-cache-link';link.symlink_to(target)
        self.assertIsNone(_exclusion('plugins/synthetic/__pycache__',link))
        self.assertIsNone(_exclusion('workspace/__pycache__',target))
        self.assertEqual(_exclusion('plugins/synthetic/__pycache__',target),'regenerable')


class ClaimedOwnerAdmission(unittest.TestCase):
    def test_fresh_dashboard_claim_activation_has_usable_local_owner_admission(self):
        fixture=activation_fixture.MemoryActivationTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
        fixture.configuration.update(lambda value:value.update(accounts={'dashboard:owner':'owner'},destinations={}))
        current=fixture.importer.preview(account='dashboard:owner')
        fixture.snapshot=fixture.setup.backup.fixture.fixture.home/'review-exact-claim-import'
        fixture.captured=fixture.importer.prepare(fixture.snapshot,current['signature'],account='dashboard:owner')
        decisions=[{'id':item['id'],'action':'import','required':True,
            'category':'principal' if source['path'].endswith('USER.md') else 'project','project':'lab',
            'title':'Synthetic exact dashboard claim','content':item['content']}
            for source in current['sources'] for item in source['chunks'] if item['content']]
        fixture.plan=fixture.importer.plan(fixture.snapshot,fixture.captured['snapshot_signature'],decisions,account='dashboard:owner')
        fixture.publish();review=fixture.prepare();result=fixture.operation().apply(review['signature'],account='dashboard:owner')
        self.assertEqual(result['state'],'configured')
        selected=fixture.configuration.load()
        context=host_context(selected,{'HERMES_SESSION_PLATFORM':'cli','HERMES_SESSION_ID':'synthetic-review'},
            model_route='synthetic-reviewed-route',hermes_home=str(fixture.configuration.path.parent))
        scope=MemoryPolicy(selected).resolve(context)
        self.assertEqual(scope.reason,'','Fresh dashboard owner activation has no usable approved local owner destination')
