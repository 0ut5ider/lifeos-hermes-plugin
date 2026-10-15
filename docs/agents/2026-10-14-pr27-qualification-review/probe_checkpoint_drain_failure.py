# ABOUTME: Checks checkpoint cleanup control flow after a simulated partial service drain failure.
# ABOUTME: Executes the pinned operator try/finally with no guest calls or output receipt writes.
import ast
import json
from pathlib import Path
import subprocess
import time

project=Path(__file__).resolve().parents[3]
source=project/'docs/verification/2026-10-14-release-0.5.0'
code=subprocess.check_output(['git','show','94ea72dd52a84425bf39f1e482ba64aaddb0c03b:docs/verification/2026-10-14-release-0.5.0/protect_development.py'],cwd=project,text=True)
node=next(item for item in ast.parse(code).body if isinstance(item,ast.Try))
calls=[]
writes=[]
class ReceiptView:
    def __init__(self,name='root'):
        self.name=name
    def __truediv__(self,name):
        return ReceiptView(name)
    @property
    def parent(self):
        return self
    def exists(self):
        return (source/'bound-whole-guest-process.done').exists()
    def read_text(self):
        name='bound-whole-guest-process.done' if self.name.endswith('process.done') else 'bound-whole-guest-recovery.json'
        return (source/name).read_text()
    def read_bytes(self):
        return self.read_text().encode()
    def write_text(self,value):
        writes.append({'name':self.name,'text':value})

def drain_failure(action,label):
    calls.append(label)
    if label=='drain-development':
        raise RuntimeError('Injected failure after partial drain')

namespace={'root':ReceiptView(),'out':ReceiptView(),'source':drain_failure,'run':None,
           'time':time,'json':json,'result':1,'drained':False}
try:
    exec(compile(ast.Module(body=[node],type_ignores=[]),'<pinned-checkpoint-try>','exec'),namespace)
except RuntimeError as error:
    assert str(error)=='Injected failure after partial drain'
else:
    raise AssertionError('Fault did not execute')
report={'case':'partial-drain-failure','operator_commit':'94ea72dd52a84425bf39f1e482ba64aaddb0c03b',
 'calls':calls,'recovery_attempted':'recover-development-services' in calls,
 'observed_drained_flag':namespace['drained'],'failure_marker_in_memory':writes,
 'remote_commands_run':False,'completion_receipt_written':False,
 'limit':'This probes operator control flow. It does not simulate a successful backup or exercise real services.'}
Path(__file__).with_name('checkpoint-drain-failure.json').write_text(json.dumps(report,indent=2)+'\n')
assert not report['recovery_attempted'] and report['observed_drained_flag'] is False
print(json.dumps(report,indent=2))
