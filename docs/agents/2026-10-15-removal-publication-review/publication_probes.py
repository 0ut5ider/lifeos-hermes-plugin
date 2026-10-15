# ABOUTME: Probes complete native tool removal and protected ancestor admission in the joined publisher.
# ABOUTME: Uses private native source copies and actual serialized services without production records.
import hashlib
import json
from pathlib import Path
import shutil
import unittest

import test_removal_publication as fixture_module
from optional.lifeos_release_manager.release_programs import ProgramTransaction,publish

OUTPUT=Path(__file__).parent


class PublicationBoundaryReview(unittest.TestCase):
    def setUp(self):
        self.fixture=fixture_module.RemovalPublicationTests();self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root=Path(self.fixture.policy.configuration.load()['root'])

    def replace_programs(self,*,directories=None,additional=None):
        fixture=self.fixture
        (fixture.stage/'programs').rename(fixture.stage/'programs-fixture-original')
        transaction=ProgramTransaction(fixture.stage/'programs')
        transaction.prepare(directories=directories or {},files={fixture.program:None,
            fixture.policy.configuration.path:None,fixture.service.installed_pulse:None,**(additional or {})})
        fixture.programs=transaction
        fixture.policy.plan['program_entries_sha256']=transaction.entries_digest()
        data=json.dumps(fixture.policy.plan,sort_keys=True,separators=(',',':')).encode()
        fixture.signature=hashlib.sha256(data).hexdigest();publish(fixture.stage/'plan.json',data)
        publish(fixture.profile/'.lifeos-removal.json',json.dumps({'format':1,'workflow':fixture.policy.job.name,'signature':fixture.signature}).encode())
        publish(fixture.stage/'operation.json',json.dumps({'signature':fixture.signature,'state':'ready'}).encode())

    def include_actual_native_memory_tool(self):
        tools=self.root/'LIFEOS/TOOLS'
        self.assertTrue(tools.is_symlink())
        original=tools.resolve();tools.unlink()
        shutil.copytree(original,tools,symlinks=True,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        tool=tools/'MemorySystem.ts';self.assertTrue(tool.is_file());self.assertEqual(tool.resolve(),tool)
        self.replace_programs(additional={tool:None})
        return tool

    def test_actual_memory_tool_removal_can_roll_back(self):
        tool=self.include_actual_native_memory_tool()
        operation=self.fixture.operation()
        result=operation.apply(account='dashboard:owner')
        self.assertEqual(result['state'],'verification_required');self.assertFalse(tool.exists())
        observed={'apply_state':result['state'],'memory_tool_removed':not tool.exists()}
        try:observed['rollback']=self.fixture.operation().rollback(account='dashboard:owner')
        except RuntimeError as error:observed['rollback_error']=str(error)
        observed['service_pids']={role:self.fixture.service.fixture.properties(role)['MainPID'] for role in self.fixture.service.fixture.units}
        (OUTPUT/'memory-tool-rollback.json').write_text(json.dumps(observed,indent=2)+'\n')
        self.assertNotIn('rollback_error',observed)

    def test_interrupted_complete_native_removal_can_resume(self):
        tool=self.include_actual_native_memory_tool()
        def checkpoint(point):
            if point=='programs-published':raise InterruptedError('Synthetic exit after complete native tool removal')
        with self.assertRaises(InterruptedError):self.fixture.operation().apply(account='dashboard:owner',checkpoint=checkpoint)
        self.assertFalse(tool.exists())
        observed={'memory_tool_removed':not tool.exists()}
        try:observed['retry']=self.fixture.operation().apply(account='dashboard:owner')
        except RuntimeError as error:observed['retry_error']=str(error)
        (OUTPUT/'memory-tool-resume.json').write_text(json.dumps(observed,indent=2)+'\n')
        self.assertNotIn('retry_error',observed)

    def test_native_data_ancestor_is_never_a_removal_target(self):
        parent=self.root.parent/'.config/LIFEOS'
        self.assertTrue((parent/'USER').is_dir())
        self.replace_programs(directories={parent:None})
        observed={'target_contains_native_user':(parent/'USER').is_dir()}
        try:self.fixture.operation();observed['accepted']=True
        except ValueError as error:observed['refused']=str(error)
        (OUTPUT/'personal-data-ancestor.json').write_text(json.dumps(observed,indent=2)+'\n')
        self.assertIn('refused',observed)
