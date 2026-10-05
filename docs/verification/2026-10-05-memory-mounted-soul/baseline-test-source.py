# ABOUTME: Verifies managed soul regeneration retains the primary mounted LifeOS policy.
# ABOUTME: Uses actual native renderers and Hermes loading with synthetic identity and the public constitution.
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

from lifeos_hook_bridge.memory_prompt import bundle
import test_memory_hermes_soul_writer as soul_fixture
from test_memory_native import OWNER, SOURCE


class MemoryMountedSoulTests(unittest.TestCase):
    def setUp(self):
        self.fixture=soul_fixture.MemoryHermesSoulWriterTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.memory=self.fixture.fixture.fixture.fixture.fixture.memory
        self.constitution=self.fixture.root/'LIFEOS/LIFEOS_SYSTEM_PROMPT.md'

    def test_managed_regeneration_retains_the_primary_constitution_and_identity(self):
        canonical=bundle(self.memory,OWNER)['soul']
        printed=self.fixture.successful('--stdout')
        self.assertIn(canonical.strip(),printed.stdout)
        self.assertIn('Synthetic mounted LifeOS doctrine.',printed.stdout)
        self.assertNotIn('The real work lives in the terminal.',printed.stdout)
        self.fixture.successful()
        self.assertIn('LifeOS is mounted in Hermes.',self.fixture.context.read_text())
        self.assertNotIn('I do not have it mounted',self.fixture.context.read_text())
        self.assertNotIn('I say it belongs in the terminal',self.fixture.context.read_text())

    def test_missing_constitution_refuses_and_preserves_both_previous_artifacts(self):
        before=self.fixture.previous()
        self.constitution.unlink()
        result=self.fixture.call()
        self.assertNotEqual(result.returncode,0)
        self.assertEqual((self.fixture.soul.read_bytes(),self.fixture.context.read_bytes()),before)

    def test_excluded_constitution_refuses_and_preserves_both_previous_artifacts(self):
        before=self.fixture.previous()
        self.constitution.write_text('<private>Synthetic excluded constitution.</private>\n')
        result=self.fixture.call()
        self.assertNotEqual(result.returncode,0)
        self.assertEqual((self.fixture.soul.read_bytes(),self.fixture.context.read_bytes()),before)
        self.assertNotIn('Synthetic excluded constitution',result.stdout)

    def test_public_constitution_survives_managed_regeneration_and_actual_hermes_loading(self):
        self.constitution.write_text((SOURCE/'LIFEOS/LIFEOS_SYSTEM_PROMPT.md').read_text())
        canonical=bundle(self.memory,OWNER)['soul']
        self.fixture.successful()
        self.assertIn(canonical.strip(),self.fixture.soul.read_text())
        program='from agent.prompt_builder import load_soul_md;from pathlib import Path;import json;'
        program+='p=Path('+repr(str(self.fixture.profile))+');s=p.joinpath("SOUL.md").read_text().strip();'
        program+='v=load_soul_md(context_length=131072,home_override=p);print(json.dumps({"complete":v==s,"source_chars":len(s),"loaded_chars":len(v or "")}))'
        result=subprocess.run([sys.executable,'-c',program],capture_output=True,text=True,
            env={**os.environ,'HERMES_HOME':str(self.fixture.profile)},timeout=30)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertTrue(json.loads(result.stdout)['complete'],result.stdout)
        self.assertNotIn('TRUNCATED',result.stderr)
        self.assertIn('matched injection pattern(s)',result.stderr)

    def test_unmanaged_standalone_role_keeps_original_terminal_contract(self):
        (self.fixture.root/'LIFEOS/USER/CONFIG/memory-access.json').unlink()
        result=self.fixture.call('--stdout',context=False)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(result.stderr,'')
        self.assertIn('The real work lives in the terminal.',result.stdout)
        self.assertNotIn('Synthetic mounted LifeOS doctrine.',result.stdout)
