# ABOUTME: Measures managed prompt source admission and turn bookkeeping interruption.
# ABOUTME: Uses the real local memory service, native Bun programs, and synthetic context.
from dataclasses import asdict, replace
import json
import os
from pathlib import Path
import subprocess
import time
import unittest

import test_memory_delegation as delegation


class NativeManagedPromptTests(unittest.TestCase):
    def setUp(self):
        self.fixture=delegation.MemoryDelegationTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root=self.fixture.root
        self.environment={**os.environ,'HOME':str(self.fixture.fixture.home),
            'LIFEOS_DIR':str(self.root/'LIFEOS'),'BUN_CONFIG_NO_AUTO_INSTALL':'1',
            'LIFEOS_MEMORY_CONTEXT':json.dumps(asdict(self.fixture.context))}
        self.environment.pop('LIFEOS_MEMORY_INTERNAL',None)

    def call(self, environment):
        result=subprocess.run(['bun','--no-install',str(self.root/'hooks/DriftReminder.hook.ts')],
            input=json.dumps({'prompt':'Hello','session_id':'managed-drift'}),env=environment,
            text=True,capture_output=True,timeout=10)
        self.assertEqual((result.returncode,result.stderr),(0,''))
        return json.loads(result.stdout)['hookSpecificOutput']['additionalContext']

    def test_managed_drift_metrics_require_current_caller_and_destination(self):
        cache=self.root/'LIFEOS/MEMORY/STATE/last-response.txt'
        cache.parent.mkdir(parents=True,exist_ok=True)
        cache.write_text('Synthetic previous response without required structure')
        self.assertIn('no banner',self.call(self.environment))
        missing={k:v for k,v in self.environment.items() if k!='LIFEOS_MEMORY_CONTEXT'}
        self.assertNotIn('no banner',self.call(missing))
        changed=self.environment|{'LIFEOS_MEMORY_CONTEXT':json.dumps(asdict(replace(self.fixture.context,
            destination='unregistered-destination')))}
        self.assertNotIn('no banner',self.call(changed))
        self.fixture.configuration.update(lambda value:value['accounts'].pop('chat-a:100'))
        self.assertNotIn('no banner',self.call(self.environment))

    def test_interrupted_turn_injection_preserves_the_prior_bookkeeping(self):
        target=self.root/'LIFEOS/MEMORY/STATE/memory-inject/native-turn.json'
        target.parent.mkdir(parents=True,exist_ok=True)
        previous=b'{"lastHash":"synthetic-prior","turnsSinceInject":4}\n'
        target.write_bytes(previous)
        marker=self.root/'publication-ready'
        preload=self.root/'publication-delay.cjs'
        preload.write_text('''// ABOUTME: Pauses native turn bookkeeping publication for a kill control.
// ABOUTME: Measures actual state writes and atomic rename without changing memory responses.
const fs=require('node:fs'); const write=fs.writeFileSync; const rename=fs.renameSync;
function pause(){write(process.env.LIFEOS_PUBLICATION_MARKER,'ready');Atomics.wait(new Int32Array(new SharedArrayBuffer(4)),0,0,30000);}
fs.writeFileSync=function(path,...args){if(String(path)===process.env.LIFEOS_PUBLICATION_TARGET){const fd=fs.openSync(path,'w');fs.closeSync(fd);pause();}return write.call(this,path,...args);};
fs.renameSync=function(source,target){if(String(target)===process.env.LIFEOS_PUBLICATION_TARGET)pause();return rename.call(this,source,target);};
''')
        environment=self.environment|{'LIFEOS_PUBLICATION_TARGET':str(target),'LIFEOS_PUBLICATION_MARKER':str(marker)}
        process=subprocess.Popen(['bun','--preload',str(preload),str(self.root/'hooks/MemoryTurnStart.hook.ts')],
            env=environment,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        process.stdin.write(json.dumps({'session_id':'native-turn','prompt':'Hello'}))
        process.stdin.close();process.stdin=None
        try:
            deadline=time.monotonic()+10
            while not marker.exists() and process.poll() is None and time.monotonic()<deadline:time.sleep(.02)
        finally:
            if process.poll() is None:process.kill()
            output,errors=process.communicate(timeout=5)
        self.assertTrue(marker.exists(),(output,errors))
        self.assertEqual(process.returncode,-9,(output,errors))
        self.assertEqual(target.read_bytes(),previous)

    def test_feedback_preview_requires_current_source_admission(self):
        cache=self.root/'LIFEOS/MEMORY/STATE/last-response.txt'
        cache.parent.mkdir(parents=True,exist_ok=True);cache.write_text('SYNTHETIC_PRIOR_PRIVATE_RESPONSE')
        log=self.root/'LIFEOS/MEMORY/LEARNING/SIGNALS/ratings.jsonl'
        cases=[(self.environment,True),({k:v for k,v in self.environment.items() if k!='LIFEOS_MEMORY_CONTEXT'},False),
            (self.environment|{'LIFEOS_MEMORY_CONTEXT':json.dumps(asdict(replace(self.fixture.context,destination='unregistered')))},False)]
        for environment,admitted in cases:
            result=subprocess.run(['bun','--no-install',str(self.root/'hooks/SatisfactionCapture.hook.ts')],
                input=json.dumps({'prompt':'9','session_id':'managed-feedback'}),env=environment,text=True,capture_output=True,timeout=15)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertIn('Wrote explicit rating 9',result.stderr)
            row=json.loads(log.read_text().splitlines()[-1])
            self.assertEqual('SYNTHETIC_PRIOR_PRIVATE_RESPONSE' in json.dumps(row),admitted)
        self.fixture.configuration.update(lambda value:value['accounts'].pop('chat-a:100'))
        result=subprocess.run(['bun','--no-install',str(self.root/'hooks/SatisfactionCapture.hook.ts')],
            input=json.dumps({'prompt':'9','session_id':'managed-feedback'}),env=self.environment,text=True,capture_output=True,timeout=15)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertNotIn('SYNTHETIC_PRIOR_PRIVATE_RESPONSE',log.read_text().splitlines()[-1])

    def test_actual_startup_and_resume_load_only_admitted_work(self):
        from datetime import datetime
        work=self.root/'LIFEOS/MEMORY/WORK'/(datetime.now().strftime('%Y%m%d-%H%M%S')+'_synthetic-managed')
        work.mkdir(parents=True)
        (work/'ISA.md').write_text('---\ntitle: SYNTHETIC_MANAGED_ACTIVE_WORK\nphase: climbing\nprogress: 0/1\n---\n')
        environment=self.environment|{'LIFEOS_NOTIFICATION_CHANNEL':'discord'}
        for source in ('startup','resume'):
            result=subprocess.run(['bun','--no-install',str(self.root/'hooks/LoadContext.hook.ts')],
                input=json.dumps({'source':source}),env=environment,text=True,capture_output=True,timeout=15)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertIn('SYNTHETIC_MANAGED_ACTIVE_WORK',result.stdout)
        for changed in ({k:v for k,v in environment.items() if k!='LIFEOS_MEMORY_CONTEXT'},
            environment|{'LIFEOS_MEMORY_CONTEXT':json.dumps(asdict(replace(self.fixture.context,destination='unregistered')))}):
            result=subprocess.run(['bun','--no-install',str(self.root/'hooks/LoadContext.hook.ts')],
                input='{}',env=changed,text=True,capture_output=True,timeout=15)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertNotIn('SYNTHETIC_MANAGED_ACTIVE_WORK',result.stdout)
