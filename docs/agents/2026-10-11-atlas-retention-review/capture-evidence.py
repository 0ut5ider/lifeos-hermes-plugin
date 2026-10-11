# ABOUTME: Preserves reviewer commands and code evidence for the exact retention commits.
# ABOUTME: Reads repository and installed program source without accessing user fixture data.
import hashlib
import json
from pathlib import Path
import subprocess
repo = Path(__file__).resolve().parents[3]
out = Path(__file__).parent
commands = [
 ['git','rev-parse','HEAD','c9fdf51ca92c937a4d01e5c7903cf659a1e46552'],
 ['git','status','--short','--untracked-files=no'],
 ['git','diff','--name-only','c9fdf51c..72b0d4a2'],
]
records = []
for command in commands:
 r = subprocess.run(command,cwd=repo,capture_output=True,text=True)
 records.append({'command':command,'exit_code':r.returncode,'stdout':r.stdout,'stderr':r.stderr})
(out/'git-evidence.json').write_text(json.dumps(records,indent=2)+'\n')
files = [
 'lifeos_hook_bridge/memory_atlas_history.py','lifeos_hook_bridge/memory_atlas_sync.py',
 'lifeos_hook_bridge/memory_access.py','lifeos_hook_bridge/memory_service.py',
 'lifeos_hook_bridge/cli.py','lifeos_hook_bridge/memory_atlas.py',
 'lifeos_hook_bridge/memory_atlas_insight.py','lifeos_hook_bridge/memory_transaction.py',
 'lifeos_hook_bridge/memory_policy.py','lifeos_hook_bridge/memory_runtime.py',
 'lifeos_hook_bridge/memory_source_review.py','lifeos_hook_bridge/memory_sources.py',
 'lifeos_hook_bridge/memory_tab_freshness.py','lifeos_hook_bridge/memory_native.ts',
 'tests/test_memory_atlas_retention.py','tests/memory_atlas_retention_process.py',
 'tests/test_memory_atlas_capacity.py','tests/test_footprint_contracts.py',
 'tests/test_memory_atlas_sync.py',
 'docs/verification/2026-10-11-atlas-retention/README.md',
]
native = Path('/home/outsider/.cache/lifeos-atlas-20261010/native-limits-refresh/LifeOS/install')
files = [repo/p for p in files] + [native/'LIFEOS/ATLAS/Store.ts', native/'LIFEOS/ATLAS/collectors/Gear.ts',native/'LIFEOS/ATLAS/collectors/Projects.ts', native/'LIFEOS/PULSE/modules/atlas.ts']
index = {}
with (out/'inspected-code.txt').open('w') as stream:
 for p in files:
  content = p.read_text()
  index[str(p)] = hashlib.sha256(p.read_bytes()).hexdigest()
  stream.write(f'FILE {p}\n')
  for i,line in enumerate(content.splitlines(),1):
   stream.write(f'{i:5}: {line}\n')
  stream.write('\n')
(out/'inspected-source-hashes.json').write_text(json.dumps(index,indent=2)+'\n')
receipts = {}
for name in ('release-gate.json','development-verification.json'):
 p = repo/'docs/verification/2026-10-11-atlas-retention'/name
 value = json.loads(p.read_text())
 receipts[name] = {'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'top_level_keys':sorted(value)}
 for key in ('command','exit_code','duration_seconds','source_hashes_unchanged','tests','skipped','status'):
  if key in value:
   receipts[name][key] = value[key]
(out/'saved-receipts-summary.json').write_text(json.dumps(receipts,indent=2)+'\n')
(out/'additional-execution.json').write_text(json.dumps({'command':['/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python','-W','error::ResourceWarning',str(out/'additional-cases.py')],'environment_overrides':json.loads((out/'focused.json').read_text())['environment_overrides'],'reported_result':'Ran 16 tests in 67.573s; OK','new_cases':2,'replayed_existing_retention_cases':14,'note':'The unittest loader also discovers the imported fixture class. The output records all 16 cases.'},indent=2)+'\n')
(out/'additional.done').write_text('unittest OK\n')
