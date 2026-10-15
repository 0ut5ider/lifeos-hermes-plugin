# ABOUTME: Checks that development orchestration refuses invalid checkpoint input before mutation phases.
# ABOUTME: Uses local control-flow fault boundaries and records no completion receipts or guest commands.
import ast
import json
from pathlib import Path
import sys
from types import SimpleNamespace

project=Path(__file__).resolve().parents[3]
source=project/'docs/verification/2026-10-14-release-0.5.0'
text=(source/'advance_development.py').read_text()
node=next(item for item in ast.parse(text).body if isinstance(item,ast.Try))
results=[]
for case in ('failed-checkpoint-marker','wait-expired','wrong-checkpoint-status','wrong-checkpoint-guest','services-not-resumed','daily-changed','foreign-backup'):
    calls=[]
    writes=[]
    phases=[]
    class Output:
        def __truediv__(self,name):return self
        def write_text(self,value):writes.append(value)
    class Clock:
        count=0
        @classmethod
        def monotonic(cls):
            cls.count+=1
            return 0 if cls.count==1 else 7201
        @staticmethod
        def sleep(seconds):raise AssertionError('No actual sleep is permitted in this refusal probe')
    def remote_poll(command,**options):
        calls.append(command)
        return SimpleNamespace(returncode=1 if case=='wait-expired' else 0,stdout='1\n' if case=='failed-checkpoint-marker' else '0\n')
    def run(command,label,**options):
        phases.append(label)
        assert label=='protected-checkpoint', 'A mutation phase is reached by rejected checkpoint data'
        # Negative inputs only. No accepted checkpoint or completion receipt is written.
        checkpoint={'status':'PASS','guest':101,'services_resumed':True,'daily_guest_changed':False,
                    'protected_archive':'PBS-01:backup/ct/101/negative-local-test'}
        key,value={'wrong-checkpoint-status':('status','FAIL'),'wrong-checkpoint-guest':('guest',253),
            'services-not-resumed':('services_resumed',False),'daily-changed':('daily_guest_changed',True),
            'foreign-backup':('protected_archive','local:backup/ct/101/negative-local-test')}[case]
        checkpoint[key]=value
        return json.dumps(checkpoint)
    namespace={'subprocess':SimpleNamespace(run=remote_poll),'time':Clock,'run':run,'json':json,'out':Output()}
    caught=False
    try:
        exec(compile(ast.Module(body=[node],type_ignores=[]),'<advance-refusal>','exec'),namespace)
    except AssertionError:
        caught=True
    assert caught and writes==['1\n']
    assert all(label=='protected-checkpoint' for label in phases)
    assert all(command[0]=='ssh' and command[3]=='root@192.168.8.101' for command in calls)
    results.append({'case':case,'status':'PASS','mutation_phase_reached':False,'checkpoint_read_only':True,
                    'failure_marker_in_memory':True,'completion_receipt_written':False,
                    'remote_commands_run':False})
report={'status':'PASS','cases':len(results),'results':results,
        'limit':'Actual outer try/except control flow with negative local inputs only. No successful checkpoint is supplied to the operator.'}
Path(__file__).with_name('advance-refusal-results.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
