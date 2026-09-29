# ABOUTME: Applies the verified Stop dispatcher correction to the .212 release.
# ABOUTME: Restores the original release snapshot if source or live checks fail.
import json,os,runpy,shutil,sys,time,traceback
from pathlib import Path
h=Path.home()
assert h==Path('/home/lifeos-hermes') and os.getuid()==1004
r=h/'workspace/releases/20260929-patch-footprint-e762ac6'
n=runpy.run_path(str(r/'deploy_212.py'))
f=n['verify'].__globals__
f['CANDIDATE']=r/'prepared-corrected/hermes'
record=json.loads((r/'preflight.json').read_text())
old_result=json.loads((r/'result.json').read_text())
assert json.loads((r/'status.json').read_text())['state']=='applied'
assert n['git']('rev-parse','HEAD')==old_result['hermes_revision']
assert not n['git']('status','--porcelain')
revision=n['run'](['git','-C',r/'plugin-source','rev-parse','HEAD'])
expected={str(relative):n['_digest_file'](path) for relative,path in n['_files'](f['CANDIDATE'])}
prior={str(relative):n['_digest_file'](path) for relative,path in n['_files'](r/'prepared/hermes')}
changed=sorted(path for path in expected if expected[path]!=prior.get(path))
assert changed==['hermes_cli/plugins.py','tests/hermes_cli/test_stop_policy_dispatch.py'],changed
assert not prior.keys()-expected.keys()
record['revision']=revision
record['hermes_digest_after']=n['_digest_tree'](f['CANDIDATE'])
record['plugin_digest_after']=n['_digest_tree'](r/'plugin-source/lifeos_hook_bridge')
with (r/'correction.log').open('w') as output:
 sys.stdout=sys.stderr=output
 try:
  n['save']('status.json',{'state':'correcting_stop_dispatch'})
  for unit in ['hermes-dashboard.service','hermes-gateway.service']:n['service'](unit,'stop')
  for name in changed:
   source=f['CANDIDATE']/name;target=n['HERMES']/name
   target.parent.mkdir(parents=True,exist_ok=True)
   temporary=target.with_name('.'+target.name+'.release')
   shutil.copy2(source,temporary);os.replace(temporary,target)
  n['_sync_tree'](r/'plugin-source/lifeos_hook_bridge',n['PLUGIN'])
  n['git']('add','--',*changed)
  n['git']('-c','user.name=LifeOS Release','-c','user.email=lifeos-release@localhost','commit','-m','fix(plugins): forward provider in Stop dispatch')
  metadata_path=n['PROFILE']/'plugins/.install-metadata.json';metadata=json.loads(metadata_path.read_text())
  metadata['lifeos-hook-bridge']['revision']=revision
  metadata_path.write_text(json.dumps(metadata,indent=2,sort_keys=True)+'\n')
  for unit in ['hermes-gateway.service','hermes-dashboard.service']:n['service'](unit,'start')
  time.sleep(5)
  result=n['verify'](record)
  carrier=n['run']([n['COMMAND'],'lifeos-probe','--run'],timeout=300)
  assert 'HermesCarrierProbe: HOLDS' in carrier,carrier
  print(carrier,flush=True)
  result.update(old_result)
  result.update(plugin_revision=revision,hermes_revision=n['git']('rev-parse','HEAD'),
                gateway_pid=n['run'](['systemctl','--user','show','hermes-gateway.service','-p','MainPID','--value']),
                carrier_probe=carrier,state='applied')
  n['save']('preflight.json',record)
  n['save']('result.json',result)
  n['save']('status.json',{'state':'applied'})
  (r/'correction.done').write_text('0\n')
  print(json.dumps(result,indent=2),flush=True)
 except BaseException as error:
  traceback.print_exc()
  for unit in n['UNITS']:n['service'](unit,'stop')
  n['_sync_tree'](n['BACKUP']/'hermes-before',n['HERMES'])
  n['git']('reset','--mixed',record['hermes_before'])
  n['git']('switch',record['hermes_branch_before'])
  n['_sync_tree'](n['BACKUP']/'profile-before/plugins/lifeos-hook-bridge',n['PLUGIN'])
  n['restore_snapshot'](n['BACKUP']/'native',n['PROFILE'],preserve_divergent=True)
  shutil.copy2(n['BACKUP']/'baseline-before.json',n['BASELINE'])
  shutil.copy2(n['BACKUP']/'profile-before/plugins/.install-metadata.json',n['PROFILE']/'plugins/.install-metadata.json')
  for unit in reversed(n['UNITS']):n['service'](unit,'start')
  n['save']('status.json',{'state':'rolled_back','error':str(error)[:500]})
  (r/'correction.done').write_text('1\n')
  raise
