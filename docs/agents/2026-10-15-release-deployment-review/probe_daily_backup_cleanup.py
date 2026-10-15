# ABOUTME: Verifies both backup operators recover partial drain failures and preserve the first error.
# ABOUTME: Uses exact local try/finally code and fault boundaries without guest commands or receipt writes.
import ast
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import time

project=Path(__file__).resolve().parents[3]
source=project/'docs/verification/2026-10-14-release-0.5.0'
results=[]

for operator,drain,resume,recover,backup,guest in (
 ('protect_daily.py','drain-daily','resume-daily','recover-daily-services','backup-daily',102),
):
    code=(source/operator).read_text()
    node=next(item for item in ast.parse(code).body if isinstance(item,ast.Try))
    for failure_stage in ('pre-drain','drain','backup','resume'):
        for cleanup_fails in (False,True):
            if failure_stage=='pre-drain' and cleanup_fails:
                continue
            calls=[]
            writes=[]
            actions=[]
            failed_label={'drain':drain,'backup':backup,'resume':resume}.get(failure_stage)
            error_message='injected-'+failure_stage+'-failure'
            class ReceiptView:
                def __init__(self,name='root'): self.name=name
                def __truediv__(self,name): return ReceiptView(name)
                @property
                def parent(self): return self
                def exists(self):
                    if failure_stage=='pre-drain':raise RuntimeError(error_message)
                    return (source/'bound-whole-guest-process.done').exists()
                def read_text(self):
                    name='bound-whole-guest-process.done' if self.name.endswith('process.done') else 'bound-whole-guest-recovery.json'
                    return (source/name).read_text()
                def read_bytes(self): return self.read_text().encode()
                def write_text(self,value):writes.append((self.name,value))
            def selected_source(action,label):
                calls.append(label)
                actions.append({'label':label,'action':action})
                if label==failed_label:raise RuntimeError(error_message)
                if label==recover and cleanup_fails:raise RuntimeError('injected-cleanup-failure')
                return ''
            def run(arguments,label,**options):
                calls.append(label)
                if failure_stage=='pre-drain' and label=='inventory':raise RuntimeError(error_message)
                if label==failed_label:raise RuntimeError(error_message)
                if label=='inventory':return '[]'
                if label=='capture-program-artifacts':return (source/'source-program-artifact-capture.json').read_text()
                if label=='archives':return json.dumps([{'ctime':1,'volid':'PBS-01:backup/ct/'+str(guest)+'/2026-10-14T23:59:45Z'}])
                return ''
            namespace={'root':ReceiptView(),'out':ReceiptView(),'source':selected_source,'run':run,
                'time':time,'json':json,'sys':sys,'result':1,'recovery_required':False,'created':False,
                'args':SimpleNamespace(resume_backup=False),'vmid':110,
                'services_code':'ACTION','python':'synthetic-python',
                'os':SimpleNamespace(environ={'LIFEOS_STABLE_OPERATION':'2bef1668a01e499096f1b855a2d9eac7'})}
            caught=None
            try:
                exec(compile(ast.Module(body=[node],type_ignores=[]),'<backup-closure-'+operator+'>','exec'),namespace)
            except RuntimeError as error:
                caught=error
            expected_recovery=failure_stage!='pre-drain'
            assert caught is not None and str(caught)==error_message
            assert (recover in calls)==expected_recovery
            assert ('process.done','1\n') in writes
            if expected_recovery:
                action=next(row['action'] for row in actions if row['label']==recover)
                assert "s.resume() if s.status()['recovery_required'] else None" in action
            notes=getattr(caught,'__notes__',[])
            assert bool(notes)==(expected_recovery and cleanup_fails)
            results.append({'operator':operator,'failure_stage':failure_stage,'cleanup_fails':cleanup_fails,
                'status':'PASS','calls':calls,'original_error':str(caught),'notes':notes,
                'failure_marker_in_memory':True,'receipt_written':False,'remote_commands_run':False})
report={'status':'PASS','cases':len(results),'results':results,'control_flow_fault_injection_only':True}
Path(__file__).with_name('backup-cleanup-results.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
