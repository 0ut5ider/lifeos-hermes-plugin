# ABOUTME: Verifies built-in memory return through the real Hermes constructor and prompt builder.
# ABOUTME: Uses a local protocol fixture and exports hashes and counts without memory content.
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

import test_memory_model_calls as fixture


class MemoryTransitionProbeTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixture.MemoryModelCallTests();self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.profile=self.fixture.fixture.home
        self.home=self.fixture.fixture.fixture.home
        self.config={**self.fixture.host_config,'memory':{'provider':'builtin','memory_enabled':True,'user_profile_enabled':True}}
        (self.profile/'config.yaml').write_text(json.dumps(self.config))
        (self.profile/'memories').mkdir(mode=0o700)
        self.files={'MEMORY.md':'Synthetic reviewed exported project.','USER.md':'Synthetic reviewed exported preference.'}
        for name,data in self.files.items():(self.profile/'memories'/name).write_text(data)
        (self.profile/'SOUL.md').write_text('You are the synthetic Hermes acceptance agent.')

    def probe(self):
        environment={key:os.environ[key] for key in ('PATH','LANG','TZ') if key in os.environ}
        environment.update(HOME=str(self.home),HERMES_HOME=str(self.profile),
            PYTHONPATH=os.pathsep.join((str(fixture.HOST),str(Path(__file__).parents[1]))))
        code='import json,sys\nfrom lifeos_hook_bridge.memory_transition_probe import verify_builtin\nprint(json.dumps(verify_builtin(json.load(sys.stdin))))\n'
        return subprocess.run([sys.executable,'-B','-c',code],input=json.dumps(self.files),
            text=True,capture_output=True,env=environment,timeout=45)

    def test_actual_fresh_constructor_loads_exact_entries_and_emits_only_safe_proof(self):
        result=self.probe();self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(result.stderr,'')
        proof=json.loads(result.stdout)
        self.assertEqual(proof['provider'],'builtin')
        self.assertEqual(proof['entry_counts'],{'MEMORY.md':1,'USER.md':1})
        self.assertTrue(proof['fresh_agent_verified'])
        self.assertEqual(proof['native_providers'],[])
        for text in self.files.values():self.assertNotIn(text,result.stdout)
        self.assertFalse(any(request['path'].endswith('/chat/completions') for request in self.fixture.received))

    def test_current_file_change_refuses_the_reviewed_proof(self):
        (self.profile/'memories/MEMORY.md').write_text('Synthetic later built-in fact.')
        result=self.probe()
        self.assertNotEqual(result.returncode,0)
        self.assertEqual(result.stdout,'')
        self.assertIn('does not match the reviewed export',result.stderr)
