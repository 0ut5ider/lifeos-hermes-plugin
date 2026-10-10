# ABOUTME: Exercises native current-state proposals and identity preference publication with real processes.
# ABOUTME: Uses disposable managed data to characterize owner behavior and refuse unbound writers.
from dataclasses import asdict
import json
import os
from pathlib import Path
import subprocess
import unittest

import test_memory_delegation as delegation_fixture


class MemoryManualStateTests(unittest.TestCase):
    def setUp(self):
        self.fixture = delegation_fixture.MemoryDelegationTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        self.directory = self.root / 'LIFEOS/USER/TELOS/CURRENT_STATE'
        self.directory.mkdir(parents=True)
        self.queue = self.directory / 'proposals.jsonl'
        self.target = self.directory / 'ACTIVITY.md'
        self.target.write_text('# Activity\nSynthetic existing activity\n')
        self.identity = self.root / 'LIFEOS/USER/PRINCIPAL/PRINCIPAL_IDENTITY.md'
        self.identity.write_text('---\npreferences:\n  temperature_unit: celsius\n  date_format: iso\n---\n')
        self.settings = self.root / 'settings.json'
        self.settings.write_text('{"synthetic_keep":true,"preferences":{"manual":"retained"}}')
        marker = self.root / 'LIFEOS/USER/CONFIG/memory-http.json'
        marker.write_text('{"version":1,"managed":true}')
        marker.chmod(0o600)

    def seed_queue(self, marker='SyntheticManualProposal'):
        row = {'id':'synthetic-proposal-id','timestamp':'2026-10-08T12:00:00+00:00',
               'source':'manual','target':'ACTIVITY','payload':{'name':marker},'status':'pending'}
        self.queue.write_text(json.dumps(row) + '\n')
        return row

    def call(self, tool, *arguments, context=True):
        environment = dict(os.environ, HOME=str(self.fixture.fixture.home),
                           LIFEOS_DIR=str(self.root / 'LIFEOS'), BUN_CONFIG_NO_AUTO_INSTALL='1')
        for key in ('LIFEOS_MEMORY_INTERNAL', 'LIFEOS_MEMORY_CONTEXT', 'LIFEOS_MEMORY_PUBLICATION_JOURNAL'):
            environment.pop(key, None)
        if context: environment['LIFEOS_MEMORY_CONTEXT'] = json.dumps(asdict(self.fixture.context))
        return subprocess.run(['bun','--no-install',str(self.root / 'LIFEOS/TOOLS' / tool),*arguments],
            capture_output=True,text=True,timeout=40,env=environment,cwd=self.fixture.fixture.home)

    def propose(self, *, context=True):
        return self.call('ProposeCurrentStateEntry.ts', '--source','manual','--target','ACTIVITY',
                         '--json','{"name":"SyntheticManualProposal"}',context=context)

    def test_unbound_proposal_cannot_create_queue(self):
        result = self.propose(context=False)
        self.assertNotEqual(result.returncode,0,result.stdout + result.stderr)
        self.assertFalse(self.queue.exists())

    def test_unbound_review_cannot_disclose_queue(self):
        self.seed_queue()
        before = self.queue.read_bytes()
        result = self.call('ApproveCurrentStateEntries.ts','--review',context=False)
        self.assertNotEqual(result.returncode,0,result.stdout + result.stderr)
        self.assertNotIn('SyntheticManualProposal',result.stdout + result.stderr)
        self.assertEqual(self.queue.read_bytes(),before)

    def test_unbound_approval_cannot_publish_or_remove_queue(self):
        row = self.seed_queue()
        before = (self.queue.read_bytes(),self.target.read_bytes())
        result = self.call('ApproveCurrentStateEntries.ts','--approve',row['id'],context=False)
        self.assertNotEqual(result.returncode,0,result.stdout + result.stderr)
        self.assertEqual((self.queue.read_bytes(),self.target.read_bytes()),before)

    def test_unbound_identity_sync_cannot_publish_preferences(self):
        before = self.settings.read_bytes()
        result = self.call('SyncIdentityToSettings.ts',context=False)
        self.assertNotEqual(result.returncode,0,result.stdout + result.stderr)
        self.assertNotIn('celsius',result.stdout + result.stderr)
        self.assertEqual(self.settings.read_bytes(),before)

    def test_native_owner_proposal_review_approval_and_rejection(self):
        result = self.propose()
        self.assertEqual(result.returncode,0,result.stderr)
        row = json.loads(self.queue.read_text())
        self.assertEqual(set(row),{'id','timestamp','source','target','payload','status'})
        self.assertEqual(row['payload'],{'name':'SyntheticManualProposal'})
        result = self.call('ApproveCurrentStateEntries.ts','--review')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('SyntheticManualProposal',result.stdout)
        result = self.call('ApproveCurrentStateEntries.ts','--approve',row['id'])
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('Synthetic existing activity',self.target.read_text())
        self.assertIn('name: "SyntheticManualProposal"',self.target.read_text())
        self.assertEqual(self.queue.read_text(),'')
        self.seed_queue('SyntheticRejectedProposal')
        result = self.call('ApproveCurrentStateEntries.ts','--reject','synthetic-proposal-id')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(self.queue.read_text(),'')
        self.assertNotIn('SyntheticRejectedProposal',self.target.read_text())

    def test_native_identity_sync_preserves_settings_and_repeat_bytes(self):
        result = self.call('SyncIdentityToSettings.ts')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(self.settings.read_text()), {'synthetic_keep':True,'preferences':{
            'manual':'retained','temperatureUnit':'celsius','dateFormat':'iso'}})
        before = (self.settings.read_bytes(),self.settings.stat().st_mtime_ns)
        result = self.call('SyncIdentityToSettings.ts')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual((self.settings.read_bytes(),self.settings.stat().st_mtime_ns),before)

    def test_native_identity_noop_keeps_carriage_returns_and_mtime(self):
        self.settings.write_bytes(b'{\r\n  "preferences": {"temperatureUnit":"celsius", "dateFormat":"iso"}\r\n}\r\n')
        before = (self.settings.read_bytes(),self.settings.stat().st_mtime_ns)
        result = self.call('SyncIdentityToSettings.ts')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual((self.settings.read_bytes(),self.settings.stat().st_mtime_ns),before)

    def test_native_proposal_append_keeps_existing_queue_line_bytes(self):
        row = self.seed_queue()
        before = (json.dumps(row) + '\r\n').encode()
        self.queue.write_bytes(before)
        result = self.propose()
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertTrue(self.queue.read_bytes().startswith(before))
        self.assertEqual(len(self.queue.read_text().splitlines()),2)

    def test_read_only_owner_can_review_but_cannot_publish(self):
        row = self.seed_queue()
        before = (self.queue.read_bytes(),self.target.read_bytes(),self.settings.read_bytes())
        self.fixture.configuration.update(lambda value:value['destinations']['chat-a:200'].update(write=[]))
        result = self.call('ApproveCurrentStateEntries.ts','--review')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('SyntheticManualProposal',result.stdout)
        for tool,arguments in (('ProposeCurrentStateEntry.ts', ['--source','manual','--target','ACTIVITY','--json','{}']),
                ('ApproveCurrentStateEntries.ts',['--approve',row['id']]), ('ApproveCurrentStateEntries.ts',['--reject',row['id']]),
                ('SyncIdentityToSettings.ts',[])):
            with self.subTest(tool=tool,arguments=arguments):
                self.assertNotEqual(self.call(tool,*arguments).returncode,0)
                self.assertEqual((self.queue.read_bytes(),self.target.read_bytes(),self.settings.read_bytes()),before)

    def test_private_inputs_refuse_without_source_disclosure_or_publication(self):
        marker = '<private>SyntheticManualPrivate</private>'
        for mode in ('queue','identity','payload'):
            with self.subTest(mode=mode):
                self.seed_queue(marker if mode == 'queue' else 'SyntheticManualProposal')
                self.identity.write_text('---\npreferences:\n  temperature_unit: '+(marker if mode == 'identity' else 'celsius')+'\n---\n')
                before = (self.queue.read_bytes(),self.target.read_bytes(),self.settings.read_bytes())
                result = (self.call('ApproveCurrentStateEntries.ts','--review') if mode == 'queue' else
                    self.call('SyncIdentityToSettings.ts') if mode == 'identity' else
                    self.call('ProposeCurrentStateEntry.ts','--source','manual','--target','ACTIVITY','--json',json.dumps({'name':marker})))
                self.assertNotEqual(result.returncode,0)
                self.assertNotIn('SyntheticManualPrivate',result.stdout + result.stderr)
                self.assertEqual((self.queue.read_bytes(),self.target.read_bytes(),self.settings.read_bytes()),before)

    def test_forgotten_queue_content_cannot_return_through_review_or_approval(self):
        from test_memory_native import OWNER
        self.seed_queue('SyntheticManualRetired')
        saved = self.fixture.fixture.memory.remember(OWNER,category='principal',content='RULE: SyntheticManualRetired',
            title='',project='',request_id='manual-retained')
        self.fixture.fixture.memory.forget(OWNER,saved['reference'],'manual-forget')
        before = (self.queue.read_bytes(),self.target.read_bytes())
        for arguments in (['--review'],['--approve','synthetic-proposal-id']):
            result = self.call('ApproveCurrentStateEntries.ts',*arguments)
            self.assertNotEqual(result.returncode,0)
            self.assertNotIn('SyntheticManualRetired',result.stdout + result.stderr)
            self.assertEqual((self.queue.read_bytes(),self.target.read_bytes()),before)

    def test_redirected_sources_and_missing_connector_cannot_fall_back(self):
        self.seed_queue()
        outside = self.fixture.fixture.home / 'synthetic-manual-outside.jsonl'
        outside.write_bytes(self.queue.read_bytes())
        for mode in ('symlink','hardlink','missing'):
            with self.subTest(mode=mode):
                self.queue.unlink()
                if mode == 'symlink': self.queue.symlink_to(outside)
                elif mode == 'hardlink': os.link(outside,self.queue)
                else:
                    self.seed_queue()
                    (self.root / 'LIFEOS/USER/CONFIG/memory-access.json').unlink()
                result = self.call('ApproveCurrentStateEntries.ts','--review')
                self.assertNotEqual(result.returncode,0)
                self.assertNotIn('SyntheticManualProposal',result.stdout + result.stderr)
        self.assertIn('SyntheticManualProposal',outside.read_text())

    def test_private_files_and_unrelated_state_remain_intact(self):
        unrelated = self.directory / 'SOCIAL.md'
        unrelated.write_text('<private>SyntheticUnrelatedPrivate</private>\n')
        before = (unrelated.read_bytes(),unrelated.stat().st_mtime_ns)
        result = self.propose()
        self.assertEqual(result.returncode,0,result.stderr)
        row = json.loads(self.queue.read_text())
        result = self.call('ApproveCurrentStateEntries.ts','--approve',row['id'])
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(self.queue.stat().st_mode & 0o777,0o600)
        self.assertEqual(self.target.stat().st_mode & 0o777,0o600)
        self.assertEqual((unrelated.read_bytes(),unrelated.stat().st_mtime_ns),before)
        result = self.call('SyncIdentityToSettings.ts')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(self.settings.stat().st_mode & 0o777,0o600)

    def test_missing_approval_target_preserves_queue_after_native_loss_control(self):
        row = self.seed_queue()
        self.target.unlink()
        source = Path(os.environ['LIFEOS_HARVEST_CONTROL_SOURCE'])
        result = subprocess.run(['bun','--no-install',str(source / 'LIFEOS/TOOLS/ApproveCurrentStateEntries.ts'),
            '--approve',row['id']],capture_output=True,text=True,timeout=30,
            env=dict(os.environ,HOME=str(self.fixture.fixture.home),LIFEOS_DIR=str(self.root / 'LIFEOS')))
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('Target file does not exist',result.stderr)
        self.assertEqual(self.queue.read_text(),'')
        self.seed_queue()
        before = self.queue.read_bytes()
        result = self.call('ApproveCurrentStateEntries.ts','--approve',row['id'])
        self.assertNotEqual(result.returncode,0)
        self.assertEqual(self.queue.read_bytes(),before)
        self.assertFalse(self.target.exists())

    def test_actual_native_render_rechecks_bytes_inode_creation_and_owner(self):
        import sys
        for mode in ('source','metadata','created','authority'):
            with self.subTest(mode=mode):
                self.seed_queue()
                if mode == 'created': self.queue.unlink()
                result = subprocess.run([sys.executable,str(Path(__file__).with_name('memory_manual_state_process.py')),
                    str(self.fixture.configuration.path),json.dumps(asdict(self.fixture.context)),mode],
                    capture_output=True,text=True,timeout=30)
                self.assertEqual(result.returncode,0,result.stderr)
                self.assertEqual(result.stderr,'')
                self.assertEqual(json.loads(result.stdout),{'rendered':True,'withheld':True})
                self.assertNotIn('name: "SyntheticManualProposal"',self.target.read_text())

    def test_process_interruption_recovers_queue_and_target_before_retry(self):
        import sys
        self.seed_queue()
        before = (self.queue.read_bytes(),self.target.read_bytes())
        result = subprocess.run([sys.executable,str(Path(__file__).with_name('memory_manual_state_process.py')),
            str(self.fixture.configuration.path),json.dumps(asdict(self.fixture.context)),'publication-kill'],
            capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,71,result.stderr)
        self.assertEqual(result.stderr,'')
        self.assertIn('name: "SyntheticManualProposal"',self.target.read_text())
        memory = self.fixture.fixture.memory
        with memory._transaction(): pass
        self.assertEqual((self.queue.read_bytes(),self.target.read_bytes()),before)
        result = self.call('ApproveCurrentStateEntries.ts','--approve','synthetic-proposal-id')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(self.target.read_text().count('name: "SyntheticManualProposal"'),1)
        self.assertEqual(self.queue.read_text(),'')

    def test_malformed_tool_and_queue_target_return_a_refusal(self):
        from lifeos_hook_bridge.memory_service import MemoryService
        service = MemoryService(self.fixture.configuration)
        result = service.native(self.fixture.context,'manual_state',{'tool':[], 'args':[]})
        self.assertFalse(result['ok'],result)
        row = self.seed_queue()
        row['target'] = []
        self.queue.write_text(json.dumps(row)+'\n')
        result = service.native(self.fixture.context,'manual_state',{
            'tool':'ApproveCurrentStateEntries.ts','args':['--review']})
        self.assertFalse(result['ok'],result)

    def test_exact_review_restores_safe_old_queue_settings_and_identity(self):
        from test_memory_native import OWNER
        from lifeos_hook_bridge.memory_source_review import preview, approve
        from lifeos_hook_bridge.memory_service import MemoryService
        self.seed_queue()
        memory = self.fixture.fixture.memory
        saved = memory.remember(OWNER,category='principal',content='RULE: SyntheticUnrelatedManualRetirement',
            title='',project='',request_id='manual-review-retained')
        memory.forget(OWNER,saved['reference'],'manual-review-forget')
        paths = ['LIFEOS/USER/TELOS/CURRENT_STATE/proposals.jsonl',
                 'LIFEOS/USER/PRINCIPAL/PRINCIPAL_IDENTITY.md','settings.json']
        for relative in paths: os.utime(self.root / relative,(1_577_836_800,1_577_836_800))
        before = [(self.root / path).read_bytes() for path in paths]
        self.assertNotEqual(self.call('ApproveCurrentStateEntries.ts','--review').returncode,0)
        self.assertNotEqual(self.call('SyncIdentityToSettings.ts').returncode,0)
        service = MemoryService(self.fixture.configuration)
        configuration = self.fixture.configuration.load()
        scope = service._context_scope(configuration,self.fixture.context)
        snapshot = preview(memory,scope,paths)
        self.assertTrue(all(row['accepted'] for row in snapshot['sources']),snapshot)
        result = approve(memory,scope,paths,snapshot['signature'],
            check_current=lambda:service._check_current_context(configuration,self.fixture.context,scope))
        self.assertEqual(result['status'],'committed',result)
        self.assertEqual([(self.root / path).read_bytes() for path in paths],before)
        result = self.call('ApproveCurrentStateEntries.ts','--review')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('SyntheticManualProposal',result.stdout)
        result = self.call('SyncIdentityToSettings.ts')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(self.settings.read_text())['preferences']['temperatureUnit'],'celsius')

    def test_complete_queue_without_newline_cannot_publish_malformed_append(self):
        self.seed_queue()
        self.queue.write_bytes(self.queue.read_bytes().rstrip(b'\n'))
        before = self.queue.read_bytes()
        result = self.propose()
        self.assertNotEqual(result.returncode,0)
        self.assertEqual(self.queue.read_bytes(),before)

    def test_bulk_approval_keeps_native_targets_and_repeat_does_not_duplicate(self):
        row = self.seed_queue()
        second = dict(row,id='synthetic-second-proposal',target='SIGNALS',payload={'name':'SyntheticSecondProposal'})
        self.queue.write_text(json.dumps(row)+'\n'+json.dumps(second)+'\n')
        other = self.directory / 'SIGNALS.md'
        other.write_text('# Signals\nSynthetic existing signal\n')
        result = self.call('ApproveCurrentStateEntries.ts','--approve-all')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(self.queue.read_text(),'')
        self.assertEqual(self.target.read_text().count('name: "SyntheticManualProposal"'),1)
        self.assertEqual(other.read_text().count('name: "SyntheticSecondProposal"'),1)
        before = [(path.read_bytes(),path.stat().st_mtime_ns) for path in (self.queue,self.target,other)]
        result = self.call('ApproveCurrentStateEntries.ts','--approve-all')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual([(path.read_bytes(),path.stat().st_mtime_ns) for path in (self.queue,self.target,other)],before)
