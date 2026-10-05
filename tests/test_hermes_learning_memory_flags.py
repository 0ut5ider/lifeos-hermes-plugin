# ABOUTME: Checks learning-graph surfaces against the selected Hermes built-in memory flags.
# ABOUTME: Uses isolated real Hermes processes to preserve disabled stores and retain enabled behavior.
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class HermesLearningMemoryFlagsTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory(prefix='hermes-learning-flags-')
        self.addCleanup(self.directory.cleanup)
        self.home=Path(self.directory.name)
        (self.home/'memories').mkdir()
        (self.home/'memories/MEMORY.md').write_text('Synthetic preserved journey memory.\n')
        (self.home/'memories/USER.md').write_text('Synthetic preserved journey preference.\n')
        self.events=[]

    def call(self,operation,source='memory',*,flags=(False,False),queued=False):
        (self.home/'config.yaml').write_text('memory:\n  memory_enabled: '+str(flags[0]).lower()+
            '\n  user_profile_enabled: '+str(flags[1]).lower()+'\n')
        host=Path(os.environ['LIFEOS_HERMES_SOURCE'])
        environment={**os.environ,'HERMES_HOME':str(self.home),'HOME':str(self.home),
            'PYTHONPATH':str(host)+os.pathsep+str(Path(__file__).resolve().parents[1]),
            'PYTHONDONTWRITEBYTECODE':'1'}
        result=subprocess.run([sys.executable,str(Path(__file__).with_name('hermes_learning_memory_queued_process.py' if queued else 'hermes_learning_memory_process.py'))],
            input=json.dumps({'operation':operation,'source':source}),env=environment,capture_output=True,text=True,timeout=30)
        self.events.append({'operation':operation,'source':source,'flags':flags,'status':result.returncode,
                            'stdout':result.stdout,'stderr':result.stderr})
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(result.stderr,'')
        return json.loads(result.stdout)

    def test_disabled_stores_do_not_supply_graph_cards(self):
        result=self.call('cards')
        self.assertEqual(result['result'],[])
        self.assertTrue(result['unchanged'])

    def test_disabled_stores_refuse_detail_prefill_without_exposing_content(self):
        for source in ('memory','profile'):
            with self.subTest(source=source):
                result=self.call('detail',source)
                self.assertFalse(result['result']['ok'],result)
                self.assertNotIn('Synthetic preserved journey',json.dumps(result['result']))
                self.assertTrue(result['unchanged'])

    def test_disabled_stores_refuse_edits_without_changing_files(self):
        for source in ('memory','profile'):
            with self.subTest(source=source):
                result=self.call('edit',source)
                self.assertFalse(result['result']['ok'],result)
                self.assertTrue(result['unchanged'])

    def test_disabled_stores_refuse_deletion_without_changing_files(self):
        for source in ('memory','profile'):
            with self.subTest(source=source):
                result=self.call('delete',source)
                self.assertFalse(result['result']['ok'],result)
                self.assertTrue(result['unchanged'])

    def test_each_enabled_store_retains_its_own_graph_cards(self):
        for flags,source in (((True,False),'memory'),((False,True),'profile')):
            with self.subTest(flags=flags):
                result=self.call('cards',flags=flags)
                self.assertEqual([entry['source'] for entry in result['result']],[source])
                self.assertTrue(result['unchanged'])

    def test_enabled_stores_retain_native_edit_and_detail_behavior(self):
        for source in ('memory','profile'):
            with self.subTest(source=source):
                detail=self.call('detail',source,flags=(True,True))
                self.assertTrue(detail['result']['ok'],detail)
                result=self.call('edit',source,flags=(True,True))
                self.assertTrue(result['result']['ok'],result)
                self.assertFalse(result['unchanged'])
                self.assertIn('Synthetic replacement journey fact.',result['bytes'])

    def test_queued_enabled_store_refuses_edit_after_current_flags_change(self):
        for source in ('memory','profile'):
            with self.subTest(source=source):
                result=self.call('edit',source,flags=(True,True),queued=True)
                self.assertEqual(result['loaded_enabled'],[True])
                self.assertFalse(result['result']['ok'],result)
                self.assertTrue(result['unchanged'])

    def test_queued_enabled_store_refuses_delete_after_current_flags_change(self):
        for source in ('memory','profile'):
            with self.subTest(source=source):
                result=self.call('delete',source,flags=(True,True),queued=True)
                self.assertEqual(result['loaded_enabled'],[True])
                self.assertFalse(result['result']['ok'],result)
                self.assertTrue(result['unchanged'])
