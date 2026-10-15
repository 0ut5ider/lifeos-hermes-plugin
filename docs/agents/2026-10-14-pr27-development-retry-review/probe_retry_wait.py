# ABOUTME: Checks actual development wait gates refuse failure before preservation and memory turns.
# ABOUTME: Uses only negative local metadata and writes no completion receipt or guest state.
import ast,json
from pathlib import Path
from types import SimpleNamespace

project=Path(__file__).resolve().parents[3]
source=project/'docs/verification/2026-10-14-release-0.5.0'
code=(source/'verify_development_apply.py').read_text()
node=next(item for item in ast.parse(code).body if isinstance(item,ast.Try))
identifier='4eac8d1b398e47138d80f8b67b6df596'
results=[]
for case in ('wrong-identifier','rejected','rolled_back','recovery_required','unknown','expired-ready','expired-applying'):
    calls=[];writes=[]
    class Output:
        def __truediv__(self,name):return self
        def write_text(self,value):writes.append(value)
    class Clock:
        count=0
        @classmethod
        def monotonic(cls):
            cls.count+=1
            return 0 if cls.count==1 else 3601
        @staticmethod
        def sleep(seconds):raise AssertionError('A bounded refusal must precede any sleep')
    def run(command,label,**options):
        calls.append({'command':command,'label':label})
        assert label=='selected-operation-status', 'An unaccepted operation reaches a verification or memory phase'
        state={'wrong-identifier':'applying','expired-ready':'ready','expired-applying':'applying'}.get(case,case)
        return json.dumps({'identifier':'0'*32 if case=='wrong-identifier' else identifier,'state':state})
    namespace={'json':json,'run':run,'time':Clock,'identifier':identifier,
        'remote':'root@192.168.8.252','job':'/home/lifeos-hermes/.hermes/.lifeos-releases/'+identifier,'out':Output()}
    rejected=False
    try:exec(compile(ast.Module(body=[node],type_ignores=[]),'<actual-development-wait>','exec'),namespace)
    except AssertionError:rejected=True
    assert rejected and writes==['1\n'] and len(calls)==1
    assert calls[0]['command'][3]=='root@192.168.8.252'
    results.append({'case':case,'status':'PASS','verification_phase_reached':False,'memory_phase_reached':False,
        'remote_commands_run':False,'completion_receipt_written':False})
report={'status':'PASS','cases':len(results),'results':results}
Path(__file__).with_name('development-wait-results.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
