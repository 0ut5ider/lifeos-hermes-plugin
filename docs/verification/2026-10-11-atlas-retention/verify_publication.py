# ABOUTME: Checks Atlas retention source and evidence before repository publication.
# ABOUTME: Scans current files and branch versions without printing private credential values.
import hashlib
import json
from pathlib import Path
import re
import subprocess


root = Path(__file__).resolve().parents[3]
out = Path(__file__).parent
git = lambda *args: subprocess.check_output(['git',*args],cwd=root)
paths = set(git('diff','--name-only','origin/main').decode().splitlines())
paths.update(str(path.relative_to(root)) for path in out.iterdir() if path.is_file() and path.name!='publication-checks.json')
paths.update({'lifeos_hook_bridge/memory_atlas_history.py','tests/test_memory_atlas_retention.py',
    'tests/memory_atlas_retention_process.py','notes/2026-10-11-atlas-history-retention.md'})
paths.discard(str((out/'publication-checks.json').relative_to(root)))
payloads = [(name,(root/name).read_bytes()) for name in sorted(paths) if (root/name).is_file()]
for commit in git('rev-list','origin/main..HEAD').decode().splitlines():
    names = git('diff-tree','--no-commit-id','--name-only','-r',commit).decode().splitlines()
    for name in names:
        payloads.append((commit+':'+name,git('show',commit+':'+name)))
cache = Path('/home/outsider/.cache/lifeos-daily-20261011/dashboard-access.json')
secrets = []
def collect(value):
    if isinstance(value,dict):
        for key,item in value.items():
            if re.search('password|token|secret',key,re.IGNORECASE) and isinstance(item,str) and len(item)>=8:
                secrets.append(item.encode())
            else:
                collect(item)
    elif isinstance(value,list):
        for item in value:
            collect(item)
if cache.is_file():
    collect(json.loads(cache.read_text()))
findings = []
for name,content in payloads:
    if any(secret in content for secret in secrets) or re.search(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',content):
        findings.append(name)
assert not findings, 'Credential exclusion fails for: '+', '.join(findings)
json_count = python_count = 0
for name in sorted(paths):
    path=root/name
    if not path.is_file():
        continue
    if path.suffix=='.json':
        json.loads(path.read_text());json_count+=1
    elif path.suffix=='.py':
        compile(path.read_bytes(),str(path),'exec');python_count+=1
    elif path.suffix=='.md':
        text=path.read_text()
        assert '\u2014' not in text,name
        for target in re.findall(r'\]\(([^)]+)\)',text):
            target=target.split('#',1)[0]
            if target and not re.match(r'[a-z]+:',target) and not target.startswith('/'):
                assert (path.parent/target).exists(),name+': '+target
report={'status':'PASS','branch':git('branch','--show-current').decode().strip(),
    'head':git('rev-parse','HEAD').decode().strip(),'files_and_branch_versions_scanned':len(payloads),
    'actual_private_values_checked':len(secrets),'credential_findings':[],
    'json_documents_parsed':json_count,'python_files_compiled':python_count,
    'current_source_hashes':{name:hashlib.sha256(content).hexdigest() for name,content in payloads if ':' not in name},
    'limits':{'daily_guest_deployed':False,'new_off_server_guest_restore_tested':False}}
(out/'publication-checks.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({key:value for key,value in report.items() if key!='current_source_hashes'},indent=2))
