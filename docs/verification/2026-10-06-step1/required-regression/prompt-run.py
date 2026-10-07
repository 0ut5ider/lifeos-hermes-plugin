# ABOUTME: Executes the actual title-inference hook through the installed Hermes child adapter.
# ABOUTME: Retains real request hashes and source identity on the isolated development host.
import base64,hashlib,json,os,subprocess,threading
from pathlib import Path
from http.server import ThreadingHTTPServer
from paired_response_server import response_handler
from paired_evaluation_effects import configure_evaluation
base=Path('/var/tmp/lifeos-step1-20261006');root=base/'prompt-inference-final';root.mkdir(exist_ok=True)
config=json.loads((base/'evaluation-operations-final-configuration.json').read_text());spec=config['hermes']
server=ThreadingHTTPServer(('127.0.0.1',0),response_handler(config['model_environment']));server.observed=[]
threading.Thread(target=server.serve_forever,daemon=True).start()
endpoint=f'http://127.0.0.1:{server.server_port}'
home=root/'adapter-home';home.mkdir();profile=home/'.hermes';profile.mkdir()
(profile/'config.yaml').write_text(json.dumps({'model':{'provider':'custom','base_url':endpoint+'/v1','api_key':'PAIR_TITLE','default':'lifecycle-fixture','api_mode':'chat_completions'},'auxiliary':{'title_generation':{'model_upgrade_enabled':False}}}))
env={**os.environ,**spec['environment'],'HOME':str(home),'HERMES_HOME':str(profile),'TMPDIR':str(root/'tmp'),
'PYTHONPATH':str(base/'remote-tests/repository/tests')+':'+str(base/'remote-tests/repository')+':'+spec['environment']['PYTHONPATH']}
(root/'tmp').mkdir();configure_evaluation(home,'hermes',spec,endpoint,env)
env.update(LIFEOS_PROMPT_PROCESSING_PATH=str(base/'lifeos-evaluation-final/hooks/PromptProcessing.hook.ts'),LIFEOS_PROMPT_MODEL_ENV_PATH=env['LIFEOS_HOOK_MODEL_ENV'],LIFEOS_CHILD_LAUNCHER_DIR=str(home/'.local/bin'))
for p in (root,home,*root.rglob('*')):
 if not p.is_symlink():os.chown(p,1007,1007)
python=str(Path(spec['environment']['PYTHONPATH'].split(':')[-1]).parents[2]/'bin/python')
command=[python,'-m','unittest','test_native_prompt_processing.NativePromptProcessingTests.test_first_natural_prompt_names_session_with_local_model','-v']
code=1
try:
 with (root/'tests.txt').open('w') as f:r=subprocess.run(command,cwd=base/'remote-tests/repository',env=env,user=1007,group=1007,extra_groups=[],stdout=f,stderr=subprocess.STDOUT,timeout=150)
 code=r.returncode
 proof=[]
 for row in server.observed:
  if 'response_body_base64' not in row:continue
  assert row['upstream_status']==200
  for field in ('body','response_body'):assert hashlib.sha256(base64.b64decode(row[field+'_base64'])).hexdigest()==row[field+'_sha256']
  proof.append({k:row[k] for k in ('path','body_sha256','response_body_sha256','upstream_status','actual_model')})
 (root/'wire-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
 assert proof
finally:
 server.shutdown();server.server_close()
 with os.fdopen(os.open(root/'requests-private.json',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'w') as f:json.dump(server.observed,f)
 (root/'run.done').write_text(str(code)+'\n')
