# ABOUTME: Executes the native morning brief with synthetic TELOS sources and current owner contexts.
# ABOUTME: Compares native output and checks private sources, retired goals, revocation, and local jobs.
from dataclasses import asdict
import json
import os
from pathlib import Path
import subprocess
import unittest

from test_memory_native import OWNER,SOURCE
import test_memory_delegation as delegation
import test_memory_owner_jobs as jobs_fixture


class MemoryMorningBriefTests(unittest.TestCase):
    def setUp(self):
        self.fixture=delegation.MemoryDelegationTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root=self.fixture.root
        pulse=self.root/'LIFEOS/PULSE'
        if not pulse.exists():pulse.symlink_to(SOURCE/'LIFEOS/PULSE',target_is_directory=True)
        self.telos=self.root/'LIFEOS/USER/TELOS'
        self.telos.mkdir(parents=True,exist_ok=True)

    def seed(self):
        (self.telos/'GOALS.md').write_text('# Synthetic goals\n- **G1**: Synthetic first goal\n- G2: Synthetic second goal\n- G3: Synthetic third goal...\n- G4: Synthetic omitted goal\n')
        (self.telos/'SPARKS.md').write_text('# Synthetic sparks\n### Synthetic only spark\n')
        (self.telos/'CURRENT.md').write_text('# Synthetic current\n## Next likely actions\n1. Synthetic next action\n')

    def call(self,*,context=True,original=False,standalone=False):
        source=Path(os.environ['LIFEOS_HARVEST_CONTROL_SOURCE']) if original else self.root
        environment=dict(os.environ,HOME=str(self.fixture.fixture.home),LIFEOS_DIR=str(self.root/'LIFEOS'),
            BUN_CONFIG_NO_AUTO_INSTALL='1')
        environment.pop('LIFEOS_MEMORY_INTERNAL',None)
        environment.pop('LIFEOS_MEMORY_CONTEXT',None)
        if standalone:environment['LIFEOS_MEMORY_INTERNAL']='1'
        if context:environment['LIFEOS_MEMORY_CONTEXT']=json.dumps(asdict(self.fixture.context))
        return subprocess.run(['bun','--no-install',str(source/'LIFEOS/PULSE/checks/life-morning-brief.ts')],
            capture_output=True,text=True,timeout=40,env=environment)

    def test_owner_brief_preserves_native_goal_spark_and_action_output(self):
        self.seed()
        expected=self.call(original=True)
        result=self.call()
        self.assertEqual(expected.returncode,0,expected.stderr)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(result.stderr,'')
        self.assertEqual(result.stdout,expected.stdout)

    def test_missing_sources_preserve_native_no_action(self):
        result=self.call()
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(result.stderr,'')
        self.assertEqual(result.stdout,'NO_ACTION\n')
        self.assertEqual(result.stdout,self.call(original=True).stdout)

    def test_unbound_brief_cannot_read_personal_sources(self):
        self.seed()
        result=self.call(context=False)
        self.assertNotEqual(result.returncode,0,result.stdout)
        self.assertNotIn('Synthetic first goal',result.stdout)

    def test_revoked_brief_cannot_read_personal_sources(self):
        self.seed()
        self.fixture.configuration.update(lambda value:value['accounts'].clear())
        result=self.call()
        self.assertNotEqual(result.returncode,0,result.stdout)
        self.assertNotIn('Synthetic first goal',result.stdout)

    def test_private_sources_do_not_enter_brief(self):
        self.seed()
        (self.telos/'GOALS.md').write_text('- G1: <private>Synthetic hidden goal</private>\n')
        result=self.call()
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertNotIn('Synthetic hidden goal',result.stdout)
        self.assertIn('Synthetic only spark',result.stdout)

    def test_retired_source_does_not_enter_brief(self):
        memory=self.fixture.fixture.memory
        saved=memory.remember(OWNER,category='principal',content='RULE: Synthetic retired morning goal',
            title='',project='',request_id='synthetic-morning-retained')
        (self.telos/'GOALS.md').write_text('- G1: Synthetic retired morning goal\n')
        memory.forget(OWNER,saved['reference'],'synthetic-morning-forget')
        result=self.call()
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(result.stdout,'NO_ACTION\n')

    def test_legacy_goals_and_unified_telos_fallback_match_native(self):
        path=self.telos/'TELOS.md'
        path.write_text('# Synthetic unified TELOS\n## Goals\n- G1: Synthetic unified goal\n## Other\nSynthetic other section\n')
        for legacy in (False,True):
            with self.subTest(legacy=legacy):
                if legacy:(self.telos/'GOALS.md').write_text('- G1: Synthetic legacy goal\n')
                result=self.call();expected=self.call(original=True)
                self.assertEqual(result.returncode,0,result.stderr)
                self.assertEqual(result.stdout,expected.stdout)

    def test_enabled_owner_job_executes_the_actual_brief(self):
        fixture=jobs_fixture.MemoryOwnerJobsTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        root=fixture.fixture.root
        pulse=root/'LIFEOS/PULSE'
        if not pulse.exists():pulse.symlink_to(SOURCE/'LIFEOS/PULSE',target_is_directory=True)
        path=root/'LIFEOS/USER/TELOS/GOALS.md'
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text('- G1: Synthetic scheduled morning goal\n')
        result=fixture.run_job('life-morning-brief')
        self.assertEqual(result['status'],'completed',result)
        self.assertIn('Synthetic scheduled morning goal',result['output'])

    def test_standalone_legacy_goals_do_not_open_unused_unified_source(self):
        (self.telos/'GOALS.md').write_text('- G1: Synthetic legacy source\n')
        unused=self.fixture.fixture.home/'unused-unified-directory'
        unused.mkdir()
        (self.telos/'TELOS.md').symlink_to(unused)
        expected=self.call(original=True)
        self.assertEqual(expected.returncode,0,expected.stderr)
        result=self.call(standalone=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(result.stdout,expected.stdout)

    def test_source_and_authority_changes_after_actual_render_withhold_narration(self):
        import sys
        for mode in ('source','authority'):
            with self.subTest(mode=mode):
                self.seed()
                result=subprocess.run([sys.executable,str(Path(__file__).with_name('memory_morning_brief_process.py')),
                    str(self.fixture.configuration.path),mode,json.dumps(asdict(self.fixture.context))],
                    capture_output=True,text=True,timeout=40,
                    env=dict(os.environ,PYTHONPATH=str(Path(__file__).resolve().parents[1])))
                self.assertEqual(result.returncode,0,result.stderr)
                self.assertEqual(json.loads(result.stdout),{'rendered':True,'withheld':True})

    def test_redirected_source_cannot_supply_narration(self):
        path=self.telos/'GOALS.md'
        outside=self.fixture.fixture.home/'outside-goals.md'
        outside.write_text('- G1: Synthetic outside goal\n')
        path.symlink_to(outside)
        result=self.call()
        self.assertNotEqual(result.returncode,0,result.stdout)
        self.assertNotIn('Synthetic outside goal',result.stdout)
        self.assertTrue(outside.exists())

    def test_read_only_owner_can_read_brief_without_publishing_files(self):
        self.seed()
        self.fixture.configuration.update(lambda value:value['destinations']['chat-a:200'].update(write=[]))
        before={path.name:path.read_bytes() for path in self.telos.iterdir()}
        result=self.call()
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('Synthetic first goal',result.stdout)
        self.assertEqual({path.name:path.read_bytes() for path in self.telos.iterdir()},before)

    def test_connector_loss_cannot_use_unmanaged_personal_sources(self):
        self.seed()
        connector=self.root/'LIFEOS/USER/CONFIG/memory-access.json'
        marker=self.root/'LIFEOS/USER/CONFIG/memory-http.json'
        marker.write_text('{"version":1,"managed":true}')
        marker.chmod(0o600)
        connector.unlink()
        result=self.call()
        self.assertNotEqual(result.returncode,0,result.stdout)
        self.assertNotIn('Synthetic first goal',result.stdout)

    def test_oversized_source_and_control_text_never_enter_brief(self):
        path=self.telos/'GOALS.md'
        for content in ('- G1: Synthetic\x00bad goal\n','- G1: '+'x'*(256*1024)):
            with self.subTest(length=len(content)):
                path.write_text(content)
                result=self.call()
                self.assertNotIn('bad goal',result.stdout)
                self.assertNotIn('x'*100,result.stdout)
                if len(content)>256*1024:self.assertNotEqual(result.returncode,0,result.stdout)
                else:self.assertEqual(result.stdout,'NO_ACTION\n')
