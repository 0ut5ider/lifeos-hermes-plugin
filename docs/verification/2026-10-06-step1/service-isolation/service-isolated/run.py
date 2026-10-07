# ABOUTME: Measures concurrent disposable service controls before changing admission logic.
# ABOUTME: Retains service manager properties, process identity, test output, and completion.
from pathlib import Path
import concurrent.futures,json,os,subprocess,sys
root=Path(__file__).resolve().parent
namespace={}
exec(Path('/home/outsider/.cache/lifeos-hook-completion-20261006/run-full.py').read_text().split('commands=')[0],namespace)
env=namespace['env'];repo=namespace['repo'];env['TMPDIR']='/home/outsider/.cache/lhc6'
Path(env['TMPDIR']).mkdir(exist_ok=True)
worker=root/'worker.py'
sets=[['test_profile_services'],['test_ownership_setup.OwnershipSetupTests.test_originally_inactive_service_stays_inactive_after_setup_and_return']*5,
 ['test_ownership_setup_host.OwnershipSetupHostTests.test_restarted_profile_uses_native_tools_and_returns_to_preserved_hermes_memory']*5]
commands=[]
def run(index):
 command=[sys.executable,str(worker),str(root/f'{index}.json'),*sets[index]]
 commands.append(command)
 with (root/f'{index}.log').open('w') as stream:
  result=subprocess.run(command,cwd=repo,env=env,stdout=stream,stderr=subprocess.STDOUT)
 (root/f'{index}.done').write_text(str(result.returncode)+'\n')
 return result.returncode
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:results=list(pool.map(run,range(3)))
(root/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
(root/'run.done').write_text('0\n' if results==[0,0,0] else '1\n')
