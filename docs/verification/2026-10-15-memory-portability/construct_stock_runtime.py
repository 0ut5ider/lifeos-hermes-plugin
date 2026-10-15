# ABOUTME: Constructs the actual unpatched sealed Hermes runtime from a private checkpoint package.
# ABOUTME: Verifies native commands and records safe identities without qualifying or selecting a release.
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

repo=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(repo),'/home/outsider/.cache/lifeos-release-0.5.0-20261014/packages/0.5.0-04efe633/hermes']
sys.dont_write_bytecode=True
os.umask(0o077)
from optional.lifeos_release_manager.release_stage import prepare_runtime,runtime_source_fingerprint
from optional.lifeos_release_manager.stock_hermes import validate_archive,verify_source
from optional.lifeos_release_manager.release_programs import publish

cache=Path('/home/outsider/.cache/lifeos-memory-portability-20261015')
parser=argparse.ArgumentParser()
parser.add_argument('--package',type=Path,required=True)
parser.add_argument('--root',type=Path,required=True)
args=parser.parse_args()
package=args.package.absolute()
web=Path('/home/outsider/.cache/lifeos-daily-promotion-20261014/hermes-dashboard.tgz')
root=args.root.absolute();root.mkdir(mode=0o700)
profile=root/'account/.hermes';profile.mkdir(parents=True,mode=0o700)
profile.parent.chmod(0o700)
publish(profile/'config.yaml',b'model: {default: synthetic-model, provider: custom, base_url: "http://127.0.0.1:9/v1", api_key: "synthetic-test-key"}\nmemory: {memory_enabled: true, user_profile_enabled: true}\nplugins: {enabled: []}\nplatforms: {discord: {enabled: false}}\n')
job=root/'runtime';job.mkdir(mode=0o700)
manifest=json.loads((package/'DAILY-CANDIDATE.json').read_bytes())
validate_archive(package/'stock-hermes.tgz',manifest['stock_hermes'])
started=time.monotonic();receipt={'qualified_release':False,'selected_live':False,'daily_changed':False,'status':'FAIL'}
try:
 runtime=prepare_runtime(job,package,web,profile,stock=True)
 verify_source(job/'stock-source',runtime['stock_source'])
 environment=dict(os.environ,HOME=str(profile.parent),HERMES_HOME=str(profile),PYTHONDONTWRITEBYTECODE='1')
 results={}
 for name,args in {'hermes':['--version'],'hermes-agent':['--help'],'hermes-acp':['--help']}.items():
  result=subprocess.run([str(job/'bin'/name),*args],env=environment,capture_output=True,text=True,timeout=90)
  (root/(name+'.stdout')).write_text(result.stdout);(root/(name+'.stderr')).write_text(result.stderr)
  results[name]=result.returncode
  if result.returncode or result.stderr:raise RuntimeError('The actual stock command refuses its native invocation: '+name)
 check=subprocess.run([str(job/'bin/hermes'),'config','check'],env=environment,capture_output=True,text=True,timeout=90)
 (root/'configuration.stdout').write_text(check.stdout);(root/'configuration.stderr').write_text(check.stderr)
 if check.returncode or check.stderr:raise RuntimeError('Stock Hermes refuses the retained configuration')
 publish(profile/'memories/MEMORY.md',b'Synthetic stock constructor memory entry.')
 publish(profile/'memories/USER.md',b'Synthetic stock constructor user entry.')
 from hermes_cli import _launchers
 code=('import importlib,json,types\n'
  'package=types.ModuleType("stock_memory_probe")\n'
  'package.__path__=[sys.argv[1]];sys.modules[package.__name__]=package\n'
  'probe=importlib.import_module(package.__name__+".memory_transition_probe")\n'
  'print(json.dumps(probe.verify_builtin(json.load(sys.stdin))))\n')
 command=_launchers.runtime_command(job/'hermes',[str(package/'lifeos_hook_bridge')],code=code,python=runtime['python'])
 expected={'MEMORY.md':'Synthetic stock constructor memory entry.','USER.md':'Synthetic stock constructor user entry.'}
 result=subprocess.run(command,input=json.dumps(expected),env=environment,capture_output=True,text=True,timeout=120)
 (root/'fresh-constructor.stderr').write_text(result.stderr)
 if result.returncode or result.stderr:
  (root/'fresh-constructor.stdout').write_text(result.stdout)
  raise RuntimeError('The actual fresh stock Hermes agent does not verify built-in memory')
 proof=json.loads(result.stdout)
 if not proof['fresh_agent_verified'] or proof['model_turn_executed'] or set(proof['active_plugins']) & {'lifeos','lifeos-hook-bridge','lifeos-release-manager'}:
  raise RuntimeError('The fresh stock agent keeps active integration behavior')
 (root/'fresh-constructor.json').write_text(json.dumps(proof,indent=2)+'\n')
 receipt['fresh_constructor']=proof
 receipt.update(status='PASS',commit=runtime['stock_source']['commit'],patches=0,commands=results,
  configuration_exit=check.returncode,source=runtime_source_fingerprint(job/'hermes'),stock_source=runtime['stock_source'])
except Exception as error:
 receipt['error_type']=type(error).__name__;raise
finally:
 receipt['elapsed_seconds']=time.monotonic()-started
 (root/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
 (root/'construction.done').write_text('0\n' if receipt['status']=='PASS' else '1\n')
