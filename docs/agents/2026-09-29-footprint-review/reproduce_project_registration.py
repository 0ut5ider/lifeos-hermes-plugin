# ABOUTME: Reproduces native task policy discovery through project settings.
# ABOUTME: Runs each candidate bridge in a separate disposable process.
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile

REPO = Path(__file__).resolve().parents[3]
WORKER = r'''
import json, os
from pathlib import Path
from lifeos_hook_bridge.bridge import HookBridge
from unittest.mock import patch
patch("lifeos_hook_bridge.bridge._trusted_project", return_value=True).start()
root=Path(os.environ['REVIEW_FIXTURE'])
project=root/'project'
os.chdir(project)
bridge=HookBridge(root/'settings.json', root)
try:
 bridge._remember_project(str(project), 'review')
 print(json.dumps({'native_support':bridge._supports_native_task_hook('review',str(project)),
  'verdict':bridge._kanban_task_verdict({'title':'Meaningful task description'},'review','call')}))
finally:
 bridge.close()
'''
with tempfile.TemporaryDirectory(prefix='lifeos-review-') as directory:
 temp=Path(directory)
 old=temp/'old'; old.mkdir()
 archive=temp/'head.tar'
 archive.write_bytes(subprocess.check_output(['git','archive','3966a42','lifeos_hook_bridge'],cwd=REPO))
 with tarfile.open(archive) as tar: tar.extractall(old,filter='data')
 root=temp/'fixture'; (root/'hooks').mkdir(parents=True)
 native=root/'hooks/TaskGovernance.hook.ts'
 native.write_text('const input=JSON.parse(await Bun.stdin.text());\nif(input.hermes_bridge_probe){console.log(JSON.stringify({hermes_bridge_task_governance:1}));process.exit(0);}\nconsole.error("native task policy rejects this task");process.exit(2);\n')
 (root/'settings.json').write_text('{"hooks":{}}')
 project=root/'project'; (project/'.claude').mkdir(parents=True)
 (project/'.claude/settings.json').write_text(json.dumps({'hooks':{'TaskCreated':[{'hooks':[{'type':'command','command':f'bun {native}'}]}]}}))
 env={key:value for key,value in os.environ.items() if not any(word in key for word in ('TOKEN','KEY','BASE_URL','ANTHROPIC','LIFEOS','HERMES'))}
 env['REVIEW_FIXTURE']=str(root)
 for label,path in [('3966a42',old),('working_tree',REPO)]:
  result=subprocess.run([sys.executable,'-c',WORKER],cwd=temp,env={**env,'PYTHONPATH':str(path)},text=True,capture_output=True)
  print(json.dumps({'version':label,'returncode':result.returncode,'stdout':result.stdout,'stderr':result.stderr}))
