# ABOUTME: Measures native completion policy state, boundaries, and interrupted publication.
# ABOUTME: Uses real Bun programs, bridge dispatch, and filesystem operations in disposable homes.
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
import unittest

from lifeos_hook_bridge.bridge import HookBridge
import test_native_lifecycle_branches as lifecycle

SOURCE = os.environ.get('LIFEOS_GUARD_SOURCE')


@unittest.skipUnless(SOURCE and shutil.which('bun'), 'Prepared native completion programs and Bun are required')
class NativeCompletionPolicyTests(unittest.TestCase):
    def fixture(self):
        fixture = lifecycle.NativeLifecycleBranchTests()
        home, root, environment = fixture.fixture()
        self.addCleanup(fixture.doCleanups)
        return home, root, environment

    def run_hook(self, root, environment, name, payload, preload=None):
        command = ['bun']
        if preload:
            command += ['--preload', str(preload)]
        command += [str(Path(SOURCE)/'hooks'/(name+'.hook.ts'))]
        return subprocess.run(command, input=json.dumps(payload), env=environment, cwd=root,
                              text=True, capture_output=True, timeout=15)

    def interruption(self, name, relative, payload, previous, *, driver=None):
        _, root, environment = self.fixture()
        target = root/'LIFEOS'/relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(previous)
        marker = root/'publication-ready'
        preload = root/'publication-delay.cjs'
        preload.write_text('''// ABOUTME: Pauses a native destination write or atomic rename for an interruption control.
// ABOUTME: Retains actual state computation and prior destination bytes until publication.
const fs = require('node:fs');
const write = fs.writeFileSync;
const rename = fs.renameSync;
function pause() {
  write.call(fs, process.env.LIFEOS_PUBLICATION_MARKER, 'ready');
  Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 30000);
}
fs.writeFileSync = function(path, ...args) {
  if (String(path) === process.env.LIFEOS_PUBLICATION_TARGET) {
    const fd = fs.openSync(path, 'w');
    fs.closeSync(fd);
    pause();
  }
  return write.call(this, path, ...args);
};
fs.renameSync = function(source, target) {
  if (String(target) === process.env.LIFEOS_PUBLICATION_TARGET) pause();
  return rename.call(this, source, target);
};
''')
        environment.update(LIFEOS_PUBLICATION_TARGET=str(target), LIFEOS_PUBLICATION_MARKER=str(marker))
        if driver:
            script = root/'driver.ts'
            script.write_text(driver(root))
            command = ['bun','--preload',str(preload),str(script)]
        else:
            command = ['bun','--preload',str(preload),str(Path(SOURCE)/'hooks'/(name+'.hook.ts'))]
        process = subprocess.Popen(command, env=environment, cwd=root, stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        process.stdin.write(json.dumps(payload)); process.stdin.close(); process.stdin = None
        try:
            deadline = time.monotonic()+8
            while not marker.exists() and process.poll() is None and time.monotonic()<deadline:
                time.sleep(.02)
            self.assertTrue(marker.exists(), 'Actual native publication was not reached')
        finally:
            if process.poll() is None:
                process.kill()
            stdout, stderr = process.communicate(timeout=5)
        self.assertEqual(process.returncode,-9,(stdout,stderr))
        self.assertEqual(target.read_bytes(),previous)

    def test_interrupted_response_publication_preserves_prior_bytes(self):
        self.interruption('LastResponseCache','MEMORY/STATE/last-response.txt',
            {'hook_event_name':'Stop','session_id':'cache','transcript_path':'/nonexistent/synthetic-transcript','last_assistant_message':'Completed generation'},
            b'PREVIOUS_COMPLETED_RESPONSE\n')

    def test_interrupted_algorithm_publication_preserves_prior_state(self):
        self.interruption('AlgorithmNudge','MEMORY/STATE/isa-nudge/algorithm.json',
            {'hook_event_name':'UserPromptSubmit','session_id':'algorithm','prompt':'go deep'},
            b'{"toolCallsTotal":4,"lastNudgeAt":{},"lateISAFired":false}\n')

    def test_interrupted_spend_publication_preserves_prior_state(self):
        self.interruption('SpendAuditor','MEMORY/STATE/spend-audit-state.json',
            {'hook_event_name':'Stop','session_id':'spend','transcript_path':'/nonexistent/synthetic-transcript'},
            json.dumps({'prior':int(time.time()*1000)}).encode())

    def test_interrupted_integrity_publication_preserves_prior_state(self):
        def driver(root):
            transcript = root/'transcript.jsonl'
            transcript.write_text(json.dumps({'type':'assistant','message':{'content':[{
                'type':'tool_use','id':'write','name':'Write','input':{
                    'file_path':str(root/'hooks/NewFixture.hook.ts'),'content':'// Synthetic change'}}]}})+'\n')
            module = str(Path(SOURCE)/'hooks/handlers/SystemIntegrity.ts')
            return 'import {handleSystemIntegrity} from '+json.dumps(module)+';\nawait handleSystemIntegrity({} as any,'+json.dumps({
                'session_id':'integrity','hook_event_name':'SessionEnd','transcript_path':str(transcript)})+');\n'
        self.interruption('IntegrityCheck','MEMORY/STATE/integrity-state.json',{},
            b'{"last_run":"2000-01-01T00:00:00Z","last_changes_hash":"prior","cooldown_until":"2000-01-01T00:00:00Z"}\n',driver=driver)

    def test_concurrent_review_cadence_keeps_one_global_fire_and_separate_session_counts(self):
        home, root, environment = self.fixture()
        # An absent real reviewer exercises the native unavailable-tool branch.
        (root/'LIFEOS/TOOLS').unlink()
        configuration = root/'LIFEOS/USER/CONFIG/memory-review.json'
        configuration.parent.mkdir(parents=True)
        configuration.write_text(json.dumps({'turn_threshold':1,'min_minutes_between':30}))
        selected = {'type':'command','command':'bun '+str(root/'hooks/MemoryReviewFire.hook.ts')}
        settings = root/'settings.json'
        settings.write_text(json.dumps({'hooks':{'Stop':[{'hooks':[selected]}]}}))
        preload = root/'review-publication-delay.cjs'
        preload.write_text('''// ABOUTME: Widens actual review global-state publication for a race control.
// ABOUTME: Preserves all native cadence decisions and state values.
const fs=require('node:fs'); const write=fs.writeFileSync;
fs.writeFileSync=function(path,...args) {
 const result=write.call(this,path,...args);
 if(String(path).endsWith('/review-state.json.tmp')) Atomics.wait(new Int32Array(new SharedArrayBuffer(4)),0,0,100);
 return result;
};
''')
        binaries = home/'bin'; binaries.mkdir()
        launcher = binaries/'bun'
        import shlex
        launcher.write_text('#!/bin/sh\nexec '+shlex.quote(shutil.which('bun'))+' --preload '+shlex.quote(str(preload))+' "$@"\n')
        launcher.chmod(0o755)
        environment['PATH']=str(binaries)+os.pathsep+environment['PATH']
        bridges = [HookBridge(settings,root,lifeos_home=home) for _ in range(8)]
        for bridge in bridges:
            bridge.environment.update(environment); self.addCleanup(bridge.close)
        with ThreadPoolExecutor(max_workers=8) as pool:
            results=list(pool.map(lambda i:bridges[i]._run('Stop',{'hook_event_name':'Stop','session_id':'review-'+str(i)}),range(8)))
        self.assertEqual([(r[0].returncode,r[0].stderr) for results0 in results for r in results0],[(0,'')]*8)
        rows=[json.loads(line) for line in (root/'LIFEOS/MEMORY/OBSERVABILITY/reviewer-fires.jsonl').read_text().splitlines()]
        self.assertEqual(len(rows),1,rows)
        self.assertEqual((rows[0]['spawned'],rows[0]['reason']),(False,'reviewer-not-found'))
        counts=[json.loads(p.read_text())['turn_count_since_last_review'] for p in (root/'LIFEOS/MEMORY/STATE/memory-review').glob('*.json')]
        self.assertEqual(sorted(counts),[0]+[1]*7)

    def test_drift_exact_age_boundary_code_exclusion_and_malformed_state(self):
        _, root, environment = self.fixture()
        state=root/'LIFEOS/MEMORY/STATE'
        cache=state/'last-response.txt'; cache.write_text('```\n'+'\n'.join(['code']*50)+'\n```\nPlain text')
        preload=root/'fixed-clock.cjs'
        preload.write_text('// ABOUTME: Fixes the policy clock for exact native age boundaries.\n'
                           '// ABOUTME: Leaves file timestamps and format policy unchanged.\nDate.now=()=>Number(process.env.LIFEOS_POLICY_NOW);\n')
        os.utime(cache,(1800000000,1800000000))
        for age in (1800000-1,1800000,1800000+1):
            with self.subTest(age=age):
                result=self.run_hook(root,environment|{'LIFEOS_POLICY_NOW':str(1800000000000+age)},'DriftReminder',
                    {'prompt':'Hello'},preload)
                self.assertEqual((result.returncode,result.stderr),(0,''))
                context=json.loads(result.stdout)['hookSpecificOutput']['additionalContext']
                self.assertEqual('no banner' in context,age<=1800000)
                self.assertNotIn('51 lines',context)
                self.assertIn('max 15 prose lines',context)
        (state/'drift-reminder.json').write_text('{invalid')
        result=self.run_hook(root,environment,'DriftReminder',{'prompt':'Give a detailed report'})
        self.assertEqual((result.returncode,result.stderr),(0,''))
        self.assertIn('line cap lifted',result.stdout)
        self.assertEqual(json.loads((state/'drift-reminder.json').read_text())['turn_count'],1)

    def test_spend_capability_floor_and_missing_transcript_use_native_policy(self):
        _, root, environment = self.fixture()
        module=str(Path(SOURCE)/'hooks/SpendAuditor.hook.ts')
        script=root/'spend-controls.ts'
        script.write_text('import {decideTrigger,runAudit,collectCaps} from '+json.dumps(module)+';\n'
            'const caps={skills:[],agents:[],tool_calls:5};\n'
            'console.log(JSON.stringify([199,200,201].map(lastPromptLen=>decideTrigger({sessionId:"threshold",caps,lastPromptLen,now:Date.now()}))));\n'
            'console.log(JSON.stringify(decideTrigger({sessionId:"threshold",caps:{...caps,skills:["fixture"]},lastPromptLen:201,now:Date.now()})));\n'
            'await runAudit("/nonexistent/synthetic-transcript","missing");\n')
        result=subprocess.run(['bun',str(script)],env=environment,text=True,capture_output=True,timeout=10)
        self.assertEqual((result.returncode,result.stderr),(0,''))
        rows=result.stdout.splitlines()
        self.assertEqual(json.loads(rows[0]),[None,'zero-capability-sweep','zero-capability-sweep'])
        self.assertIsNone(json.loads(rows[1]))
        audit=json.loads((root/'LIFEOS/MEMORY/OBSERVABILITY/spend-audit.jsonl').read_text())
        self.assertEqual((audit['audited'],audit['reason']),(False,'transcript-missing'))

    def test_algorithm_initial_repeat_missing_malformed_and_late_isa_state(self):
        _, root, environment = self.fixture()
        state=root/'LIFEOS/MEMORY/STATE/isa-nudge/algorithm.json'
        first=self.run_hook(root,environment,'AlgorithmNudge',{
            'hook_event_name':'UserPromptSubmit','session_id':'algorithm','prompt':'go deep'})
        self.assertEqual(first.returncode,0)
        self.assertIn('He directed depth',first.stdout)
        repeated=self.run_hook(root,environment,'AlgorithmNudge',{
            'hook_event_name':'UserPromptSubmit','session_id':'algorithm','prompt':'go deep'})
        self.assertEqual((repeated.returncode,repeated.stdout,repeated.stderr),(0,'',''))
        state.write_text('{invalid')
        recovered=self.run_hook(root,environment,'AlgorithmNudge',{
            'hook_event_name':'UserPromptSubmit','session_id':'algorithm','prompt':'go deep'})
        self.assertEqual(recovered.returncode,0)
        self.assertIn('He directed depth',recovered.stdout)
        current=json.loads(state.read_text())
        current.update(toolCallsTotal=24,lateISAFired=False,lastNudgeAt={})
        state.write_text(json.dumps(current))
        late=self.run_hook(root,environment,'AlgorithmNudge',{
            'hook_event_name':'PostToolUse','session_id':'algorithm','tool_name':'Read','tool_input':{'file_path':'/synthetic/read'}})
        self.assertEqual(late.returncode,0)
        self.assertIn('25+ tool calls and no run registered',late.stdout)
        again=self.run_hook(root,environment,'AlgorithmNudge',{
            'hook_event_name':'PostToolUse','session_id':'algorithm','tool_name':'Read','tool_input':{'file_path':'/synthetic/read'}})
        self.assertEqual((again.returncode,again.stdout,again.stderr),(0,'',''))
        self.assertEqual(json.loads(state.read_text())['toolCallsTotal'],26)

    def test_integrity_missing_malformed_changed_duplicate_and_unchanged_state(self):
        _, root, environment = self.fixture()
        # Missing maintenance intentionally avoids any model call in this marker control.
        (root/'LIFEOS/TOOLS').unlink()
        transcript=root/'transcript.jsonl'
        transcript.write_text(json.dumps({'type':'assistant','message':{'content':[{
            'type':'tool_use','id':'change','name':'Write','input':{
                'file_path':str(root/'hooks/NewFixture.hook.ts'),'content':'// Synthetic change'}}]}})+'\n')
        payload={'hook_event_name':'SessionEnd','session_id':'integrity','transcript_path':str(transcript)}
        marker=root/'LIFEOS/MEMORY/STATE/integrity-state.json'
        for initial in (None,'{invalid'):
            with self.subTest(initial=initial):
                marker.unlink(missing_ok=True)
                if initial:marker.write_text(initial)
                result=self.run_hook(root,environment,'IntegrityCheck',payload)
                self.assertEqual(result.returncode,0,result.stderr)
                self.assertIn('Significant changes detected',result.stderr)
                self.assertIn('IntegrityMaintenance.ts not found',result.stderr)
                self.assertTrue(json.loads(marker.read_text())['last_changes_hash'])
        prior=marker.read_bytes()
        cooldown=self.run_hook(root,environment,'IntegrityCheck',payload)
        self.assertIn('In cooldown',cooldown.stderr)
        self.assertEqual(marker.read_bytes(),prior)
        current=json.loads(prior);current['cooldown_until']='2000-01-01T00:00:00Z';marker.write_text(json.dumps(current))
        prior=marker.read_bytes()
        duplicate=self.run_hook(root,environment,'IntegrityCheck',payload)
        self.assertIn('Duplicate change set',duplicate.stderr)
        self.assertEqual(marker.read_bytes(),prior)
        transcript.write_text('')
        unchanged=self.run_hook(root,environment,'IntegrityCheck',payload)
        self.assertIn('No system changes detected',unchanged.stderr)
        self.assertEqual(marker.read_bytes(),prior)

    def test_drift_malformed_input_and_publication_failure_preserve_failure_policy(self):
        _, root, environment = self.fixture()
        result=subprocess.run(['bun',str(Path(SOURCE)/'hooks/DriftReminder.hook.ts')],
            input='{invalid',env=environment,text=True,capture_output=True,timeout=10)
        self.assertEqual((result.returncode,result.stderr),(0,''))
        self.assertIn('max 15 prose lines',result.stdout)
        target=root/'LIFEOS/MEMORY/STATE/drift-reminder.json'
        target.unlink();target.mkdir()
        protected=target/'protected.txt';protected.write_text('Synthetic prior state')
        failed=self.run_hook(root,environment,'DriftReminder',{'prompt':'Hello'})
        self.assertEqual((failed.returncode,failed.stdout),(0,''))
        self.assertIn('DriftReminder error:',failed.stderr)
        self.assertEqual(protected.read_text(),'Synthetic prior state')

    def test_absent_and_malformed_model_carriers_do_not_invent_a_tier(self):
        _,root,environment=self.fixture()
        (root/'settings.json').write_text('{"model":"fable"}')
        transcript=root/'model-transcript.jsonl'
        transcript.write_text(json.dumps({'type':'assistant','message':{'model':'actual-private-fixture',
            'content':'Synthetic completed answer'}})+'\n')
        for carrier in ('null','{invalid',json.dumps({'model':'different-model','provider':'custom',
            'effort':'low','tier':'haiku','pin':'fable'}),json.dumps({'model':'actual-private-fixture',
            'provider':'custom','effort':{},'tier':'haiku','pin':'fable'})):
            with self.subTest(carrier=carrier):
                result=self.run_hook(root,environment|{'LIFEOS_CARRIER_OBSERVATION':carrier},'ModelRungGuard',
                    {'hook_event_name':'UserPromptSubmit','session_id':'rung','transcript_path':str(transcript)})
                self.assertEqual((result.returncode,result.stdout,result.stderr),(0,'',''))
                log=root/'LIFEOS/MEMORY/OBSERVABILITY/model-rung.jsonl'
                row=json.loads(log.read_text().splitlines()[-1])
                self.assertIsNone(row['live'])
                self.assertIsNone(row['reasoning_effort'])

    def test_concurrent_spend_markers_and_feedback_pulses_keep_all_sessions(self):
        import shlex
        for hook,event in (('SpendAuditor','Stop'),('SatisfactionCapture','UserPromptSubmit')):
            with self.subTest(hook=hook):
                home,root,environment=self.fixture()
                target=root/'LIFEOS/MEMORY/STATE'/('spend-audit-state.json' if hook=='SpendAuditor' else 'work.json')
                target.write_text('{}' if hook=='SpendAuditor' else '{"sessions":{}}')
                preload=root/'state-read-delay.cjs'
                preload.write_text('// ABOUTME: Widens actual shared state reads for parallel session controls.\n'
                    '// ABOUTME: Retains native state decisions and real writes.\n'
                    "const fs=require('node:fs');const read=fs.readFileSync;fs.readFileSync=function(path,...args){const result=read.call(this,path,...args);if(String(path)===process.env.LIFEOS_STATE_READ_TARGET)Atomics.wait(new Int32Array(new SharedArrayBuffer(4)),0,0,100);return result;};\n")
                binaries=home/'bin';binaries.mkdir()
                launcher=binaries/'bun';launcher.write_text('#!/bin/sh\nexec '+shlex.quote(shutil.which('bun'))+' --preload '+shlex.quote(str(preload))+' "$@"\n');launcher.chmod(0o755)
                environment.update(PATH=str(binaries)+os.pathsep+environment['PATH'],LIFEOS_STATE_READ_TARGET=str(target))
                settings=root/'settings.json';settings.write_text(json.dumps({'hooks':{event:[{'hooks':[{'type':'command','command':'bun '+str(root/'hooks'/(hook+'.hook.ts'))}]}]}}))
                bridges=[HookBridge(settings,root,lifeos_home=home) for _ in range(8)]
                for bridge in bridges:bridge.environment.update(environment);self.addCleanup(bridge.close)
                def dispatch(index):
                    if event=='Stop':return bridges[index]._run(event,{'hook_event_name':event,'session_id':'parallel-'+str(index),'transcript_path':'/nonexistent/synthetic-transcript'})
                    return bridges[index].pre_llm_call('9',session_id='parallel-'+str(index))
                with ThreadPoolExecutor(max_workers=8) as pool:results=list(pool.map(dispatch,range(8)))
                current=json.loads(target.read_text())
                if hook=='SpendAuditor':self.assertEqual(set(current),{'parallel-'+str(i) for i in range(8)},results)
                else:
                    self.assertEqual(len(current['sessions']['__pulse_strip']['ratings']),8,results)
                    ratings=root/'LIFEOS/MEMORY/LEARNING/SIGNALS/ratings.jsonl'
                    self.assertEqual(len(ratings.read_text().splitlines()),8)

    def test_spend_malformed_transcript_and_repeated_stop_keep_one_actual_audit(self):
        _,root,environment=self.fixture()
        transcript=root/'malformed-transcript.jsonl';transcript.write_text('{invalid\n')
        state=root/'LIFEOS/MEMORY/STATE/spend-audit-state.json';state.write_text('{invalid')
        payload={'hook_event_name':'Stop','session_id':'repeat-audit','transcript_path':str(transcript)}
        first=self.run_hook(root,environment,'SpendAuditor',payload)
        self.assertEqual((first.returncode,first.stdout,first.stderr),(0,'',''))
        marked=json.loads(state.read_text());self.assertIn('repeat-audit',marked)
        log=root/'LIFEOS/MEMORY/OBSERVABILITY/spend-audit.jsonl'
        deadline=time.monotonic()+5
        while not log.exists() and time.monotonic()<deadline:time.sleep(.02)
        self.assertTrue(log.exists())
        rows=[json.loads(line) for line in log.read_text().splitlines()]
        self.assertEqual(len(rows),1,rows)
        self.assertEqual((rows[0]['audited'],rows[0]['reason']),(False,'not-eligible'))
        for _ in range(3):
            result=self.run_hook(root,environment,'SpendAuditor',payload)
            self.assertEqual((result.returncode,result.stdout,result.stderr),(0,'',''))
        self.assertEqual(json.loads(state.read_text()),marked)
        self.assertEqual([json.loads(line) for line in log.read_text().splitlines()],rows)
