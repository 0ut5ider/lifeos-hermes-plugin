# ABOUTME: Checks Pulse stop and cleanup failures against the exact daily editor control flow.
# ABOUTME: Uses local failure boundaries without accessing configuration, credentials, or remote services.
import argparse,ast,json
from pathlib import Path
from types import SimpleNamespace
parser=argparse.ArgumentParser();parser.add_argument('--source');parser.add_argument('--report',default='editor-cleanup-before.json');parser.add_argument('--require-fixed',action='store_true');args=parser.parse_args()
p=Path(__file__).resolve().parents[3]
s=Path(args.source) if args.source else p/'docs/verification/2026-10-14-release-0.5.0/activate_daily_editor.py'
tree=ast.parse(s.read_text());main=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
context=next(n for n in main.body if isinstance(n,ast.With))
body=context.body
# Run the actual stop call and associated cleanup. A future guard may enclose both.
stop_index=next((i for i,n in enumerate(body) if isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and ast.unparse(n).startswith("subprocess.run(['systemctl', '--user', 'stop'")),None)
if stop_index is not None:chosen=body[stop_index:stop_index+2]
else:
 chosen=[n for n in body if isinstance(n,ast.Try) and "'stop', 'com.lifeos.pulse.service'" in ast.unparse(n)]
 assert len(chosen)==1
class OriginalFailure(RuntimeError):pass
class CleanupFailure(RuntimeError):pass
results=[]
for label in ['partial-stop-failure','write-failure-start-succeeds','write-failure-start-fails']:
 calls=[]
 def run(argv,**kw):
  action=argv[2];calls.append(action)
  if action=='stop' and label=='partial-stop-failure':raise OriginalFailure('Partial stop failure')
  if action=='start' and label=='write-failure-start-fails':raise CleanupFailure('Cleanup also fails')
 def mkstemp(**kw):raise OriginalFailure('Configuration publication failure')
 ns={'subprocess':SimpleNamespace(run=run),'target':SimpleNamespace(read_bytes=lambda:b'original',parent=Path('/synthetic-unused')),'before':b'original','tempfile':SimpleNamespace(mkstemp=mkstemp),'sys':__import__('sys')}
 error=None
 try:exec(compile(ast.Module(body=chosen,type_ignores=[]),'<actual-editor-cleanup>','exec'),ns)
 except BaseException as exc:error=exc
 expected='start' in calls and isinstance(error,OriginalFailure)
 results.append({'case':label,'calls':calls,'error_type':type(error).__name__,'error':str(error),'expected_cleanup_and_original_failure':expected,'notes':getattr(error,'__notes__',[]),'remote_calls':False,'config_read':False,'file_write':False})
report={'status':'PASS' if all(x['expected_cleanup_and_original_failure'] for x in results) else 'FAIL','source':str(s),'cases':results}
Path(__file__).with_name(args.report).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if args.require_fixed:assert report['status']=='PASS'
