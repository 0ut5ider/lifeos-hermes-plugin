# ABOUTME: Verifies native proposal consumers use the governed service under a trusted context.
# ABOUTME: Runs real Bun and Python subprocesses for direct decisions and automatic review.
from dataclasses import asdict
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

from lifeos_hook_bridge.memory_policy import SessionContext
from lifeos_hook_bridge.memory_service import MemoryConfiguration
import test_memory_proposals as proposal_fixture


class MemoryProposalDelegationTests(unittest.TestCase):
    def setUp(self):
        self.fixture = proposal_fixture.MemoryProposalTests(); self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.fixture.root
        self.config = self.fixture.fixture.home / 'hermes/memory.json'
        self.value = {'version':1,'root':str(self.root),'principal':'owner',
                      'accounts':{'chat-a:100':'owner'},'destinations':{'chat-a:200':{
                          'visibility':'private','participants':['owner'],'read':['principal','assistant','project'],
                          'write':['principal','assistant','project'],'projects':['*'],'model_routes':['local'],
                          'proposals':['create','review','approve','auto_apply']}}}
        MemoryConfiguration(self.config).save(self.value)
        program = Path(__file__).resolve().parents[1] / 'lifeos_hook_bridge/memory_rpc.py'
        connector = self.root / 'LIFEOS/USER/CONFIG/memory-access.json'
        connector.write_text(json.dumps({'version':1,'command':[sys.executable,str(program),'--configuration',str(self.config)]}))
        connector.chmod(0o600)
        self.context = SessionContext('chat-a','100','200','private',('owner',),'local','native-session')

    def call(self, action, **values):
        code = '''
import {pathToFileURL} from 'node:url';
const request = JSON.parse(await Bun.stdin.text());
const root = process.env.HOME + '/.claude';
const proposals = await import(pathToFileURL(root+'/LIFEOS/PULSE/lib/memory-proposals.ts').href);
let result;
if(request.action === 'list') result = proposals.loadProposalQueue();
else if(request.action === 'accept') result = proposals.acceptProposal(request.id);
else if(request.action === 'raw_apply') result = proposals.applyProposalEdit(request.target, request.edit);
else if(request.action === 'raw_mark') {
  try { result = proposals.markProposal(request.id, {status:'accepted'}); }
  catch(error) { result = {ok:false,reason:String(error)}; }
}
else if(request.action === 'dispatch') {
  const reviewer = await import(pathToFileURL(root+'/LIFEOS/TOOLS/MemoryReviewer.ts').href);
  result = reviewer.dispatchItems(request.items, {confidenceThreshold:0.7});
}
console.log(JSON.stringify(result));
'''
        environment = dict(os.environ, HOME=str(self.fixture.fixture.home), LIFEOS_DIR=str(self.root/'LIFEOS'),
                           LIFEOS_MEMORY_CONTEXT=json.dumps(asdict(self.context)), BUN_CONFIG_NO_AUTO_INSTALL='1')
        environment.pop('LIFEOS_MEMORY_INTERNAL',None)
        response = subprocess.run(['bun','--no-install','--eval',code],input=json.dumps({'action':action,**values}),
                                  text=True,capture_output=True,env=environment,cwd=self.root,timeout=40)
        self.assertEqual(response.returncode,0,response.stderr)
        self.assertEqual(response.stderr,'')
        return json.loads(response.stdout)

    def test_direct_native_decision_updates_the_managed_reference(self):
        saved = self.fixture.enqueue()
        reference = saved['receipt']['proposal_reference']
        result = self.call('accept',id=reference['id'])
        self.assertTrue(result['ok'], result)
        self.assertEqual(result['receipt']['status'],'committed')
        self.assertEqual(self.fixture.memory.review_proposals(self.fixture.scope),[])
        self.assertEqual(self.call('list')[0]['status'],'accepted')
        retry = self.fixture.memory.decide_proposal(self.fixture.scope,reference,'accept','after-native')
        self.assertEqual(retry['status'],'conflict',retry)
        self.assertIn(self.fixture.item()['edit'], self.fixture.target.read_text())

    def test_native_queue_read_and_decision_obey_revocation(self):
        saved = self.fixture.enqueue()
        self.assertEqual(len(self.call('list')),1)
        self.value['destinations']['chat-a:200']['proposals']=[]
        MemoryConfiguration(self.config).save(self.value)
        self.assertEqual(self.call('list'),[])
        result = self.call('accept',id=saved['receipt']['proposal_reference']['id'])
        self.assertFalse(result['ok'],result)
        self.assertNotIn(self.fixture.item()['edit'],self.fixture.target.read_text())

    def test_raw_native_writers_cannot_bypass_proposal_decisions(self):
        saved = self.fixture.enqueue()
        result = self.call('raw_apply',target=str(self.fixture.target),edit='Synthetic bypass marker')
        self.assertFalse(result['ok'],result)
        result = self.call('raw_mark',id=saved['receipt']['proposal_reference']['id'])
        self.assertFalse(result['ok'],result)
        self.assertNotIn('Synthetic bypass marker',self.fixture.target.read_text())
        self.assertEqual(len(self.fixture.memory.review_proposals(self.fixture.scope)),1)

    def test_native_reviewer_auto_application_and_diversion_use_governed_decisions(self):
        result = self.call('dispatch',items=[self.fixture.item(confidence=0.9)])
        self.assertEqual(result['summary']['proposals_auto_applied'],1,result)
        self.assertEqual(self.fixture.memory.review_proposals(self.fixture.scope),[])
        self.assertIn(self.fixture.item()['edit'],self.fixture.target.read_text())
        result = self.call('dispatch',items=[self.fixture.item('SyntheticLab must keep its own synthetic deployment checklist.',confidence=0.9)])
        self.assertEqual(result['summary']['succeeded'],1,result)
        self.assertEqual(result['summary']['proposals_auto_applied'],0,result)
        self.assertEqual(result['summary']['proposals_auto_apply_failed'],0,result)
        self.assertNotIn('own synthetic deployment checklist',self.fixture.target.read_text())

    def test_native_reviewer_does_not_infer_approval_from_a_creation_grant(self):
        self.value['destinations']['chat-a:200']['proposals']=['create','review']
        MemoryConfiguration(self.config).save(self.value)
        result = self.call('dispatch',items=[self.fixture.item(confidence=0.9)])
        self.assertEqual(result['summary']['proposals_auto_applied'],0,result)
        self.assertEqual(result['summary']['proposals_auto_apply_failed'],1,result)
        self.assertEqual(len(self.fixture.memory.review_proposals(self.fixture.scope)),1)
        self.assertNotIn(self.fixture.item()['edit'],self.fixture.target.read_text())
