# ABOUTME: Validates the actual restored-verifier command against its actual argument parser.
# ABOUTME: Extracts only parser and command expressions without guest commands or private inputs.
import argparse,ast,contextlib,io,json,os
from pathlib import Path
p=Path(__file__).resolve().parents[3];s=p/'docs/verification/2026-10-14-release-0.5.0';r=Path(__file__).resolve().parent
import sys
use_snapshot='--before' in sys.argv
operator=r/'proxmox_daily_restore.before.py' if use_snapshot else s/'proxmox_daily_restore.py'
verifier=r/'verify_daily_restored_programs.before.py' if use_snapshot else s/'verify_daily_restored_programs.py'
body=ast.parse(verifier.read_text()).body
parser_stmt=next(n for n in body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='parser' for t in n.targets))
adds=[n for n in body if isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and ast.unparse(n.value.func)=='parser.add_argument']
ns={'argparse':argparse};exec(compile(ast.Module(body=[parser_stmt]+adds,type_ignores=[]),'<actual-verifier-parser>','exec'),ns)
command=next(n for n in ast.walk(ast.parse(operator.read_text())) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='run' and len(n.args)>1 and isinstance(n.args[1],ast.Constant) and n.args[1].value=='verify-stable-programs')
argv=eval(compile(ast.Expression(command.args[0]),'<actual-restored-command>','eval'),{'str':str,'vmid':110,'python':'synthetic-python','os':type('Env',(),{'environ':{'LIFEOS_STABLE_OPERATION':'a'*32}})})
flags=argv[argv.index('/home/lifeos-hermes/releases/qualification-0.5.0/verify_daily_restored_programs.py')+1:]
error=io.StringIO();parsed=None;exitcode=None
with contextlib.redirect_stderr(error):
 try:parsed=ns['parser'].parse_args(flags)
 except SystemExit as exc:exitcode=exc.code
result={'status':'PASS' if parsed is not None and parsed.action=='verify' and parsed.operation=='a'*32 else 'FAIL','actual_arguments':flags,'argparse_exit':exitcode,'stderr':error.getvalue(),'remote_calls':False}
label='before' if use_snapshot else 'after';(r/('restore-invocation-'+label+'.json')).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if '--require-fixed' in sys.argv:assert result['status']=='PASS'
