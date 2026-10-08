# ABOUTME: Runs the native Knowledge linter against synthetic registered notes and owner contexts.
# ABOUTME: Checks report fidelity, excluded sources, read grants, and authority after rendering.
from dataclasses import asdict
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

from lifeos_hook_bridge.memory_service import MemoryService
from test_memory_native import OWNER
import test_memory_knowledge_harvest as harvest_fixture


class MemoryKnowledgeLintTests(unittest.TestCase):
    def setUp(self):
        self.harvest=harvest_fixture.MemoryKnowledgeHarvestTests()
        self.harvest.setUp()
        self.addCleanup(self.harvest.doCleanups)
        self.fixture=self.harvest.fixture
        self.root=self.fixture.root
        self.first,self.reference=self.harvest.seed(slug='synthetic-private-lint',body='Synthetic lint fact',
            quality=5,created='2026-10-01',metadata='status: invented-state\n')
        self.harvest.seed(domain='Ideas',slug='synthetic-idea-lint',body='Synthetic second lint fact',
            quality=5,created='2026-10-01')
        self.control=Path(os.environ.get('LIFEOS_HARVEST_CONTROL_SOURCE',str(Path.home()/
            '.cache/lifeos-daily-text-20261007/background-control-source/LifeOS/install')))

    def call(self,*arguments,context=True,source=None):
        environment=dict(os.environ,HOME=str(self.fixture.fixture.home),BUN_CONFIG_NO_AUTO_INSTALL='1')
        environment.pop('LIFEOS_MEMORY_CONTEXT',None)
        environment.pop('LIFEOS_MEMORY_INTERNAL',None)
        if context:environment['LIFEOS_MEMORY_CONTEXT']=json.dumps(asdict(self.fixture.context))
        script=(source or self.root)/'LIFEOS/TOOLS/KnowledgeLint.ts'
        return subprocess.run(['bun','--no-install',str(script),*arguments],env=environment,
                              capture_output=True,text=True,timeout=40)

    def test_native_report_options_match_the_original_command(self):
        for arguments in [(),('--json',),('--list','1'),('--list','40'),('--dir','Research'),
                          ('--json','--dir','Ideas'),('--dir','Books')]:
            with self.subTest(arguments=arguments):
                actual=self.call(*arguments)
                control=self.call(*arguments,source=self.control)
                self.assertEqual(actual.returncode,0,actual.stderr)
                self.assertEqual(control.returncode,0,control.stderr)
                self.assertEqual(actual.stderr,'')
                self.assertEqual(control.stderr,'')
                self.assertEqual(actual.stdout,control.stdout)

    def test_unbound_lint_cannot_expose_private_filenames_or_counts(self):
        result=self.call('--list','20',context=False)
        self.assertNotEqual(result.returncode,0,result)
        self.assertNotIn('synthetic-private-lint',result.stdout+result.stderr)
        self.assertNotIn('Notes:',result.stdout)

    def test_read_only_owner_can_lint_without_changing_sources(self):
        before=self.first.read_bytes()
        self.fixture.configuration.update(lambda value:value['destinations']['chat-a:200'].update(write=[]))
        result=self.call('--json')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout)['total'],2)
        self.assertEqual(self.first.read_bytes(),before)

    def test_revoked_owner_cannot_receive_a_report(self):
        self.fixture.configuration.update(lambda value:value['accounts'].clear())
        result=self.call('--json')
        self.assertNotEqual(result.returncode,0,result)
        self.assertNotIn('per_dir',result.stdout)

    def test_unregistered_notes_do_not_change_counts_or_expose_labels(self):
        unknown=self.first.with_name('synthetic-unregistered-lint.md')
        unknown.write_text(self.first.read_text().replace('invented-state','SyntheticUnregisteredLintState'))
        result=self.call('--list','20')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('Notes:              2',result.stdout)
        self.assertNotIn('synthetic-unregistered-lint',result.stdout)
        self.assertNotIn('SyntheticUnregisteredLintState',result.stdout)
        self.assertTrue(unknown.exists())

    def test_forgotten_notes_do_not_change_counts_or_expose_labels(self):
        self.fixture.fixture.memory.forget(OWNER,self.reference,'synthetic-forget-lint')
        result=self.call('--list','20')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('Notes:              1',result.stdout)
        self.assertNotIn('synthetic-private-lint',result.stdout)

    def test_managed_options_cannot_select_another_directory_or_unbounded_list(self):
        service=MemoryService(self.fixture.configuration)
        for arguments in [dict(json=True,list=20,directory='../_harvest-queue'),
                          dict(json=True,list=10001,directory=None),
                          dict(json=True,list=True,directory=None)]:
            result=service.native(self.fixture.context,'knowledge_lint',arguments)
            self.assertFalse(result['ok'],result)
            self.assertNotIn('stdout',result)

    def test_standalone_without_connector_keeps_the_original_report(self):
        (self.root/'LIFEOS/USER/CONFIG/memory-access.json').unlink()
        actual=self.call('--list','20',context=False)
        control=self.call('--list','20',source=self.control,context=False)
        self.assertEqual(actual.returncode,0,actual.stderr)
        self.assertEqual(actual.stdout,control.stdout)

    def test_authority_and_source_changes_after_real_render_withhold_the_report(self):
        before=self.first.read_bytes()
        for mode in ('authority','source'):
            result=subprocess.run([sys.executable,str(Path(__file__).with_name('memory_knowledge_lint_process.py')),
                str(self.fixture.configuration.path),mode],capture_output=True,text=True,timeout=40,
                env=dict(os.environ,PYTHONPATH=str(Path(__file__).resolve().parents[1])))
            self.assertEqual(result.returncode,0,result.stderr)
            response=json.loads(result.stdout)
            self.assertTrue(response['rendered'])
            self.assertFalse(response['result']['ok'],response)
            self.assertNotIn('stdout',response['result'])
            self.fixture.configuration.update(lambda value:value['accounts'].update({'chat-a:100':'owner'}))
            self.first.write_bytes(before)


if __name__=='__main__':unittest.main()
