# ABOUTME: Characterizes original native Content run requests and file disposal with synthetic data.
# ABOUTME: Records ledger effects, repeated requests, trash movement, and missing-item responses.
import json
from datetime import datetime
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


class NativeContentActionTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory(prefix='native-content-actions-')
        self.addCleanup(self.directory.cleanup)
        self.home=Path(self.directory.name)
        self.root=self.home/'.claude'
        self.events=self.root/'LIFEOS/MEMORY/STATE/content-pipeline/events.jsonl'
        self.events.parent.mkdir(parents=True)
        self.source=self.home/'Recordings/Inbox/synthetic.wav'
        self.source.parent.mkdir(parents=True)
        self.source.write_bytes(b'Synthetic media bytes for disposal characterization.')
        self.sidecar=Path(str(self.source)+'.md')
        self.sidecar.write_text('title: Synthetic native Content item.\n')
        self.seed={'v':1,'ts':'2026-10-09T12:00:00Z','id':'synthetic1','op':'upsert','src':'synthetic',
            'fields':{'id':'synthetic1','path':str(self.source),'title':'Synthetic native Content item.',
                'stage':'inbox','stage_status':'pending','created':'2026-10-09T12:00:00Z'}}
        self.events.write_text(json.dumps(self.seed)+'\n')

    def request(self,method,target):
        source=Path(os.environ['LIFEOS_HARVEST_CONTROL_SOURCE'])/'LIFEOS/PULSE/modules/content.ts'
        program='import {handleRequest} from '+json.dumps(str(source))+';const request=new Request('+json.dumps('http://localhost'+target)+',{method:'+json.dumps(method)+'});const response=await handleRequest(request,new URL(request.url).pathname);console.log(JSON.stringify({status:response?.status,body:response ? await response.json():null}));'
        result=subprocess.run(['bun','--no-install','-e',program],capture_output=True,text=True,timeout=20,
            env=dict(os.environ,HOME=str(self.home),CLAUDE_CONFIG_DIR=str(self.root),LIFEOS_DIR=str(self.root/'LIFEOS')))
        self.assertEqual((result.returncode,result.stderr),(0,''))
        return json.loads(result.stdout)

    def test_original_run_request_is_one_native_ledger_upsert_and_repeats_without_append(self):
        result=self.request('POST','/api/content/synthetic1/run')
        self.assertEqual(result,{'status':200,'body':{'ok':True,'id':'synthetic1','requested_run':'regular'}})
        rows=[json.loads(line) for line in self.events.read_text().splitlines()]
        self.assertEqual(len(rows),2)
        self.assertEqual({key:value for key,value in rows[-1].items() if key!='ts'},
            {'v':1,'id':'synthetic1','op':'upsert','src':'dashboard','fields':rows[-1]['fields']})
        self.assertEqual(set(rows[-1]['fields']),{'requested_run','requested_at','updated'})
        self.assertEqual(rows[-1]['fields']['requested_run'],'regular')
        self.assertLessEqual(datetime.fromisoformat(rows[-1]['fields']['requested_at']),datetime.fromisoformat(rows[-1]['fields']['updated']))
        before=self.events.read_bytes()
        self.assertEqual(self.request('POST','/api/content/synthetic1/run'),
            {'status':200,'body':{'ok':True,'id':'synthetic1','already':True}})
        self.assertEqual(self.events.read_bytes(),before)
        self.assertTrue(self.source.exists())

    def test_original_delete_appends_tombstone_moves_source_and_sidecar_and_removes_artifacts(self):
        artifact=self.root/'LIFEOS/MEMORY/STATE/content-pipeline/artifacts/synthetic1/transcript.md'
        artifact.parent.mkdir(parents=True)
        artifact.write_text('Synthetic derivative transcript.\n')
        source=self.source.read_bytes()
        sidecar=self.sidecar.read_bytes()
        result=self.request('DELETE','/api/content/synthetic1')
        self.assertEqual(result,{'status':200,'body':{'ok':True,'id':'synthetic1','trashed':2,
            'artifactsRemoved':True,'runnerKicked':False}})
        self.assertFalse(self.source.exists())
        self.assertFalse(self.sidecar.exists())
        self.assertEqual((self.source.parent/'.trash'/self.source.name).read_bytes(),source)
        self.assertEqual((self.source.parent/'.trash'/self.sidecar.name).read_bytes(),sidecar)
        self.assertFalse(artifact.parent.exists())
        rows=[json.loads(line) for line in self.events.read_text().splitlines()]
        self.assertEqual(len(rows),2)
        self.assertEqual({key:value for key,value in rows[-1].items() if key!='ts'},
            {'v':1,'id':'synthetic1','op':'delete','src':'dashboard'})
        before=self.events.read_bytes()
        self.assertEqual(self.request('DELETE','/api/content/synthetic1'),
            {'status':404,'body':{'error':'no item synthetic1'}})
        self.assertEqual(self.events.read_bytes(),before)

    def test_original_missing_run_request_does_not_append_or_change_the_source(self):
        before=self.events.read_bytes()
        self.assertEqual(self.request('POST','/api/content/missing1/run'),
            {'status':404,'body':{'error':'no item missing1'}})
        self.assertEqual(self.events.read_bytes(),before)
        self.assertTrue(self.source.exists())

    def test_original_unknown_prototype_named_item_creates_a_phantom_request_known_bug(self):
        result=self.request('POST','/api/content/constructor/run')
        self.assertEqual(result,{'status':200,'body':{'ok':True,'id':'constructor','requested_run':'regular'}})
        rows=[json.loads(line) for line in self.events.read_text().splitlines()]
        self.assertEqual(len(rows),2)
        self.assertEqual(rows[-1]['id'],'constructor')
