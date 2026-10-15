# ABOUTME: Checks public fixture provisioning refuses occupied guests, addresses, and unsafe storage.
# ABOUTME: Exercises only negative local control paths without creating a guest or completion receipt.
import ast,json
from pathlib import Path
from types import SimpleNamespace

project=Path(__file__).resolve().parents[3]
source=project/'docs/verification/2026-10-14-release-0.5.0'
node=next(item for item in ast.parse((source/'provision_public_replay.py').read_text()).body if isinstance(item,ast.Try))
results=[]
for case in ('guest-occupied','address-responds','key-missing','storage-missing','storage-alias'):
 calls=[];writes=[]
 def run(command,**options):
  calls.append(command)
  assert command[0]=='pvesh', 'A mutation phase is reached'
  return json.dumps([{'vmid':113}] if case=='guest-occupied' else [])
 def ping(command,**options):
  calls.append(command)
  assert command[0]=='ping'
  return SimpleNamespace(returncode=0 if case=='address-responds' else 1)
 class FakePath:
  def __init__(self,name):self.name=name
  def is_file(self):return case!='key-missing'
  def is_dir(self):return case!='storage-missing'
  def is_symlink(self):return case=='storage-alias'
 class Output:
  def __truediv__(self,name):return self
  def write_text(self,value):writes.append(value)
 namespace={'json':json,'run':run,'subprocess':SimpleNamespace(run=ping),'Path':FakePath,'out':Output()}
 rejected=False
 try:exec(compile(ast.Module(body=[node],type_ignores=[]),'<public-provision-refusal>','exec'),namespace)
 except AssertionError:rejected=True
 assert rejected and writes==['1\n'] and not any(command[0]=='pct' for command in calls)
 results.append({'case':case,'status':'PASS','guest_creation_reached':False,'failure_marker_in_memory':True,'remote_commands_run':False})
report={'status':'PASS','cases':len(results),'results':results,'guest_created':False,'completion_receipt_written':False}
Path(__file__).with_name('public-refusal-results.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
