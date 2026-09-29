# ABOUTME: Reproduces LifeOS patch review findings in disposable local fixtures.
# ABOUTME: Uses native patched hooks without production services or model calls.
from pathlib import Path
import os, json, subprocess, tempfile, sys
from datetime import datetime,timedelta,timezone
from lifeos_hook_bridge.bridge import HookBridge
from lifeos_hook_bridge.model_tiers import configured_model_map
SRC=Path('/tmp/lifeos-astra-review-20260929/source/LifeOS/install')
results={}
with tempfile.TemporaryDirectory(prefix='lifeos-review-rung-') as tmp:
 home=Path(tmp);root=home/'.claude';root.mkdir();settings=root/'settings.json'
 settings.write_text(json.dumps({'model':'local-model','hooks':{'UserPromptSubmit':[{'hooks':[{'type':'command','command':f'bun {SRC}/hooks/ModelRungGuard.hook.ts'}]}]}}))
 mapping=configured_model_map(lambda key,default:default,default_provider='local',default_model='local-model')
 bridge=HookBridge(settings,root,model_tiers_provider=lambda:mapping)
 bridge.environment.update(HOME=str(home),LIFEOS_DIR=str(root/'LIFEOS'))
 try:
  bridge.stop('Top tier answer',session_id='default-top-tier',model='local-model',reasoning_effort='xhigh')
  result=bridge.pre_llm_call('Continue',session_id='default-top-tier')
 finally: bridge.close()
 results['default_rung']={'mapping':mapping,'result':result,'log':(root/'LIFEOS/MEMORY/OBSERVABILITY/model-rung.jsonl').read_text()}
with tempfile.TemporaryDirectory(prefix='lifeos-review-probe-') as tmp:
 root=Path(tmp); settings=root/'settings.json';marker=root/'events.jsonl';recorder=root/'record.py'
 recorder.write_text('import json,sys\nfrom pathlib import Path\nwith Path('+repr(str(marker))+').open("a") as f: f.write(json.dumps(json.load(sys.stdin))+"\\n")\n')
 settings.write_text(json.dumps({'hooks':{'TaskCreated':[{'hooks':[{'type':'command','command':f'bun {SRC}/hooks/TaskGovernance.hook.ts'},{'type':'command','command':f'{sys.executable} {recorder}'}]}]}}))
 bridge=HookBridge(settings,root)
 try:
  supported=bridge._supports_native_task_hook('probe-session',str(root))
  verdict=bridge._native_task_verdict('probe-session','task-1','meaningful description','meaningful description',0)
 finally:bridge.close()
 results['capability_probe']={'supported':supported,'verdict':verdict,'events':[json.loads(row) for row in marker.read_text().splitlines()]}
with tempfile.TemporaryDirectory(prefix='lifeos-review-checkpoint-') as tmp:
 root=Path(tmp);repo=root/'repo';home=root/'home';claude=home/'.claude';claude.mkdir(parents=True)
 subprocess.run(['git','clone','--quiet','--no-hardlinks','/tmp/LifeOS-upstream',str(repo)],check=True,capture_output=True)
 hooks=repo/'.git/hooks';pre=hooks/'pre-commit';pre.write_text('#!/bin/sh\nsleep 6\n');pre.chmod(0o755)
 isa=claude/'LIFEOS/MEMORY/WORK/probe/ISA.md';isa.parent.mkdir(parents=True)
 isa.write_text('---\ntitle: timeout probe\nstarted: '+(datetime.now(timezone.utc)-timedelta(minutes=1)).isoformat()+'\n---\n\n## Claims\n- [x] ISC-1: Completed criterion\n')
 (claude/'checkpoint-repos.txt').write_text(str(repo)+'\n');(repo/'checkpoint-proof.txt').write_text('proof\n')
 env={**os.environ,'HOME':str(home),'LIFEOS_DIR':str(claude/'LIFEOS'),'GIT_AUTHOR_NAME':'Review Probe','GIT_AUTHOR_EMAIL':'review@example.invalid','GIT_COMMITTER_NAME':'Review Probe','GIT_COMMITTER_EMAIL':'review@example.invalid'}
 result=subprocess.run(['bun',str(SRC/'hooks/CheckpointPerISC.hook.ts')],input=json.dumps({'hook_event_name':'PostToolUse','tool_name':'Write','tool_input':{'file_path':str(isa)}}),text=True,capture_output=True,env=env,timeout=20)
 results['checkpoint_slow_hook']={'returncode':result.returncode,'stdout':result.stdout,'stderr':result.stderr,'state':json.loads((isa.parent/'.checkpoint-state.json').read_text()),'git_status':subprocess.check_output(['git','status','--porcelain'],cwd=repo,text=True)}
print(json.dumps(results,indent=2))
