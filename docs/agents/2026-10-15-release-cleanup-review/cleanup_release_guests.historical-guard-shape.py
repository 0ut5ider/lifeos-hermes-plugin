# Reviewer characterization: restores the two guards observed before the primary fix.
# This is not a frozen pre-fix full operator; it retains the current operation ledger.
# ABOUTME: Removes only the three exact release rehearsal guests after complete daily recovery passes.
# ABOUTME: Preserves all other guests and refuses nonempty or redirected disposable storage.
import argparse,json,re,subprocess
from pathlib import Path

OWNED={111:'lifeos-050-daily-rehearsal',112:'lifeos-050-fresh-rehearsal',113:'lifeos-050-public-install'}
def validate_guest(guest,config):
 assert guest in OWNED and config['hostname']==OWNED[guest]
 assert config['tags']=='disposable;lifeos-test'
 assert config['rootfs']==f'lifeos-050-tests:{guest}/vm-{guest}-disk-0.raw,size=120G'
 assert not any(re.fullmatch(r'(mp|unused)\d+',key) for key in config)

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--evidence',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
 args=parser.parse_args();assert not args.out.exists()
 operations=[]
 def run(command):
  result=subprocess.run(command,capture_output=True,text=True,timeout=180)
  operations.append({'command':command,'exit_code':result.returncode})
  args.out.with_suffix('.operations.json').write_text(json.dumps(operations,indent=2)+'\n')
  result.check_returncode()
  return result.stdout
 def config(guest):
  raw=run(['pct','config',str(guest)])
  return dict(line.split(':',1) for line in raw.splitlines() if ':' in line and not line.startswith('#'))
 def validated(guest):
  value={key:value.strip() for key,value in config(guest).items()};validate_guest(guest,value)
 proof=json.loads((args.evidence/'verification.json').read_bytes())
 assert proof['status']=='PASS' and proof['version']=='0.5.0' and proof['source_guest']==102 and proof['restored_guest']==110
 assert proof['program_commit']=='04efe633296eb2b1a1d95561ca6d3e9516cd47dc'
 assert proof['archive_sha256']=='a6dd0e11b8fb1b5ae30345be20c955db02728839f7bc907f60a70944ad392813'
 assert (args.evidence/'process.done').read_text().strip()=='0'
 prior=json.loads((args.evidence/'operations.json').read_bytes())
 assert len([row for row in prior if row['label']=='destroy-disposable' and row['exit_code']==0])==1
 archive=proof['archive'];assert archive.startswith('PBS-01:backup/ct/102/')
 protection=json.loads(run(['pvesh','get','/nodes/pve-tr1950x/storage/PBS-01/content/'+archive,'--output-format','json']))
 assert protection['protected'] is True
 inventory_command=['pvesh','get','/cluster/resources','--type','vm','--output-format','json']
 before=json.loads(run(inventory_command));assert not any(row['vmid']==110 for row in before)
 assert all(any(row['vmid']==guest and row['type']=='lxc' for row in before) for guest in OWNED)
 preserved={row['vmid']:{key:row[key] for key in ('type','name','status')} for row in before if row['vmid'] not in OWNED}
 for guest in OWNED:validated(guest)
 for guest in OWNED:
  run(['pct','shutdown',str(guest),'--timeout','90'])
  assert run(['pct','status',str(guest)]).strip()=='status: stopped'
  validated(guest)
  run(['pct','destroy',str(guest),'--purge','1'])
 after=json.loads(run(inventory_command))
 assert all(row['vmid'] not in OWNED for row in after)
 assert {row['vmid']:{key:row[key] for key in ('type','name','status')} for row in after}==preserved
 storage=json.loads(run(['pvesh','get','/storage/lifeos-050-tests','--output-format','json']))
 assert storage['type']=='dir' and storage['path']=='/var/lib/vz/lifeos-050-tests' and storage['storage']=='lifeos-050-tests'
 root=Path(storage['path']);assert root.resolve()==root and root.is_dir() and not root.is_symlink()
 assert json.loads(run(['pvesh','get','/nodes/pve-tr1950x/storage/lifeos-050-tests/content','--output-format','json']))==[]
 directories=list(root.rglob('*'));assert all(path.is_dir() and not path.is_symlink() for path in directories)
 run(['pvesm','remove','lifeos-050-tests'])
 for path in sorted(directories,key=lambda p:len(p.parts),reverse=True):path.rmdir()
 root.rmdir()
 report={'status':'PASS','owned_guests_removed':sorted(OWNED),'restore_guest_already_removed':110,
  'owned_storage_removed':True,'protected_archive_preserved':archive,'other_guests_preserved':preserved,'operations':operations}
 args.out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
