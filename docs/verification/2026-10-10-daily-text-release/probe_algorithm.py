# ABOUTME: Captures actual concurrent summary responses before changing the failing path.
# ABOUTME: Retains synthetic fixture state, child diagnostics, and inference requests on disk.
import json
import importlib
import os
from pathlib import Path
import select
import shutil
import subprocess
import sys
import unittest
import httpx
import test_memory_algorithm_jobs as subject

here=Path(__file__).resolve().parent
responses=[]
original=httpx.get
def observed(*args,**kwargs):
    result=original(*args,**kwargs)
    if '/api/algorithm-tab' in str(args[0]):
        responses.append({'status':result.status_code,'body':result.text})
    return result
httpx.get=observed

class Probe(subject.MemoryAlgorithmJobRelayTests):
    def launch_lifetime_process(self,environment,**keywords):
        self.child_log=self.fixture.home/'algorithm-child-output.jsonl'
        original=subprocess.Popen
        def instrument(command,*args,**kwargs):
            program=self.fixture.home/'conduit-lifetime.ts'
            if command==['bun','--no-install',str(program)]:
                text=program.read_text()
                module=self.root/'LIFEOS/PULSE/modules'/self.native_module
                helper=self.root/'LIFEOS/TOOLS/lib/MemoryAccess.ts'
                text=text.replace('import {handleRequest,stop} from '+json.dumps(str(module))+';',
                    'const {handleRequest,stop}=await import('+json.dumps(str(module))+');')
                text=text.replace('import {memoryHTTPServerOptions} from '+json.dumps(str(helper))+';',
                    'const {memoryHTTPServerOptions}=await import('+json.dumps(str(helper))+');')
                prefix='import {appendFileSync} from "node:fs";const cp=require("node:child_process");const oldSpawn=cp.spawn;'
                prefix+='const capture=(row)=>appendFileSync('+json.dumps(str(self.child_log))+',JSON.stringify(row)+"\\n");'
                prefix+='cp.spawn=(...args)=>{const begin=performance.now();let view=null;capture({command:args.slice(0,2),home:args[2]?.env?.HOME,pythonpath:args[2]?.env?.PYTHONPATH});const child=oldSpawn(...args);'
                prefix+='if(child.stdin){const oldEnd=child.stdin.end;child.stdin.end=function(chunk,...rest){try{const wire=JSON.parse(chunk.toString());view=wire.arguments?.view;capture({view})}catch{}return oldEnd.call(this,chunk,...rest)}};child.on("close",code=>capture({view,code,elapsed_seconds:(performance.now()-begin)/1000}));'
                prefix+='child.stdout?.on("data",chunk=>capture({stream:"stdout",text:chunk.toString()}));child.stderr?.on("data",chunk=>capture({stream:"stderr",text:chunk.toString()}));return child};'
                program.write_text(prefix+text)
            return original(command,*args,**kwargs)
        subprocess.Popen=instrument
        try:super().launch_lifetime_process(environment,**keywords)
        finally:subprocess.Popen=original
    def setUp(self):
        super().setUp()
        self.admissions=[]
        self.fixture.login()
        self.fixture.client.post('/api/plugins/lifeos-hook-bridge/memory/algorithm_job')
        preferences=importlib.import_module('lifeos_memory_settings.memory_preferences').MemoryPreferences
        original=preferences.algorithm_job_response
        def observed_job(owner,**keywords):
            try:
                result=original(owner,**keywords)
                self.admissions.append({'result':result})
                return result
            except BaseException as error:
                self.admissions.append({'error':str(error),'type':type(error).__name__})
                raise
        preferences.algorithm_job_response=observed_job
        self.addCleanup(setattr,preferences,'algorithm_job_response',original)
    def held_inference(self):
        result=super().held_inference()
        self.requests=result[2]
        self.model_environment=result[0]
        self.received=result[1]
        return result
    def lifetime(self,**keywords):
        try:
            super().lifetime(**keywords)
        finally:
            direct=None
            if not self.requests and not self.child_log.exists():
                revision=subject.MemoryPolicy(self.fixture.configuration.load()).revision
                env=dict(os.environ,HOME=str(self.fixture.home),HERMES_HOME=str(self.fixture.profile),
                    LIFEOS_HOOK_MODEL_ENV=str(self.model_environment),
                    PYTHONPATH=os.environ['LIFEOS_HERMES_SOURCE']+os.pathsep+os.environ.get('PYTHONPATH',''),
                    BUN_CONFIG_NO_AUTO_INSTALL='1')
                command=[sys.executable,'-m','hermes_cli.main','lifeos-job','algorithm-summaries',
                         '--configuration-revision',revision]
                child=subprocess.Popen(command,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
                try:
                    stdout,stderr=child.communicate(timeout=40)
                except subprocess.TimeoutExpired:
                    child.terminate()
                    stdout,stderr=child.communicate(timeout=10)
                direct={'command':command,'exit_code':child.returncode,'stdout':stdout,'stderr':stderr,
                        'inference_reached':self.received.is_set()}
            diagnostics=[]
            stream=self.process.stderr
            while select.select([stream],[],[],0)[0]:
                data=os.read(stream.fileno(),65536)
                if not data:break
                diagnostics.append(data.decode(errors='replace'))
            artifacts={}
            for relative in ('LIFEOS/USER/MEMORY/STATE/algorithm-tab-summary.json',
                             'LIFEOS/MEMORY/STATE/algorithm-tab-summary.json',
                             'LIFEOS/MEMORY/STATE/work-events.jsonl'):
                path=self.root/relative
                if path.exists():artifacts[relative]=path.read_text()
            (here/'algorithm-probe-data.json').write_text(json.dumps({'responses':responses,
              'requests':self.requests,'admissions':self.admissions,'direct_job':direct,
              'stderr':diagnostics,'artifacts':artifacts,
              'native_child_output':self.child_log.read_text() if self.child_log.exists() else None},indent=2)+'\n')

suite=unittest.TestSuite([Probe('test_simultaneous_stale_reads_start_one_job_and_module_stop_ends_children')])
result=unittest.TextTestRunner(verbosity=2).run(suite)
(here/'algorithm-probe.done').write_text(str(int(not result.wasSuccessful()))+'\n')
sys.exit(not result.wasSuccessful())
