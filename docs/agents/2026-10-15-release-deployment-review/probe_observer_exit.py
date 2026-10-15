# ABOUTME: Checks the observer-only success exit passes through the actual outer exception handler.
# ABOUTME: Executes only exit and error-handler statements with in-memory receipt writes.
import ast,json,sys
from pathlib import Path

project=Path(__file__).resolve().parents[3]
source=project/'docs/verification/2026-10-14-release-0.5.0/public_ui_replay.py'
body=ast.parse(source.read_text()).body
outer=next(node for node in body if isinstance(node,ast.Try))
observe=next(node for node in ast.walk(outer) if isinstance(node,ast.If) and isinstance(node.test,ast.Name) and node.test.id=='observe_only')
exit_node=next(node for node in observe.body if isinstance(node,ast.Expr) and isinstance(node.value,ast.Call) and ast.unparse(node.value.func)=='sys.exit')
probe=ast.Try(body=[exit_node],handlers=outer.handlers,orelse=[],finalbody=[])
writes=[];snapshots=[]
class Output:
 def __truediv__(self,name):return self
 def write_text(self,value):writes.append(value)
report={'status':'UI_APPLIED'}
namespace={'sys':sys,'report':report,'save':lambda:snapshots.append(dict(report)),'out':Output()}
code=ast.fix_missing_locations(ast.Module(body=[probe],type_ignores=[]))
caught=None
try:exec(compile(code,'<actual-observer-exit-handler>','exec'),namespace)
except SystemExit as error:caught=error.code
result={'case':'successful-observer-exit','process_exit_code':caught,'receipt_status_after_exit':report['status'],
        'completion_markers_in_memory':writes,'error_type':report.get('error_type'),
        'browser_used':False,'remote_commands_run':False,'guest_completion_receipt_written':False}
Path(__file__).with_name('observer-exit-result.json').write_text(json.dumps(result,indent=2)+'\n')
assert caught==0 and report['status']=='FAIL' and writes==['1\n']
print(json.dumps(result,indent=2))
