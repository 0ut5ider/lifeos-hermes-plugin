# ABOUTME: Exercises repeated ownership activation and current-state return with actual native data and services.
# ABOUTME: Uses a fresh real Hermes constructor for return proof without executing a model turn.
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

import test_memory_activation as activation_fixture
from lifeos_hook_bridge.memory_export import MemoryExport
from lifeos_hook_bridge.memory_import import MemoryImport
from lifeos_hook_bridge.memory_return import MemoryReturn
from lifeos_hook_bridge.memory_transition import MemoryTransition
from lifeos_hook_bridge.memory_access import MemoryUnavailable


class PortabilityLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.fixture=activation_fixture.MemoryActivationTests();self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        self.configuration=self.fixture.configuration;self.profile=self.configuration.path.parent
        self.home=self.fixture.setup.backup.fixture.fixture.home
        path=self.profile/'config.yaml'
        path.write_text(path.read_text()+'model: {default: synthetic-model, provider: custom, base_url: "http://127.0.0.1:9/v1", api_key: synthetic-key}\n'
            'plugins: {enabled: [lifeos, lifeos-hook-bridge, lifeos-release-manager]}\n')
        current=self.fixture.importer.preview(account='dashboard:owner')
        self.fixture.snapshot=self.home/'lifecycle-initial-import'
        self.fixture.captured=self.fixture.importer.prepare(self.fixture.snapshot,current['signature'],account='dashboard:owner')
        decisions=[{'id':item['id'],'action':'import','required':True,
            'category':'principal' if source['path'].endswith('USER.md') else 'project',
            'project':'lab','title':'Synthetic activation review','content':item['content']}
            for source in current['sources'] for item in source['chunks'] if item['content']]
        self.fixture.plan=self.fixture.importer.plan(self.fixture.snapshot,self.fixture.captured['snapshot_signature'],
            decisions,account='dashboard:owner')

    def constructor(self,expected):
        environment={key:os.environ[key] for key in ('PATH','LANG','TZ') if key in os.environ}
        environment.update(HOME=str(self.home),HERMES_HOME=str(self.profile),
            PYTHONPATH=os.pathsep.join((os.environ['LIFEOS_HERMES_SOURCE'],str(Path(__file__).parents[1]))))
        code='import json,sys\nfrom lifeos_hook_bridge.memory_transition_probe import verify_builtin\nprint(json.dumps(verify_builtin(json.load(sys.stdin))))\n'
        result=subprocess.run([sys.executable,'-B','-c',code],input=json.dumps(expected),text=True,
            capture_output=True,env=environment,timeout=45)
        self.assertEqual(result.returncode,0,result.stderr);self.assertEqual(result.stderr,'')
        return json.loads(result.stdout)

    def return_to_builtin(self):
        self.fixture.publish();review=self.fixture.prepare()
        self.fixture.operation().apply(review['signature'],account='dashboard:owner')
        self.assertTrue(self.configuration.load()['ownership_enabled'])
        exported=MemoryExport(self.configuration);current=exported.preview(account='dashboard:owner')
        snapshot=self.home/'lifecycle-export'
        saved=exported.prepare(snapshot,current['signature'],account='dashboard:owner')
        decisions=[{'id':item['id'],'action':'export','required':True,
            'file':'USER.md' if item['category']=='principal' else 'MEMORY.md','content':item['content']} for item in current['items']]
        plan=exported.plan(snapshot,saved['signature'],decisions,account='dashboard:owner')
        exported.apply(snapshot,saved['signature'],plan['signature'],account='dashboard:owner')
        returned=MemoryReturn(self.configuration).prepare(snapshot,saved['signature'],plan['signature'],
            prompt='Synthetic current returned prompt.',account='dashboard:owner')
        transition=MemoryTransition(self.configuration,units=self.fixture.setup.services.units)
        selected=transition.prepare_return(snapshot,returned['signature'],account='dashboard:owner')
        transition.apply(selected['signature'],account='dashboard:owner')
        result=transition.verify(selected['signature'],self.constructor,account='dashboard:owner')
        self.assertTrue(result['application_verified'])

    def import_current(self):
        importer=MemoryImport(self.configuration);current=importer.preview(account='dashboard:owner')
        second=self.home/'lifecycle-import';captured=importer.prepare(second,current['signature'],account='dashboard:owner')
        decisions=[{'id':item['id'],'action':'import','required':True,'category':'principal' if source['path'].endswith('USER.md') else 'project',
            'project':'lab','title':'Synthetic repeated lifecycle','content':item['content']}
            for source in current['sources'] for item in source['chunks'] if item['content']]
        plan=importer.plan(second,captured['snapshot_signature'],decisions,account='dashboard:owner')
        publication=importer.apply(second,captured['snapshot_signature'],plan['signature'],account='dashboard:owner')
        self.assertTrue(publication['required_items_verified'])
        return second,captured,plan

    def test_new_activation_after_verified_return_preserves_current_files(self):
        self.return_to_builtin()
        prompt=self.profile/'SOUL.md';current_prompt=prompt.read_bytes()
        path=self.profile/'memories/MEMORY.md';path.write_bytes(path.read_bytes()+b'\n\xc2\xa7\nSynthetic later built-in lifecycle fact.')
        later=path.read_bytes();second,captured,plan=self.import_current()
        prepared=self.fixture.operation().prepare(second,captured['snapshot_signature'],plan['signature'],
            self.home/'lifecycle-second-backup',account='dashboard:owner')
        self.assertEqual(prepared['state'],'ready')
        self.assertEqual(path.read_bytes(),later);self.assertEqual(prompt.read_bytes(),current_prompt)
        self.fixture.operation().apply(prepared['signature'],account='dashboard:owner')
        from ruamel.yaml import YAML
        current=YAML(typ='safe').load((self.profile/'config.yaml').read_bytes())
        self.assertTrue({'lifeos','lifeos-hook-bridge'}<=set(current['plugins']['enabled']))

    def test_exit_during_terminal_journal_archive_resumes_without_restoring_data(self):
        self.return_to_builtin();second,captured,plan=self.import_current()
        before={name:(self.profile/name).read_bytes() for name in ('config.yaml','SOUL.md','memories/MEMORY.md','memories/USER.md')}
        code='''import json,os,sys
from pathlib import Path
from lifeos_hook_bridge.memory_service import MemoryConfiguration
from lifeos_hook_bridge.memory_activation import MemoryActivation
settings=json.load(sys.stdin)
def trace(frame,event,arg):
 caller=frame.f_back
 if (event=='call' and frame.f_code.co_name=='_sync_directory' and caller is not None
   and caller.f_code.co_name=='_resume' and caller.f_code.co_filename.endswith('/memory_cycle.py')
   and caller.f_locals.get('name')=='.lifeos-memory-activation'):os._exit(73)
 return trace
sys.settrace(trace)
MemoryActivation(MemoryConfiguration(Path(settings['configuration'])),units=settings['units']).prepare(
 Path(settings['snapshot']),settings['snapshot_signature'],settings['plan_signature'],Path(settings['backup']),account='dashboard:owner')
'''
        settings={'configuration':str(self.configuration.path),'units':self.fixture.setup.services.units,
            'snapshot':str(second),'snapshot_signature':captured['snapshot_signature'],'plan_signature':plan['signature'],
            'backup':str(self.home/'lifecycle-second-backup')}
        result=subprocess.run([sys.executable,'-c',code],input=json.dumps(settings),capture_output=True,text=True,
            env=os.environ.copy(),timeout=45)
        self.assertEqual(result.returncode,73,result.stdout+result.stderr);self.assertEqual(result.stdout+result.stderr,'')
        self.assertTrue((self.profile/'.lifeos-memory-cycle.json').is_file())
        prepared=self.fixture.operation().prepare(second,captured['snapshot_signature'],plan['signature'],
            self.home/'lifecycle-second-backup',account='dashboard:owner')
        self.assertEqual(prepared['state'],'ready');self.assertFalse((self.profile/'.lifeos-memory-cycle.json').exists())
        for name,data in before.items():self.assertEqual((self.profile/name).read_bytes(),data)
        receipts=list((self.profile/'.lifeos-memory-cycle-history').glob('*/receipt.json'))
        self.assertEqual(len(receipts),1);self.assertEqual(json.loads(receipts[0].read_bytes()),
            {'state':'archived','configuration_restored':False,'memory_restored':False})

    def test_later_terminal_journal_edit_refuses_before_any_archive_or_service_stop(self):
        self.return_to_builtin();second,captured,plan=self.import_current()
        target=self.profile/'.lifeos-ownership/operation.json';later=target.read_bytes()+b'\n';edited=False
        before=self.fixture.setup.pids()
        def trace(frame,event,arg):
            nonlocal edited
            if (not edited and event=='call' and frame.f_code.co_name=='_resume'
                    and frame.f_code.co_filename.endswith('/memory_cycle.py')):
                edited=True;target.write_bytes(later)
            return trace
        sys.settrace(trace)
        try:
            with self.assertRaisesRegex(MemoryUnavailable,'changes'):
                self.fixture.operation().prepare(second,captured['snapshot_signature'],plan['signature'],
                    self.home/'lifecycle-second-backup',account='dashboard:owner')
        finally:sys.settrace(None)
        self.assertTrue(edited);self.assertEqual(target.read_bytes(),later)
        self.assertTrue((self.profile/'.lifeos-memory-activation/binding.json').is_file())
        self.assertEqual(self.fixture.setup.pids(),before)

    def test_other_owner_cannot_retire_the_verified_return(self):
        self.return_to_builtin();second,captured,plan=self.import_current()
        before=self.fixture.setup.pids()
        with self.assertRaises(PermissionError):
            self.fixture.operation().prepare(second,captured['snapshot_signature'],plan['signature'],
                self.home/'lifecycle-second-backup',account='dashboard:other')
        self.assertFalse((self.profile/'.lifeos-memory-cycle-history').exists())
        self.assertTrue((self.profile/'.lifeos-memory-transition/fresh-agent-verification.json').is_file())
        self.assertEqual(self.fixture.setup.pids(),before)
