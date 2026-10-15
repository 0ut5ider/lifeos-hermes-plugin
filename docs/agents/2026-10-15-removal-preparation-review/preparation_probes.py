# ABOUTME: Tests lost-update and shared-consumer boundaries in removal preparation.
# ABOUTME: Uses actual generated files, program transactions, and a private Bun process.
import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest

import test_removal_preparation as preparation_fixture
import test_removal_consumers as consumer_fixture
from optional.lifeos_release_manager.release_programs import ProgramTransaction

OUTPUT=Path(__file__).parent


class CurrentStateReview(unittest.TestCase):
    def test_later_configuration_and_environment_edits_survive_preparation(self):
        fixture=preparation_fixture.RemovalSoftwarePlanTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
        (fixture.home/'.local/bin').mkdir(parents=True,mode=0o700)
        directories,files,dependencies=fixture.plan()
        config=fixture.profile/'config.yaml';env=fixture.profile/'.env'
        config.write_bytes(config.read_bytes()+b'owner_later_setting: keep-new-value\n')
        env.write_bytes(env.read_bytes()+b'OWNER_LATER_SETTING=keep-new-value\n')
        observed={}
        try:
            tx=ProgramTransaction(fixture.home/'publication')
            tx.prepare(directories=directories,files=files,dependencies=dependencies)
            tx.apply();observed['applied']=True
        except ValueError as error:observed['refused']=str(error)
        observed['config_edit_retained']=b'owner_later_setting: keep-new-value' in config.read_bytes()
        observed['environment_edit_retained']=b'OWNER_LATER_SETTING=keep-new-value' in env.read_bytes()
        (OUTPUT/'current-input-edits.json').write_text(json.dumps(observed,indent=2)+'\n')
        self.assertTrue(observed['config_edit_retained']);self.assertTrue(observed['environment_edit_retained'])


class ConsumerReview(unittest.TestCase):
    def setUp(self):
        self.fixture=consumer_fixture.RemovalConsumersTests();self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def test_home_expansion_in_foreign_units_refuses(self):
        path=self.fixture.directory/'foreign-owner.service'
        path.write_text('[Service]\nExecStart=%h/.local/bin/bun %h/.claude/LIFEOS/TOOLS/Owner.ts\n')
        observed={}
        try:self.fixture.operation().unit_files(self.fixture.profile,self.fixture.installed,known={self.fixture.owned});observed['admitted']=True
        except ValueError as error:observed['refused']=str(error)
        (OUTPUT/'home-expanded-service.json').write_text(json.dumps(observed,indent=2)+'\n')
        self.assertIn('refused',observed)

    @unittest.skipUnless(shutil.which('bun'),'Actual Bun is required')
    def test_basename_argv_does_not_hide_an_owned_bun_process(self):
        command=self.fixture.home/'.local/bin/bun';command.parent.mkdir(parents=True)
        shutil.copy2(shutil.which('bun'),command)
        with subprocess.Popen(['bun','-e','setInterval(()=>{},1000)'],executable=str(command),
                stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE) as child:
            try:
                observed={'owned_executable_verified':(Path('/proc')/str(child.pid)/'exe').resolve()==command}
                self.assertTrue(observed['owned_executable_verified']);self.assertIsNone(child.poll())
                try:self.fixture.operation().processes(self.fixture.profile,self.fixture.installed,groups=set());observed['admitted']=True
                except ValueError as error:observed['refused']=str(error)
                (OUTPUT/'basename-bun-process.json').write_text(json.dumps(observed,indent=2)+'\n')
                self.assertIn('refused',observed)
            finally:
                child.terminate();stdout,stderr=child.communicate(timeout=10);self.assertEqual(stdout+stderr,b'')

    def test_braced_home_in_foreign_hooks_refuses(self):
        settings={'hooks':{'SessionEnd':[{'hooks':[{'type':'command',
            'command':'node ${HOME}/.claude/LIFEOS/TOOLS/Owner.js'}]}]}}
        observed={}
        try:self.fixture.operation().hooks(settings,self.fixture.profile,self.fixture.installed);observed['admitted']=True
        except ValueError as error:observed['refused']=str(error)
        (OUTPUT/'braced-home-hook.json').write_text(json.dumps(observed,indent=2)+'\n')
        self.assertIn('refused',observed)
