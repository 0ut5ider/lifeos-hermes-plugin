# ABOUTME: Checks a failed cleanup command is recorded before the original command error propagates.
# ABOUTME: Executes the actual nested run helper against a local completed-process boundary only.
import ast,json,subprocess
from pathlib import Path
from types import SimpleNamespace
r=Path(__file__).resolve().parent;p=r.parents[2];s=p/'docs/verification/2026-10-14-release-0.5.0/cleanup_release_guests.py'
main=next(n for n in ast.parse(s.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='main');run=next(n for n in main.body if isinstance(n,ast.FunctionDef) and n.name=='run')
command=['synthetic-cleanup-command'];writes=[];operations=[]
class Ledger:
 def with_suffix(self,suffix):return self
 def write_text(self,text):writes.append(json.loads(text))
ns={'subprocess':SimpleNamespace(run=lambda *a,**k:subprocess.CompletedProcess(command,1,'','Synthetic refusal')),'operations':operations,'args':SimpleNamespace(out=Ledger()),'json':json}
exec(compile(ast.Module(body=[run],type_ignores=[]),'<actual-cleanup-command-helper>','exec'),ns)
error=None
try:ns['run'](command)
except subprocess.CalledProcessError as exc:error=exc
assert error is not None and error.returncode==1 and writes==[[{'command':command,'exit_code':1}]] and operations==writes[0]
report={'status':'PASS','recorded_nonzero_exit_before_error':True,'original_error_type':type(error).__name__,'original_returncode':error.returncode,'remote_calls':False,'actual_files_written':False}
(r/'failure-ledger-control.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
