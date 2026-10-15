# ABOUTME: Proves the generated daily baseline from an independently authenticated public program catalog.
# ABOUTME: Permits one evidence-only fingerprint while preserving current owner mounts and retained program checks.
import hashlib,json,os,re,stat
from pathlib import Path

CATALOG_SHA256='9e3271df325328090fe525b397bbae389fb3806f854d773d98d0a88895194e47'
FILES_SHA256='5deab51ef78b77e0d577b97f94428d8d13337c7cfdcde75c9e9a93c7e3746b92'
PUBLICATION_TIME=1792029932

def prove_baseline(raw,catalog_raw,source_root,installed_root,latest_time):
 assert hashlib.sha256(catalog_raw).hexdigest()==CATALOG_SHA256
 catalog=json.loads(catalog_raw)
 assert catalog['archive_sha256']=='a6dd0e11b8fb1b5ae30345be20c955db02728839f7bc907f60a70944ad392813'
 assert len(catalog['files'])==1742 and len(catalog['frozen_lock_overrides'])==5
 assert hashlib.sha256(json.dumps(catalog['files'],sort_keys=True,separators=(',',':')).encode()).hexdigest()==FILES_SHA256
 baseline=json.loads(raw)
 assert set(baseline)=={'schema','version','created_at','source_commit','source_root','installed_root','files'}
 timestamp=baseline['created_at']
 assert type(timestamp) is int and type(latest_time) is int and PUBLICATION_TIME<=timestamp<=latest_time
 expected={'schema':2,'version':catalog['native_version'],'created_at':timestamp,
  'source_commit':catalog['source_commit'],'source_root':source_root,'installed_root':installed_root,
  'files':dict(sorted(catalog['files'].items()))}
 assert baseline==expected
 reconstructed=(json.dumps(expected)+'\n').encode()
 assert raw==reconstructed,'The generated baseline does not use its native canonical serialization'
 return {'type':'file','mode':0o600,'sha256':hashlib.sha256(reconstructed).hexdigest()}

def baseline_override(job,request,transaction,current_overrides):
 installed=Path(request['installed'])
 path=installed.parent/'.local/state/lifeos-hook-bridge/version-drift-baseline.json'
 assert path.resolve()==path
 entries=[e for e in transaction._load()['entries'] if e['target']==str(path)]
 assert len(entries)==1 and entries[0]['kind']=='file' and entries[0]['source']==str(path)
 assert str(path) not in current_overrides,'The current owner mount already owns the baseline'
 info=path.lstat()
 assert stat.S_ISREG(info.st_mode) and info.st_uid==os.getuid() and info.st_nlink==1 and stat.S_IMODE(info.st_mode)==0o600
 intent=job/'mount-intent.json';intent_info=intent.lstat()
 assert stat.S_ISREG(intent_info.st_mode) and intent_info.st_uid==os.getuid() and intent_info.st_nlink==1
 assert stat.S_IMODE(intent_info.st_mode)==0o600 and intent_info.st_size<4096
 value=json.loads(intent.read_bytes())
 assert set(value)=={'prior_journal_sha256','action'} and value['action']=='apply'
 assert value['prior_journal_sha256'] is None or re.fullmatch('[0-9a-f]{64}',value['prior_journal_sha256'])
 raw=path.read_bytes();catalog=Path(__file__).with_name('daily-baseline-public-programs.json').read_bytes()
 expected=prove_baseline(raw,catalog,str(job/'package/lifeos/LifeOS/install'),str(installed),int(intent_info.st_mtime)+1)
 after=path.lstat();after_intent=intent.lstat()
 stamp=lambda s:(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_mode,s.st_uid,s.st_nlink)
 assert stamp(info)==stamp(after) and stamp(intent_info)==stamp(after_intent)
 return str(path),expected
