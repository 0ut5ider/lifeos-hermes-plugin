# ABOUTME: Captures child adapter requests across admission, revocation, and profile changes.
# ABOUTME: Uses only temporary profiles, synthetic memory, and a localhost HTTP recorder.
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
import json,os,subprocess,sys,threading,shutil
sys.path.insert(0,str(Path.cwd()));sys.path.insert(0,str(Path.cwd()/'tests'))
from test_memory_runtime import MemoryRuntimeTests
from lifeos_hook_bridge.memory_service import MemoryConfiguration
from lifeos_hook_bridge.memory_context import route_identity
ROOT=Path.cwd(); PROGRAM=ROOT/'lifeos_hook_bridge/bin/claude_direct.py'
f=MemoryRuntimeTests();f.setUp()
requests=[]
class Gateway(BaseHTTPRequestHandler):
    def do_POST(self):
        body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        requests.append({'path':self.path,'body':body})
        if self.path=='/api/show':
            self.send_response(404);self.end_headers();return
        answer={'type':'message','content':[{'type':'text','text':'CHILD-OK'}],'id':'synthetic-response','object':'chat.completion','model':body.get('model'),
                'choices':[{'index':0,'message':{'role':'assistant','content':'CHILD-OK'},'finish_reason':'stop'}],
                'usage':{'prompt_tokens':3,'completion_tokens':1,'total_tokens':4}}
        encoded=json.dumps(answer).encode()
        if body.get('stream'):
            chunk={'id':'synthetic-response','object':'chat.completion.chunk','model':body['model'],'choices':[{'index':0,'delta':{'content':'CHILD-OK'},'finish_reason':'stop'}]}
            encoded=('data: '+json.dumps(chunk)+'\n\ndata: [DONE]\n\n').encode()
        self.send_response(200);self.send_header('Content-Type','text/event-stream' if body.get('stream') else 'application/json');self.send_header('Content-Length',str(len(encoded)));self.end_headers();self.wfile.write(encoded)
    def log_message(self,*_):pass
