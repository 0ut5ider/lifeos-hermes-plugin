# ABOUTME: Verifies real stock Hermes commands and passive package-manager admission.
# ABOUTME: Records synthetic-profile diagnostics without selecting a live runtime or calling a model.
import argparse
import json
import os
from pathlib import Path
import subprocess

parser=argparse.ArgumentParser();parser.add_argument('label');arguments=parser.parse_args()
root=Path('/home/outsider/.cache/lifeos-memory-portability-20261015/stock-runtime-construction')
profile=root/'account/.hermes';job=root/'runtime'
env=dict(os.environ,HOME=str(profile.parent),HERMES_HOME=str(profile),PYTHONDONTWRITEBYTECODE='1')
commands={'hermes-version':['hermes','--version'],'hermes-agent':['hermes-agent','--help'],
    'hermes-acp':['hermes-acp','--help'],'configuration':['hermes','config','check']}
receipt={'status':'PASS','selected_live':False,'model_turn_executed':False,'qualified_release':False,'commands':{}}
for label,(name,*args) in commands.items():
 result=subprocess.run([str(job/'bin'/name),*args],env=env,text=True,capture_output=True,timeout=90)
 (root/(arguments.label+'-'+label+'.stdout')).write_text(result.stdout)
 (root/(arguments.label+'-'+label+'.stderr')).write_text(result.stderr)
 receipt['commands'][label]={'exit':result.returncode,'stderr_empty':result.stderr=='',
     'pm_warning':any('install out of sync' in text for text in (result.stdout,result.stderr))}
 if result.returncode or result.stderr or receipt['commands'][label]['pm_warning']:receipt['status']='FAIL'
output=Path(__file__).parent
(output/(arguments.label+'.json')).write_text(json.dumps(receipt,indent=2)+'\n')
(output/(arguments.label+'.done')).write_text('0\n' if receipt['status']=='PASS' else '1\n')
print(json.dumps(receipt))
raise SystemExit(0 if receipt['status']=='PASS' else 1)
