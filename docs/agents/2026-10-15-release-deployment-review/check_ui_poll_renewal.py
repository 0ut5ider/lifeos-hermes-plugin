# ABOUTME: Checks browser polling renews an expired owner session and preserves the selected operation.
# ABOUTME: Executes the actual wait helper with local request boundaries and no browser or guest access.
import argparse,ast,copy,json
from pathlib import Path
from types import SimpleNamespace

parser=argparse.ArgumentParser();parser.add_argument('--report',default='ui-poll-renewal-controls.json');args=parser.parse_args()
project=Path(__file__).resolve().parents[3]
source=project/'docs/verification/2026-10-14-release-0.5.0'
nodes=ast.parse((source/'public_ui_replay.py').read_text()).body
wait=next(node for node in nodes if isinstance(node,ast.FunctionDef) and node.name=='wait_applied')
results=[]
for case in ('expired-owner-renewal','temporary-server-restart','terminal-operation-failure'):
    calls=[];snapshots=[];authenticated=False;polls=0
    class Clock:
        checks=0
        @classmethod
        def monotonic(cls):
            cls.checks+=1
            return 1201 if cls.checks>5 else 0
        @staticmethod
        def sleep(seconds):calls.append({'action':'bounded-retry'})
    def renew_owner(page):
        global authenticated
        calls.append({'action':'renew-owner'});authenticated=True
    def get(url,**options):
        global polls
        polls+=1;calls.append({'action':'get-operation','url':url})
        code=401 if case=='expired-owner-renewal' and not authenticated else 503 if case=='temporary-server-restart' and polls==1 else 200
        state='rejected' if case=='terminal-operation-failure' else 'applied'
        return SimpleNamespace(status=code,json=lambda:{'operations':[{'identifier':'a'*32,'state':state}]})
    report={'operation_state':'queued-apply'}
    namespace={'time':Clock,'origin':'http://local-negative-test','report':report,
        'save':lambda:snapshots.append(copy.deepcopy(report)),'renew_owner':renew_owner}
    exec(compile(ast.Module(body=[wait],type_ignores=[]),'<actual-public-ui-poll>','exec'),namespace)
    returned=None;failure=None
    try:returned=namespace['wait_applied'](SimpleNamespace(request=SimpleNamespace(get=get)),'a'*32,{'queued-apply','applying'},'applied')
    except AssertionError as error:failure=str(error)
    renewals=sum(row['action']=='renew-owner' for row in calls)
    if case=='expired-owner-renewal':
        correct=returned is not None and returned['state']=='applied' and renewals==1
    elif case=='temporary-server-restart':
        correct=returned is not None and returned['state']=='applied' and renewals==0
    else:
        correct=returned is None and failure is not None and renewals==0
    results.append({'case':case,'expected_result_verified':correct,'owner_renewals':renewals,
        'polls':polls,'failure':failure,'calls':calls,'saved_metadata':snapshots,
        'install_or_apply_request_sent':False,'browser_used':False})
report={'status':'PASS' if all(row['expected_result_verified'] for row in results) else 'FAIL',
        'cases':len(results),'results':results,'remote_commands_run':False,'guest_completion_receipt_written':False}
Path(__file__).with_name(args.report).write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2));assert report['status']=='PASS'
