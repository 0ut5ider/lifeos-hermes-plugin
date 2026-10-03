# ABOUTME: Characterizes lasting-memory ownership on the real Hermes agent constructor.
# ABOUTME: Preserves both built-in files while checking explicit store flags and skill tools.
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unittest

import test_memory_model_calls as model_fixture


class MemoryHostTests(unittest.TestCase):
    def setUp(self):
        self.fixture = model_fixture.MemoryModelCallTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.home = self.fixture.fixture.home
        shutil.copytree(Path(__file__).parents[1]/'lifeos_hook_bridge',self.home/'plugins/lifeos-hook-bridge',
                        ignore=shutil.ignore_patterns('__pycache__'))
        (self.home/'memories').mkdir()
        self.original = {'MEMORY.md':b'Synthetic Hermes lasting memory marker\n',
                         'USER.md':b'Synthetic Hermes user profile marker\n'}
        for name,data in self.original.items():
            (self.home/'memories'/name).write_bytes(data)

    def initialize(self, memory, *, expected_warning='', operation='', message='', author='100',
                   background_review=False, review_focus='Synthetic skill review',skill_approval=False,
                   review_explicit=False,followup_message=None):
        configuration = dict(self.fixture.host_config,memory=memory,plugins={'enabled':['lifeos-hook-bridge']})
        if background_review:
            configuration['skills'] = {'write_approval':skill_approval}
        if operation == 'conversation':
            configuration['model']=dict(configuration['model'],streaming=False,context_length=131072)
        (self.home/'config.yaml').write_text(json.dumps(configuration))
        environment = {key:os.environ[key] for key in ('PATH','LANG','TZ') if key in os.environ}
        environment.update(HOME=str(self.fixture.fixture.fixture.home),HERMES_HOME=str(self.home),
                           LIFEOS_HERMES_SOURCE=str(model_fixture.HOST),
                           LIFEOS_HOOK_SETTINGS=str(self.fixture.fixture.fixture.root/'settings.json'),
                           BUN_CONFIG_NO_AUTO_INSTALL='1')
        result = subprocess.run([sys.executable,str(Path(__file__).with_name('memory_host_calls.py'))],
                                input=json.dumps({'route':self.fixture.route,'operation':operation,'message':message,'author':author,
                                                  'background_review':background_review,'review_focus':review_focus,
                                                  'review_explicit':review_explicit,'followup_message':followup_message}),env=environment,
                                capture_output=True,text=True,timeout=45)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(result.stderr,'')
        self.last_process_output = result.stdout
        outcome = json.loads(result.stdout)
        self.last_outcome = outcome
        if expected_warning:
            self.assertIn(expected_warning,outcome['warnings'])
        else:
            self.assertEqual(outcome['warnings'],'')
        for name,data in self.original.items():
            self.assertEqual((self.home/'memories'/name).read_bytes(),data)
        probes = [request for request in self.fixture.received if request['path']=='/api/show']
        if operation != 'conversation':
            self.assertEqual(probes,self.fixture.received)
        probe_models = {'synthetic-model'}
        if background_review:
            probe_models.add(configuration.get('auxiliary',{}).get('background_review',{}).get('model','synthetic-model'))
        for request in probes:
            self.assertIn(request['body'],[{'name':model} for model in probe_models])
        return outcome

    def test_provider_selection_alone_keeps_builtin_memory_enabled(self):
        result = self.initialize({'provider':'lifeos-hook-bridge'})
        self.assertTrue(result['memory_enabled'])
        self.assertTrue(result['user_profile_enabled'])
        self.assertTrue(result['has_builtin_store'])
        for data in self.original.values():
            self.assertIn(data.decode().strip(),result['prompt'])
        self.assertIn('lifeos-hook-bridge',result['providers'])

    def test_explicit_ownership_flags_disable_both_builtin_stores_without_removing_files(self):
        result = self.initialize({'provider':'lifeos-hook-bridge','memory_enabled':False,'user_profile_enabled':False})
        self.assertFalse(result['memory_enabled'])
        self.assertFalse(result['user_profile_enabled'])
        self.assertFalse(result['has_builtin_store'])
        self.assertNotIn('memory',result['tools'])
        self.assertIn('lifeos_memory_remember',result['tools'])
        self.assertIn('lifeos_memory_forget',result['tools'])
        self.assertIn('skill_manage',result['tools'])
        self.assertEqual(len(result['disabled_writes']),4)
        self.assertTrue(all(outcome.get('success') is False for outcome in result['disabled_writes']),result['disabled_writes'])
        for data in self.original.values():
            self.assertNotIn(data.decode().strip(),result['prompt'])
        self.assertIn('lifeos-hook-bridge',result['providers'])

    def test_config_restoration_reuses_preserved_builtin_files_and_keeps_skills(self):
        before = self.initialize({'provider':None})
        disabled = self.initialize({'provider':'lifeos-hook-bridge','memory_enabled':False,'user_profile_enabled':False})
        restored = self.initialize({'provider':None})
        self.assertIn('lifeos-hook-bridge',disabled['providers'])
        self.assertEqual(before['providers'],[])
        self.assertEqual(restored['providers'],[])
        self.assertTrue(restored['memory_enabled'])
        self.assertTrue(restored['user_profile_enabled'])
        self.assertIn('memory',restored['tools'])
        self.assertIn('skill_manage',restored['tools'])
        for data in self.original.values():
            self.assertIn(data.decode().strip(),restored['prompt'])

    def test_unavailable_lifeos_provider_does_not_reenable_disabled_builtin_stores(self):
        from lifeos_hook_bridge.memory_service import MemoryConfiguration
        MemoryConfiguration(self.fixture.fixture.path).update(lambda configuration:configuration.update(ownership_enabled=False))
        result = self.initialize({'provider':'lifeos-hook-bridge','memory_enabled':False,'user_profile_enabled':False},
                                 expected_warning='LifeOS memory ownership cannot be activated in this release.')
        self.assertEqual(result['providers'],[])
        self.assertFalse(result['has_builtin_store'])
        self.assertNotIn('memory',result['tools'])
        self.assertNotIn('lifeos_memory_remember',result['tools'])
        self.assertIn('skill_manage',result['tools'])
        for data in self.original.values():
            self.assertNotIn(data.decode().strip(),result['prompt'])


if __name__ == '__main__':
    unittest.main()
