# ABOUTME: Checks independent public-program proof for the generated daily VersionDrift baseline.
# ABOUTME: Refuses missing or changed programs, metadata, catalogs, timestamps, and noncanonical bytes.
import copy,importlib.util,json
from pathlib import Path
root=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('daily_baseline_proof',root/'prove_daily_baseline.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
catalog=(root/'daily-baseline-public-programs.json').read_bytes();public=json.loads(catalog)
source='/synthetic/job/package/lifeos/LifeOS/install';installed='/synthetic/owner/.claude'
baseline={'schema':2,'version':'7.40.4','created_at':1792032465,
 'source_commit':'5e2f2e8c0abde612da0e99c16c0d07d4ec21b88c','source_root':source,'installed_root':installed,
 'files':public['files']}
raw=lambda x:(json.dumps(x)+'\n').encode()
expected=module.prove_baseline(raw(baseline),catalog,source,installed,1792032466)
assert expected['type']=='file' and expected['mode']==0o600
cases=[]
for label,mutate in [
 ('missing-file',lambda b:b['files'].pop(next(iter(b['files'])))),
 ('changed-file',lambda b:b['files'].__setitem__(next(iter(b['files'])),'0'*64)),
 ('changed-frozen-lock',lambda b:b['files'].__setitem__('skills/Telos/DashboardTemplate/bun.lock','0'*64)),
 ('extra-file',lambda b:b['files'].__setitem__('skills/Unknown/SKILL.md','0'*64)),
 ('wrong-version',lambda b:b.update(version='7.40.3')),
 ('wrong-commit',lambda b:b.update(source_commit='0'*40)),
 ('wrong-source',lambda b:b.update(source_root='/synthetic/other')),
 ('wrong-installation',lambda b:b.update(installed_root='/synthetic/other')),
 ('boolean-timestamp',lambda b:b.update(created_at=True)),
 ('prior-timestamp',lambda b:b.update(created_at=1792029931)),
 ('future-timestamp',lambda b:b.update(created_at=1792032468)),
 ('extra-key',lambda b:b.update(unknown=True)),
]:
 b=copy.deepcopy(baseline);mutate(b)
 try:module.prove_baseline(raw(b),catalog,source,installed,1792032466)
 except (AssertionError,KeyError,TypeError,ValueError):cases.append(label)
 else:raise AssertionError('Altered generated baseline accepted: '+label)
for label,data,selected in [
 ('changed-catalog',raw(baseline),catalog+b' '),
 ('noncanonical-serialization',json.dumps(baseline,indent=2).encode(),catalog),
 ('missing-newline',raw(baseline).rstrip(b'\n'),catalog),
]:
 try:module.prove_baseline(data,selected,source,installed,1792032466)
 except (AssertionError,KeyError,TypeError,ValueError):cases.append(label)
 else:raise AssertionError('Changed proof input accepted: '+label)
print(json.dumps({'status':'PASS','positive_controls':1,'refusal_controls':len(cases),'cases':cases,
 'live_baseline_or_reference_used':False},indent=2))
