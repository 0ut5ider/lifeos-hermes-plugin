# ABOUTME: Compares the historical patch result with the grouped patch result.
# ABOUTME: Verifies disjoint file ownership and both distributed patch copies.
import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile

REPO=Path(__file__).resolve().parents[3]
BASE=Path('/home/outsider/.cache/lifeos-footprint-20260929/hermes-clean')
PREPARED=Path('/home/outsider/.cache/lifeos-footprint-20260929/prepared-final/hermes')

def run(*args,cwd=REPO):
 return subprocess.check_output(args,cwd=cwd)
def names(source):
 tree=ast.parse(source)
 return next(ast.literal_eval(node.value) for node in tree.body if isinstance(node,ast.Assign) and any(isinstance(target,ast.Name) and target.id=='HERMES_PATCHES' for target in node.targets))
old_names=names(run('git','show','3966a42:lifeos_hook_bridge/install_source.py').decode())
new_names=names((REPO/'lifeos_hook_bridge/install_source.py').read_text())
old_patches={name:run('git','show','3966a42:patches/'+name) for name in old_names}
new_patches={name:(REPO/'patches'/name).read_bytes() for name in new_names}
paths=lambda blob: re.findall(rb'^diff --git a/(.+) b/.+$',blob,re.M)
all_paths=set(path.decode() for blob in [*old_patches.values(),*new_patches.values()] for path in paths(blob))
result={'historical_group_count':len(old_names),'new_group_count':len(new_names),'ownership':{},'mirror_mismatches':[]}
for name,blob in new_patches.items():
 for path in paths(blob): result['ownership'].setdefault(path.decode(),[]).append(name)
 if blob != (REPO/'lifeos_hook_bridge/patches'/name).read_bytes(): result['mirror_mismatches'].append(name)
result['ownership_collisions']={path:groups for path,groups in result['ownership'].items() if len(groups)>1}
with tempfile.TemporaryDirectory(prefix='lifeos-group-review-') as temp:
 temp=Path(temp)
 trees={}
 for label,patches in [('historical',old_patches),('grouped',new_patches)]:
  tree=temp/label; tree.mkdir(); trees[label]=tree
  for name in all_paths:
   show=subprocess.run(['git','show','HEAD:'+name],cwd=BASE,capture_output=True)
   if show.returncode==0:
    dest=tree/name; dest.parent.mkdir(parents=True,exist_ok=True); dest.write_bytes(show.stdout)
  for name,blob in patches.items():
   patchfile=temp/name; patchfile.write_bytes(blob)
   subprocess.run(['git','apply',str(patchfile)],cwd=tree,check=True,capture_output=True)
 result['changed_from_historical']=[]; result['prepared_replay_mismatches']=[]
 def data(path): return path.read_bytes() if path.exists() else None
 for name in sorted(all_paths):
  if data(trees['historical']/name)!=data(trees['grouped']/name): result['changed_from_historical'].append(name)
  if data(PREPARED/name)!=data(trees['grouped']/name): result['prepared_replay_mismatches'].append(name)
print(json.dumps(result,indent=2))
