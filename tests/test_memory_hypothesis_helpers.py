# ABOUTME: Exercises exported hypothesis helpers with actual native and governed owner callers.
# ABOUTME: Compares original effects and refuses unbound, revoked, restricted, or retired sources.
from dataclasses import asdict
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import unittest

import test_memory_delegation as native_fixture
import test_memory_hypothesis_relay as queue_fixture
from test_memory_native import OWNER,SOURCE


class MemoryHypothesisHelpersTests(unittest.TestCase):
    seed=queue_fixture.MemoryHypothesisRelayTests.seed

    def setUp(self):
        self.fixture=native_fixture.MemoryDelegationTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root=self.fixture.root
        (self.root/'LIFEOS/PULSE').symlink_to(SOURCE/'LIFEOS/PULSE')
        self.fixture.configuration.update(lambda value:value['destinations']['chat-a:200'].update(proposals=['approve']))

    @property
    def frames(self):return self.root/'LIFEOS/MEMORY/WISDOM/FRAMES'

    def snapshot(self):
        return {path.relative_to(self.frames).as_posix():path.read_text() for path in self.frames.rglob('*') if path.is_file()}

    def reset(self,contents):
        for path in self.frames.iterdir():
            if path.is_dir():shutil.rmtree(path)
            else:path.unlink()
        for relative,content in contents.items():
            path=self.frames/relative
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(content)

    def call(self,operation,*,context=True,original=False):
        source=Path(os.environ['LIFEOS_HARVEST_CONTROL_SOURCE']) if original else self.root
        script='import {listPending,graduateHypothesis,rejectHypothesis} from '+json.dumps(str(source/'LIFEOS/PULSE/modules/hypotheses.ts'))+';'
        expression={'list':'listPending()','graduate':'await graduateHypothesis("synthetic-hypothesis","Synthetic direct review")',
            'reject':'rejectHypothesis("synthetic-hypothesis","Synthetic direct rejection")'}[operation]
        environment=dict(os.environ,HOME=str(self.fixture.fixture.home),LIFEOS_DIR=str(self.root/'LIFEOS'),
            BUN_CONFIG_NO_AUTO_INSTALL='1')
        environment.pop('LIFEOS_MEMORY_INTERNAL',None)
        environment.pop('LIFEOS_MEMORY_CONTEXT',None)
        if context:environment['LIFEOS_MEMORY_CONTEXT']=json.dumps(asdict(self.fixture.context))
        return subprocess.run(['bun','--no-install','-e',script+'console.log(JSON.stringify('+expression+'));'],
            capture_output=True,text=True,env=environment,timeout=40)

    def test_native_list_matches_all_original_pending_fields(self):
        self.seed()
        original=self.call('list',original=True)
        actual=self.call('list')
        self.assertEqual(original.returncode,0,original.stderr)
        self.assertEqual(actual.returncode,0,actual.stderr)
        self.assertEqual(json.loads(actual.stdout),json.loads(original.stdout))
        self.assertEqual(actual.stderr,'')

    def test_unbound_direct_helpers_refuse_without_reading_or_publishing(self):
        self.seed()
        before=self.snapshot()
        for operation in ('list','graduate','reject'):
            with self.subTest(operation=operation):
                self.reset(before)
                result=self.call(operation,context=False)
                self.assertNotEqual(result.returncode,0,result.stdout)
                self.assertNotIn('SyntheticHypothesisCurrentMarker',result.stdout)
                self.assertEqual(self.snapshot(),before)

    def test_owner_direct_mutations_match_original_file_effects(self):
        self.seed()
        before=self.snapshot()
        for operation in ('graduate','reject'):
            with self.subTest(operation=operation):
                self.reset(before)
                expected=self.call(operation,original=True)
                self.assertEqual(expected.returncode,0,expected.stderr)
                effects=self.snapshot()
                self.reset(before)
                actual=self.call(operation)
                self.assertEqual(actual.returncode,0,actual.stderr)
                self.assertEqual(actual.stderr,'')
                self.assertEqual(json.loads(actual.stdout),json.loads(expected.stdout))
                normalized=lambda values:{key:re.sub(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z','SyntheticInstant',value)
                    for key,value in values.items()}
                self.assertEqual(normalized(self.snapshot()),normalized(effects))

    def test_revoked_direct_helpers_cannot_read_or_publish(self):
        self.seed()
        before=self.snapshot()
        self.fixture.configuration.update(lambda value:value['accounts'].clear())
        for operation in ('list','graduate','reject'):
            with self.subTest(operation=operation):
                self.reset(before)
                result=self.call(operation)
                self.assertNotEqual(result.returncode,0,result.stdout)
                self.assertEqual(self.snapshot(),before)

    def test_read_only_owner_can_list_and_cannot_mutate(self):
        self.seed()
        before=self.snapshot()
        self.fixture.configuration.update(lambda value:value['destinations']['chat-a:200'].update(write=[]))
        result=self.call('list')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(len(json.loads(result.stdout)),1)
        for operation in ('graduate','reject'):
            with self.subTest(operation=operation):
                self.reset(before)
                result=self.call(operation)
                self.assertNotEqual(result.returncode,0,result.stdout)
                self.assertEqual(self.snapshot(),before)

    def test_forgotten_text_leaves_retained_note_and_exits_direct_queue(self):
        saved=self.fixture.fixture.memory.remember(OWNER,category='principal',content='RULE: Synthetic direct forgotten marker',
            title='',project='',request_id='synthetic-direct-forget')
        self.assertEqual(saved['status'],'committed',saved)
        path=self.seed('Synthetic direct forgotten marker')
        self.assertEqual(len(json.loads(self.call('list').stdout)),1)
        self.fixture.fixture.memory.forget(OWNER,saved['reference'],'synthetic-direct-retire')
        result=self.call('list')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout),[])
        self.assertTrue(path.exists())

    def test_standalone_helpers_preserve_original_unbound_behavior(self):
        self.seed()
        (self.root/'LIFEOS/USER/CONFIG/memory-access.json').unlink()
        result=self.call('list',context=False)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(len(json.loads(result.stdout)),1)

    def test_private_note_is_retained_and_excluded_from_direct_list(self):
        path=self.seed('<private>Synthetic direct private marker</private>')
        result=self.call('list')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout),[])
        self.assertTrue(path.exists())

    def test_redirected_source_cannot_enter_direct_list(self):
        path=self.seed()
        external=self.root.parent/'synthetic-other-hypothesis.md'
        external.write_text(path.read_text())
        path.unlink()
        path.symlink_to(external)
        before=external.read_bytes()
        result=self.call('list')
        self.assertNotEqual(result.returncode,0,result.stdout)
        self.assertNotIn('SyntheticHypothesisCurrentMarker',result.stdout)
        self.assertEqual(external.read_bytes(),before)

    def test_actual_list_render_rechecks_source_and_authority(self):
        for mode in ('source','authority'):
            with self.subTest(mode=mode):
                self.seed()
                result=subprocess.run([sys.executable,str(Path(__file__).with_name('memory_hypothesis_helpers_process.py')),
                    str(self.fixture.configuration.path),json.dumps(asdict(self.fixture.context)),mode],
                    capture_output=True,text=True,timeout=40,
                    env=dict(os.environ,PYTHONPATH=str(Path(__file__).resolve().parents[1])))
                self.assertEqual(result.returncode,0,result.stderr)
                self.assertEqual(json.loads(result.stdout),{'rendered':True,'withheld':True})
