# ABOUTME: Reproduces nested skill project role precedence and actual ConfigChange hook delivery.
# ABOUTME: Uses retained before/after modules, synthetic files, and real hook subprocesses only.
import importlib.util,json,os,subprocess,sys,tempfile
from pathlib import Path
out=Path(__file__).parent
modules={}
for label in ('before','after'):
 spec=importlib.util.spec_from_file_location('lifeos_hook_bridge.review_'+label,out/('bridge_'+label+'.py'))
 module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module);modules[label]=module
results={}
with tempfile.TemporaryDirectory(prefix='pr16-role-precedence-') as temp:
 root=Path(temp);user=root/'user/.claude';nested=user/'skills/research-project';policy=root/'policy';other=root/'other-project'
 (nested/'.claude').mkdir(parents=True);(other/'.claude').mkdir(parents=True)
 (user/'settings.json').write_text('{}');(nested/'.claude/settings.json').write_text('{}');(nested/'.claude/settings.local.json').write_text('{}');(other/'.claude/settings.json').write_text('{}')
 for label,module in modules.items():
  module.POLICY_DIRECTORY=policy
  b=object.__new__(module.HookBridge);b.settings_path=user/'settings.json';b.project_dirs=(user.parent,nested,other)
  sources=b._config_sources();files=b._config_files()
  results[label]={'nested_settings_role':sources[nested/'.claude/settings.json'],'nested_local_role':sources[nested/'.claude/settings.local.json'],
   'path_count':len(files),'paths':sorted(str(p.relative_to(root)) for p in files),'nested_signatures':{p.name:files[p] for p in (nested/'.claude/settings.json',nested/'.claude/settings.local.json')}}
assert results['before']['paths']==results['after']['paths']
assert results['before']['nested_signatures']==results['after']['nested_signatures']
for label,module in modules.items():
 with tempfile.TemporaryDirectory(prefix='pr16-role-hook-') as temp:
  root=Path(temp);home=root/'user';user=home/'.claude';nested=user/'skills/research-project';other=root/'other-project';policy=root/'policy'
  (nested/'.claude').mkdir(parents=True);(other/'.claude').mkdir(parents=True)
  (nested/'.claude/settings.json').write_text('{}');(other/'.claude/settings.json').write_text('{}')
  actor=root/'record.py';marker=root/'events.jsonl'
  actor.write_text('import json,sys\nfrom pathlib import Path\np=Path(sys.argv[1]);v=json.load(sys.stdin)\nwith p.open("a") as f:f.write(json.dumps(v)+"\\n")\n')
  (user/'settings.json').write_text(json.dumps({'hooks':{'ConfigChange':[{'matcher':'skills','hooks':[{'type':'command','command':sys.executable+' '+str(actor)+' '+str(marker)}]}]}}))
  module.POLICY_DIRECTORY=policy;previous=Path.cwd()
  try:
   os.chdir(home)
   b=module.HookBridge(user/'settings.json',user,lifeos_home=home)
   b._remember_project(str(nested),'nested-session');b._remember_project(str(other),'other-session')
   b.started_sessions.update({'nested-session','other-session'});b.config_files=b._config_files()
   (nested/'.claude/settings.json').write_text('{"changed":true}')
   b.poll_config_changes(force=True)
   b.watcher_stop.set()
   if b.watcher is not None:b.watcher.join(timeout=5)
   rows=[json.loads(line) for line in marker.read_text().splitlines()] if marker.exists() else []
   results[label]['actual_hook_events']=[{'session_id':r['session_id'],'source':r['source'],'file_path':r['file_path']} for r in rows]
  finally:os.chdir(previous)
(out/'role-precedence-results.json').write_text(json.dumps(results,indent=2)+'\n');print(json.dumps(results,indent=2))
assert {r['session_id'] for r in results['before']['actual_hook_events']}=={'nested-session','other-session'}
assert results['after']['actual_hook_events']==[]
