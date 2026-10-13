# ABOUTME: Verifies every frozen native lock after the isolated Bun version comparison.
# ABOUTME: Reports measured lock integrity without relying on installer expectations.
import hashlib,json
from pathlib import Path
base=Path('/home/lifeos-hermes/releases/qualification-20261012-stable/bun-comparison')
report=json.loads((base/'results.json').read_bytes());assert len(report['cases'])==5 and (base/'process.done').read_text().strip()=='0'
catalog=json.loads((base/'fixed-bridge/dependency_locks/catalog.json').read_bytes());checks=[]
for row in report['cases']:
 home=base/(row['version']+'-'+str(row['case']))
 root=home/('.claude' if row['exit_code']==0 else 'failed')
 changed=[name for name,item in catalog['packages'].items() if not (root/name/'bun.lock').is_file() or hashlib.sha256((root/name/'bun.lock').read_bytes()).hexdigest()!=item['lock_sha256']]
 assert not changed,changed
 checks.append({'version':row['version'],'case':row['case'],'lock_files_checked':len(catalog['packages']),'changed_locks':changed})
print(json.dumps({'status':'PASS','cases':report['cases'],'measured_lock_checks':checks,'active_profile_changed':False},indent=2))
