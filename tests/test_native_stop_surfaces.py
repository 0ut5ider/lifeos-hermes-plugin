# ABOUTME: Measures actual notification requests and completion gates in disposable native homes.
# ABOUTME: Retains real HTTP, filesystem, command failures, and interruption effects.
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import shutil
import subprocess
import threading
import time
import unittest

from lifeos_hook_bridge.bridge import HookBridge
import test_native_completion_policies as completion
import test_native_lifecycle_branches as lifecycle

SOURCE=os.environ.get('LIFEOS_GUARD_SOURCE')


@unittest.skipUnless(SOURCE and shutil.which('bun'), 'Prepared native Stop programs and Bun are required')
class NativeStopSurfaceTests(unittest.TestCase):
    def fixture(self):
        fixture=lifecycle.NativeLifecycleBranchTests()
        home,root,environment=fixture.fixture()
        self.addCleanup(fixture.doCleanups)
        (root/'settings.json').write_text('{}')
        return home,root,environment

    def call(self,root,environment,name,payload):
        return subprocess.run([shutil.which('bun'),str(Path(SOURCE)/'hooks'/(name+'.hook.ts'))],
            input=json.dumps(payload),env=environment,cwd=root,text=True,capture_output=True,timeout=20)

    def receiver(self):
        requests=[];received=threading.Event();release=threading.Event()
        class Receiver(BaseHTTPRequestHandler):
            def do_POST(self):
                requests.append({'path':self.path,'body':json.loads(self.rfile.read(int(self.headers['Content-Length'])))})
                received.set()
                if getattr(self.server,'pause',False):release.wait(5)
                self.send_response(self.server.status);self.end_headers()
                try:self.wfile.write(b'{}')
                except BrokenPipeError:pass
            def log_message(self,*_):pass
        server=ThreadingHTTPServer(('127.0.0.1',0),Receiver);server.status=200
        threading.Thread(target=server.serve_forever,daemon=True).start()
        self.addCleanup(server.server_close);self.addCleanup(server.shutdown);self.addCleanup(release.set)
        return server,requests,received,release

    def test_voice_actual_notification_channel_policy_and_repeated_stop(self):
        _,root,environment=self.fixture()
        server,requests,_,_=self.receiver()
        environment['PULSE_URL']=f'http://127.0.0.1:{server.server_port}'
        transcript=root/'voice-transcript.jsonl';transcript.write_text('')
        payload={'session_id':'voice','hook_event_name':'Stop','transcript_path':str(transcript),
                 'last_assistant_message':'🗣️ Fixture: Synthetic laboratory checks completed.'}
        for channel in ('discord','headless','disabled'):
            result=self.call(root,environment|{'LIFEOS_NOTIFICATION_CHANNEL':channel},'VoiceCompletion',payload)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertIn('Voice OFF',result.stderr)
        self.assertEqual(requests,[])
        desktop=environment|{'LIFEOS_NOTIFICATION_CHANNEL':'desktop'}
        child=self.call(root,desktop|{'CLAUDE_CODE_AGENT_TASK_ID':'synthetic-child'},'VoiceCompletion',payload)
        self.assertIn('not main session',child.stderr);self.assertEqual(requests,[])
        for _ in range(2):
            result=self.call(root,desktop,'VoiceCompletion',payload)
            self.assertEqual((result.returncode,result.stderr),(0,''))
        self.assertEqual(len(requests),2)
        self.assertTrue(all(row['path']=='/notify' and row['body']['voice_enabled'] is True for row in requests))
        self.assertTrue(all(row['body']['message']=='Synthetic laboratory checks completed.' for row in requests))
        rows=[json.loads(line) for line in (root/'LIFEOS/MEMORY/VOICE/voice-events.jsonl').read_text().splitlines()]
        self.assertEqual([row['event_type'] for row in rows],['skipped']*3+['sent']*2)
        invalid=subprocess.run([shutil.which('bun'),str(Path(SOURCE)/'hooks/VoiceCompletion.hook.ts')],
            input='{invalid',env=desktop,text=True,capture_output=True,timeout=10)
        self.assertEqual(invalid.returncode,0)
        self.assertIn('JSON',invalid.stderr)
        self.assertEqual(len(requests),2)

    def test_voice_failure_and_interruption_never_record_sent_notification(self):
        _,root,environment=self.fixture()
        server,requests,received,release=self.receiver()
        environment.update(PULSE_URL=f'http://127.0.0.1:{server.server_port}',LIFEOS_NOTIFICATION_CHANNEL='desktop')
        transcript=root/'voice-transcript.jsonl';transcript.write_text('')
        payload={'session_id':'voice','hook_event_name':'Stop','transcript_path':str(transcript),
                 'last_assistant_message':'🗣️ Fixture: Synthetic completion notification.'}
        server.status=503
        failed=self.call(root,environment,'VoiceCompletion',payload)
        self.assertEqual(failed.returncode,0);self.assertIn('Server error',failed.stderr)
        log=root/'LIFEOS/MEMORY/VOICE/voice-events.jsonl'
        prior=log.read_bytes();self.assertEqual(json.loads(prior)['event_type'],'failed')
        server.status=200;server.pause=True;received.clear()
        process=subprocess.Popen([shutil.which('bun'),str(Path(SOURCE)/'hooks/VoiceCompletion.hook.ts')],
            env=environment,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        process.stdin.write(json.dumps(payload));process.stdin.close();process.stdin=None
        try:
            self.assertTrue(received.wait(5),'The actual native HTTP request was not reached')
        finally:
            if process.poll() is None:process.kill()
            stdout,stderr=process.communicate(timeout=5);release.set()
        self.assertEqual(process.returncode,-9,(stdout,stderr))
        self.assertEqual(log.read_bytes(),prior)
        self.assertEqual(len(requests),2)

    def test_actual_failed_command_blocks_false_completion_and_accepts_recovery(self):
        home,root,environment=self.fixture()
        settings=root/'settings.json'
        settings.write_text(json.dumps({'hooks':{'Stop':[{'hooks':[{'type':'command',
            'command':'bun '+str(Path(SOURCE)/'hooks/StopGates.hook.ts')}]}]}}))
        bridge=HookBridge(settings,root,lifeos_home=home);bridge.environment.update(environment);self.addCleanup(bridge.close)
        bridge.pre_llm_call('Run the synthetic command',session_id='failure-control')
        actual=subprocess.run(['sh','-c',"printf 'command failed with exit code 7'; exit 7"],capture_output=True,text=True)
        self.assertEqual(actual.returncode,7)
        bridge.post_tool_call('terminal',{'command':"sh -c 'exit 7'"},actual.stdout,session_id='failure-control',
                              status='error',error_message=actual.stdout,tool_call_id='failed-command')
        blocked=bridge.stop('Done. The command succeeded.',session_id='failure-control')
        self.assertIsNotNone(blocked);self.assertIn('CONTRADICTED COMPLETION',blocked['message'])
        self.assertIsNone(bridge.stop('The command failed with exit code 7.',session_id='failure-control'))
        self.assertIsNone(bridge.stop('Done. The command succeeded.',session_id='failure-control',stop_hook_active=True))
        success=subprocess.run(['sh','-c','printf verified'],capture_output=True,text=True)
        self.assertEqual(success.returncode,0)
        bridge.post_tool_call('terminal',{'command':'printf verified'},success.stdout,session_id='failure-control',tool_call_id='recovered-command')
        self.assertIsNone(bridge.stop('Done. The command succeeded.',session_id='failure-control'))

    def test_format_final_message_observation_and_writing_detector_availability(self):
        _,root,environment=self.fixture()
        transcript=root/'transcript.jsonl'
        payload={'session_id':'format','hook_event_name':'Stop','transcript_path':str(transcript)}
        for message,decision in [('Synthetic answer without the format','flag'),
            ('════ LifeOS\nSynthetic answer.\n🗣️ Synthetic answer completed.','pass')]:
            transcript.write_text(json.dumps({'type':'assistant','message':{'role':'assistant','content':message}})+'\n')
            result=self.call(root,environment,'StopGates',payload|{'last_assistant_message':message})
            self.assertEqual((result.returncode,result.stdout,result.stderr),(0,'',''))
            row=json.loads((root/'LIFEOS/MEMORY/OBSERVABILITY/format-gate.jsonl').read_text().splitlines()[-1])
            self.assertEqual(row['decision'],decision)
        message="Here's the post: "+' '.join(['Synthetic laboratory prose for the supplied fixture.']*10)
        transcript.write_text(json.dumps({'type':'assistant','message':{'role':'assistant','content':message}})+'\n')
        environment.pop('PANGRAM_API_KEY',None)
        missing=self.call(root,environment,'StopGates',payload|{'last_assistant_message':message})
        self.assertEqual((missing.returncode,missing.stdout,missing.stderr),(0,'',''))
        row=json.loads((root/'LIFEOS/MEMORY/OBSERVABILITY/writing-gate.jsonl').read_text().splitlines()[-1])
        self.assertEqual(row['decision'],'telemetry-no-detector')
        # This configured-detector policy control performs no detector request and claims no detector result.
        configured=self.call(root,environment|{'PANGRAM_API_KEY':'SYNTHETIC_AVAILABILITY_ONLY'},'StopGates',payload|{'last_assistant_message':message})
        self.assertEqual((configured.returncode,configured.stderr),(0,''))
        self.assertEqual(json.loads(configured.stdout)['decision'],'block')
        recovery=self.call(root,environment|{'PANGRAM_API_KEY':'SYNTHETIC_AVAILABILITY_ONLY'},'StopGates',payload|{
            'last_assistant_message':message,'stop_hook_active':True})
        self.assertEqual((recovery.returncode,json.loads(recovery.stdout),recovery.stderr),(0,{'continue':True},''))

    def test_render_concurrent_publication_preserves_complete_page(self):
        _,root,environment=self.fixture()
        isa=root/'ISA.md';isa.write_text('---\nphase: complete\ntitle: Synthetic Concurrent Mirror\nprogress: 1/1\n---\n## Criteria\n- [x] Fixture criterion\n')
        preload=root/'render-delay.cjs'
        preload.write_text('// ABOUTME: Widens actual mirror temporary-file publication for a race control.\n'
            '// ABOUTME: Leaves rendering and filesystem bytes unchanged.\n'
            "const fs=require('node:fs');const write=fs.writeFileSync;fs.writeFileSync=function(path,...args){const result=write.call(this,path,...args);if(String(path).includes('ISA.html.tmp'))Atomics.wait(new Int32Array(new SharedArrayBuffer(4)),0,0,100);return result;};\n")
        command=[shutil.which('bun'),'--preload',str(preload),str(Path(SOURCE)/'LIFEOS/TOOLS/ISARender.ts'),str(isa),'--no-refresh']
        with ThreadPoolExecutor(max_workers=8) as pool:
            results=list(pool.map(lambda _:subprocess.run(command,env=environment,text=True,capture_output=True,timeout=15),range(8)))
        self.assertTrue(all(row.returncode==0 for row in results),[(row.returncode,row.stderr) for row in results])
        self.assertIn('Synthetic Concurrent Mirror',(root/'ISA.html').read_text())
        self.assertEqual(list(root.glob('ISA.html.tmp*')),[])

    def test_render_missing_executable_records_spawn_failure_and_preserves_prior_page(self):
        home,root,environment=self.fixture()
        state=root/'LIFEOS/MEMORY/STATE/isa-render-debounce';state.mkdir()
        isa=root/'ISA.md';isa.write_text('---\nphase: complete\ntitle: Synthetic Spawn Failure\n---\n')
        page=root/'ISA.html';page.write_text('Synthetic prior mirror')
        pending=state/'render.json';pending.write_text(json.dumps({'edited_isas':[str(isa)]}))
        empty=home/'empty-bin';empty.mkdir();environment['PATH']=str(empty)
        result=self.call(root,environment,'ISARenderOnStop',{'session_id':'render','hook_event_name':'Stop'})
        self.assertEqual((result.returncode,json.loads(result.stdout)),(0,{'continue':True}),result.stderr)
        row=json.loads((root/'LIFEOS/MEMORY/OBSERVABILITY/isa-render.jsonl').read_text().splitlines()[-1])
        self.assertEqual(row['rendered'],[])
        self.assertEqual(row['skipped'],[str(isa)+':spawn-failed'])
        self.assertEqual(page.read_text(),'Synthetic prior mirror')

    def test_render_interrupted_rename_keeps_prior_complete_page(self):
        _,root,environment=self.fixture()
        isa=root/'ISA.md';isa.write_text('---\nphase: complete\ntitle: Synthetic Interrupted Mirror\nprogress: 1/1\n---\n')
        page=root/'ISA.html';page.write_text('Synthetic prior mirror')
        os.utime(page,(1,1))
        marker=root/'rename-ready';preload=root/'rename-delay.cjs'
        preload.write_text('// ABOUTME: Pauses the actual native mirror rename at publication.\n'
            '// ABOUTME: Preserves real rendering and the prior complete page for a kill control.\n'
            "const fs=require('node:fs');const rename=fs.renameSync;fs.renameSync=function(source,target){if(String(target)===process.env.LIFEOS_PAGE_TARGET){fs.writeFileSync(process.env.LIFEOS_RENAME_MARKER,'ready');Atomics.wait(new Int32Array(new SharedArrayBuffer(4)),0,0,30000);}return rename.call(this,source,target);};\n")
        environment.update(LIFEOS_PAGE_TARGET=str(page),LIFEOS_RENAME_MARKER=str(marker))
        process=subprocess.Popen([shutil.which('bun'),'--preload',str(preload),str(Path(SOURCE)/'LIFEOS/TOOLS/ISARender.ts'),str(isa),'--no-refresh'],
            env=environment,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        try:
            deadline=time.monotonic()+8
            while not marker.exists() and process.poll() is None and time.monotonic()<deadline:time.sleep(.02)
            self.assertTrue(marker.exists(),'The actual native page rename was not reached')
        finally:
            if process.poll() is None:process.kill()
            stdout,stderr=process.communicate(timeout=5)
        self.assertEqual(process.returncode,-9,(stdout,stderr))
        self.assertEqual(page.read_text(),'Synthetic prior mirror')
