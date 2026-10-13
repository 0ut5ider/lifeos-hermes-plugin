# ABOUTME: Compares real filesystem inventory edges and descriptor ownership before and after the scanner change.
# ABOUTME: Uses only synthetic roots, symlinks, special settings, unreadable directories, and metadata.
import importlib.util,json,os,sys,tempfile
from pathlib import Path
out=Path(__file__).parent;modules={}
for label in ('before','closure'):
 spec=importlib.util.spec_from_file_location('lifeos_hook_bridge.edges_'+label,out/('bridge_'+label+'.py'))
 module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module);modules[label]=module
with tempfile.TemporaryDirectory(prefix='pr16-inventory-edges-') as temp:
 root=Path(temp);user=root/'user/.claude';user.mkdir(parents=True);project=root/'project';(project/'.claude').mkdir(parents=True)
 policy=root/'policy';(policy/'managed-settings.json').mkdir(parents=True)
 os.mkfifo(user/'settings.json');os.mkfifo(project/'.claude/settings.local.json')
 backing=root/'backing-skills';backing.mkdir();(user/'skills').symlink_to(backing,target_is_directory=True)
 for name in ['SKILL.md','.hidden','node_modules/example/index.js','protected/data']:
  p=backing/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('synthetic')
 target=root/'outside/file';target.parent.mkdir();target.write_text('synthetic')
 (backing/'file-link').symlink_to(target);(backing/'dir-link').symlink_to(target.parent,target_is_directory=True)
 (backing/'broken-link').symlink_to(root/'missing');(backing/'cycle-link').symlink_to(backing/'cycle-link');os.mkfifo(backing/'fifo')
 protected=backing/'protected';protected.chmod(0)
 results={}
 try:
  inventories={}
  for label,module in modules.items():
   module.POLICY_DIRECTORY=policy;b=object.__new__(module.HookBridge);b.settings_path=user/'settings.json';b.project_dirs=(project,project)
   sources=b._config_sources();files=b._config_files();inventories[label]=(sources,files)
   fd_before=len(list(Path('/proc/self/fd').iterdir()))
   for _ in range(100):b._config_sources();b._config_files()
   fd_after=len(list(Path('/proc/self/fd').iterdir()))
   assert fd_after==fd_before
   results[label]={'sources':{str(p.relative_to(root)):role for p,role in sources.items()},'files':{str(p.relative_to(root)):stamp for p,stamp in files.items()},'fd_before':fd_before,'fd_after_100_complete_scans':fd_after}
  assert inventories['before']==inventories['closure']
  assert user/'skills/file-link' in inventories['closure'][1]
  assert not any('dir-link/' in str(p) for p in inventories['closure'][1])
  assert user/'settings.json' in inventories['closure'][1] and project/'.claude/settings.local.json' in inventories['closure'][1]
  assert user/'skills/fifo' not in inventories['closure'][1]
  result={'status':'PASS','exact_stable_roles_and_signatures':True,'effective_uid':os.geteuid(),'case':'symlink root, file and directory links, broken/cyclic links, hidden/dependency files, missing project settings, directory and FIFO settings, unreadable skill child, repeated project roots','results':results}
  (out/'inventory-edge-closure-results.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
 finally:protected.chmod(0o700)
