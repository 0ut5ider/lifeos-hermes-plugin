# ABOUTME: Reproduces browser poll authentication loss and public stock provenance guard omissions.
# ABOUTME: Uses local function statements and safe metadata only, without browser or guest access.
import ast,copy,json
from pathlib import Path
from types import SimpleNamespace

project=Path(__file__).resolve().parents[3]
source=project/'docs/verification/2026-10-14-release-0.5.0'
out=Path(__file__).resolve().parent
ui_nodes=ast.parse((source/'public_ui_replay.py').read_text()).body
wait=next(node for node in ui_nodes if isinstance(node,ast.FunctionDef) and node.name=='wait_applied')
results=[]
class Clock:
    reads=0
    @classmethod
    def monotonic(cls):
        cls.reads+=1
        return 0 if cls.reads==1 else 1201
    @staticmethod
    def sleep(seconds):raise AssertionError('The expired poll must not sleep')
calls=[]
def request_get(url,**options):
    calls.append({'action':'request','url':url})
    return SimpleNamespace(status=401)
page=SimpleNamespace(request=SimpleNamespace(get=request_get))
namespace={'time':Clock,'origin':'http://local-negative-test','report':{'operation_state':'queued-apply'},'save':lambda:None}
exec(compile(ast.Module(body=[wait],type_ignores=[]),'<actual-browser-poll>','exec'),namespace)
error=None
try:namespace['wait_applied'](page,'a'*32,{'queued-apply','applying'},'applied')
except AssertionError as failure:error=str(failure)
assert error=='The native operation status does not return'
assert namespace['report']['operation_state']=='queued-apply'
results.append({'case':'expired-owner-session-after-restart','http_status':401,
    'reported_operation_state':namespace['report']['operation_state'],'reauthentication_attempted':False,
    'last_http_status_recorded':False,'failure':error,'browser_used':False,'remote_commands_run':False})

nodes=ast.parse((source/'verify_public_installation.py').read_text()).body
baseline_asserts=[node for node in nodes if isinstance(node,ast.Assert) and "baseline['" in ast.unparse(node) and 'model_selection_sha256' not in ast.unparse(node)]
actual=json.loads((source/'public-stock-baseline.json').read_bytes())
for name,key,value in [('wrong-prior-source-archive','stock_source_sha256','0'*64),('wrong-prior-hermes-commit','hermes_commit','0'*40)]:
    baseline=copy.deepcopy(actual);baseline[key]=value
    exec(compile(ast.Module(body=baseline_asserts,type_ignores=[]),'<actual-public-baseline-guards>','exec'),{'baseline':baseline})
    results.append({'case':name,'metadata_change_rejected':False,'prior_source_proof_read':False,
                    'guest_acceptance_receipt_written':False,'scope':'Actual existing stock baseline assertions only; all other baseline values stay unchanged.'})
report={'cases':len(results),'results':results,'remote_commands_run':False,'credentials_read':False,'guest_receipt_written':False}
(out/'deployment-gap-results.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
