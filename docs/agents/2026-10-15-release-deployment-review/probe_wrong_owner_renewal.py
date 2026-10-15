# ABOUTME: Checks an invalid owner identity cannot be swallowed by the generic polling retry.
# ABOUTME: Runs actual owner renewal and polling helpers with local HTTP boundaries only.
import argparse,ast,json
from pathlib import Path
from types import SimpleNamespace

parser=argparse.ArgumentParser();parser.add_argument('--report',default='wrong-owner-renewal-before.json');parser.add_argument('--expect-refusal',action='store_true');args=parser.parse_args()
project=Path(__file__).resolve().parents[3]
source=project/'docs/verification/2026-10-14-release-0.5.0/public_ui_replay.py'
nodes=ast.parse(source.read_text()).body
functions=[node for node in nodes if isinstance(node,ast.FunctionDef) and node.name in {'renew_owner','wait_applied'}]
state={'renewed':False};calls=[];saved=[]
class Clock:
    @staticmethod
    def monotonic():return 0
    @staticmethod
    def sleep(seconds):calls.append({'action':'bounded-retry'})
def goto(url):state['renewed']=True;calls.append({'action':'owner-login-navigation'})
def get(url,**options):
    calls.append({'action':'get','path':url.rsplit('/',1)[-1]})
    if url.endswith('/api/auth/me'):
        return SimpleNamespace(status=200,json=lambda:{'provider':'basic','user_id':'wrong-owner'})
    return SimpleNamespace(status=200 if state['renewed'] else 401,
        json=lambda:{'operations':[{'identifier':'a'*32,'state':'applied'}]})
page=SimpleNamespace(goto=goto,request=SimpleNamespace(get=get))
report={'operation_state':'queued-apply','authenticated_owner_verified':True}
namespace={'time':Clock,'origin':'http://local-owner-test','report':report,'save':lambda:saved.append(dict(report))}
exec(compile(ast.Module(body=functions,type_ignores=[]),'<actual-renewal-and-poll>','exec'),namespace)
returned=None;error=None
try:returned=namespace['wait_applied'](page,'a'*32,{'queued-apply','applying'},'applied')
except AssertionError as failure:error=str(failure)
result={'case':'wrong-owner-after-renewal','wrong_identity_refusal_swallowed':returned is not None,
        'returned_state':None if returned is None else returned['state'],'error':error,'calls':calls,
        'http_boundary_injected_only':True,'browser_used':False,'remote_commands_run':False,
        'guest_completion_receipt_written':False}
Path(__file__).with_name(args.report).write_text(json.dumps(result,indent=2)+'\n')
assert (returned is None) == args.expect_refusal
print(json.dumps(result,indent=2))
