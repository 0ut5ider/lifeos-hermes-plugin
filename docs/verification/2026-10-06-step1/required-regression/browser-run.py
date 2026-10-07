# ABOUTME: Installs pinned browser test tools into a disposable runtime and checks real results.
# ABOUTME: Retains completion and source bindings without changing the active Hermes profile.
import json,os,subprocess,traceback
from pathlib import Path
root=Path(__file__).parent/'browser-probe';root.mkdir(exist_ok=True)
(root/'home/.hermes').mkdir(parents=True,exist_ok=True)
source=Path(__file__).parent/'prepared-evaluation-final/hermes'
repo=Path('/home/outsider/Projects/Hermes_agent/LifeOS_plugin')
env={**os.environ,'HERMES_HOME':str(root/'home/.hermes'),'HERMES_RUNTIME_DIR':str(root/'runtime'),
'PYTHONPATH':'tests:.'+os.pathsep+str(source),'TMPDIR':'/home/outsider/.cache/lhc6','LIFEOS_BROWSER_PROBE':'1'}
python='/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python'
code=1
try:
 with (root/'install.txt').open('w') as out:
  subprocess.run([python,'-c','import pm; pm.ensure("agent-browser"); pm.ensure("chromium")'],cwd=repo,env=env,stdout=out,stderr=subprocess.STDOUT,check=True)
 with (root/'tests.txt').open('w') as out:
  result=subprocess.run([python,'-m','unittest','test_live_browser_result_safety','-v'],cwd=repo,env=env,stdout=out,stderr=subprocess.STDOUT)
 code=result.returncode
finally:(root/'run.done').write_text(str(code)+'\n')