server=ThreadingHTTPServer(('127.0.0.1',0),Gateway)
threading.Thread(target=server.serve_forever,daemon=True).start()
base=f'http://127.0.0.1:{server.server_port}'
try:
    f.configuration['destinations']['chat-a:200']['model_routes'] += [route_identity('lifeos-local-gateway','child-model',base,'anthropic'),route_identity('custom','child-model',base+'/v1','chat_completions')]
    MemoryConfiguration(f.path).save(f.configuration)
    f.admit()
    env={k:v for k,v in os.environ.items() if not any(s in k for s in ('LIFEOS','HERMES','ANTHROPIC','OPENAI'))}
    env.update(HOME=str(f.fixture.home),ANTHROPIC_BASE_URL=base,ANTHROPIC_AUTH_TOKEN='synthetic-token',LIFEOS_CHILD_PROVIDER='')
    f.runtime.bind_environment(env)
    command=[sys.executable,str(PROGRAM),'--print','--model','child-model','--output-format','json','--system-prompt','Synthetic private child marker']
    def run(name,environment,cmd=command):
        count=len(requests)
        proc=subprocess.run(cmd,input='Synthetic child request',capture_output=True,text=True,env=environment,timeout=25)
        result={'case':name,'exit_code':proc.returncode,'stdout':proc.stdout,'stderr':proc.stderr,'new_requests':requests[count:]}
        print(json.dumps(result,sort_keys=True),flush=True)
    run('raw_approved',env)
    missing=dict(env);missing.pop('LIFEOS_MEMORY_CONTEXT',None)
    run('raw_missing_context_enabled',missing)
    mismatch=dict(env,LIFEOS_MEMORY_CONFIGURATION=str(f.home/'other/memory.json'))
    run('raw_configuration_profile_mismatch',mismatch)
    f.configuration['ownership_enabled']=False;MemoryConfiguration(f.path).save(f.configuration)
    run('raw_disabled_original_inherited_context',env)
    from lifeos_hook_bridge.memory_runtime import MemoryAdmissionError
    def denied(name, action):
        before=len(requests)
        try: action()
        except MemoryAdmissionError as error:
            assert len(requests)==before
            print(json.dumps({'case':name,'denied':True,'error':str(error),'new_requests':requests[before:]}),flush=True)
        else: raise AssertionError(name+' unexpectedly accepted')
    denied('disabled_readmission',lambda:f.runtime.admit(f.metadata(),**f.route,is_first_turn=False))
    rebound=dict(env)
    denied('disabled_environment_rebind',lambda:f.runtime.bind_environment(rebound,session_id='session'))
    assert rebound['LIFEOS_MEMORY_SESSION']=='session'
    missing_disabled=dict(env);missing_disabled.pop('LIFEOS_MEMORY_CONTEXT')
    run('raw_disabled_sealed_session_only',missing_disabled)
    f.path.unlink()
    denied('deleted_readmission',lambda:f.runtime.admit(f.metadata(),**f.route,is_first_turn=False))
    denied('deleted_environment_rebind',lambda:f.runtime.bind_environment(dict(env),session_id='session'))
    run('raw_deleted_original_inherited_context',env)
    run('raw_deleted_sealed_session_only',missing_disabled)
    f.runtime.clear()
    denied('deleted_recorded_session_readmission_without_bound_context',lambda:f.runtime.admit(f.metadata(),**f.route,is_first_turn=False))
    f.runtime.admit(f.metadata(session='fresh-inactive'),**f.route,is_first_turn=True)
    fresh={k:v for k,v in env.items() if not k.startswith('LIFEOS_MEMORY_')}
    f.runtime.bind_environment(fresh,session_id='fresh-inactive')
    fresh_command=command[:-1]+['Synthetic public fresh conversation']
    run('fresh_inactive_raw_child',fresh,fresh_command)
    MemoryConfiguration(f.path).save(dict(f.configuration,ownership_enabled=True))
    plugin=f.home/'plugins/lifeos-hook-bridge';plugin.parent.mkdir(parents=True,exist_ok=True)
    shutil.copytree(ROOT/'lifeos_hook_bridge',plugin,ignore=shutil.ignore_patterns('__pycache__'))
    (f.home/'config.yaml').write_text(f'model:\n  provider: custom\n  default: child-model\n  base_url: {base}/v1\n  api_key: synthetic-token\nplugins:\n  enabled: [lifeos-hook-bridge]\n')
    provider_env=dict(env,LIFEOS_CHILD_PROVIDER='custom',OPENAI_BASE_URL=base+'/v1',OPENAI_API_KEY='synthetic-token',LIFEOS_HOOK_SETTINGS=str(f.fixture.root/'settings.json'))
    script="import sys;sys.path.insert(0,"+repr(str(ROOT))+ ");sys.path.insert(0,'/home/outsider/.cache/lifeos-plugin-memory/source-gate-20260930-native/hermes');from lifeos_hook_bridge.bin.claude_direct import main;sys.exit(main())"
    provider_command=[sys.executable,'-c',script,*command[2:]]
    run('actual_hermes_provider_approved',provider_env,provider_command)
    config_path=f.home/'config.yaml'
    config_path.write_text(config_path.read_text().replace(base+'/v1',base+'/unapproved/v1'))
    run('actual_hermes_provider_unapproved_route',dict(provider_env,OPENAI_BASE_URL=base+'/unapproved/v1'),provider_command)
    config_path.write_text(config_path.read_text().replace(base+'/unapproved/v1',base+'/v1'))
    missing_provider=dict(provider_env);missing_provider.pop('LIFEOS_MEMORY_CONTEXT')
    run('actual_hermes_provider_missing_context',missing_provider,provider_command)
    saved=f.fixture.remember('Synthetic retained child fact','child-forget-source')
    f.fixture.memory.forget(__import__('test_memory_native').OWNER,saved['reference'],'child-forget')
    run('actual_hermes_provider_after_forget',provider_env,provider_command)
    executable=f.fixture.home/'.local/bin/claude';executable.parent.mkdir(parents=True)
    executable.write_text('#!/bin/sh\nprintf \'UNEXPECTED-NATIVE-FALLBACK\\n\'\n');executable.chmod(0o700)
    run('legacy_native_fallback_inherited_context',dict(env,LIFEOS_CHILD_INFERENCE_DIRECT='0',ANTHROPIC_MODEL='child-model'),[str(ROOT/'lifeos_hook_bridge/bin/claude'),*command[2:]])
finally:
    server.shutdown();server.server_close();f.runtime.clear();f.doCleanups()
