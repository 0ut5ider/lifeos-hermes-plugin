# ABOUTME: Checks all restored network interfaces are removed before the mount and boot stages.
# ABOUTME: Executes exact local configuration guards with synthetic Proxmox responses only.
import argparse,ast,json,re
from pathlib import Path
p=Path(__file__).resolve().parents[3];r=Path(__file__).resolve().parent
parser=argparse.ArgumentParser();parser.add_argument('--before',action='store_true');parser.add_argument('--require-fixed',action='store_true');args=parser.parse_args()
s=r/'proxmox_daily_restore.before.py' if args.before else p/'docs/verification/2026-10-14-release-0.5.0/proxmox_daily_restore.py'
outer=next(n for n in ast.parse(s.read_text()).body if isinstance(n,ast.Try))
start=next(i for i,n in enumerate(outer.body) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='created' for t in n.targets))+1
end=next(i for i,n in enumerate(outer.body) if isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and n.value.func.id=='run' and len(n.value.args)>1 and isinstance(n.value.args[1],ast.Constant) and n.value.args[1].value=='mount')
code=compile(ast.Module(body=outer.body[start:end],type_ignores=[]),'<actual-preboot-network-isolation>','exec')
results=[]
for case in ['single-interface','two-interfaces','already-disconnected','stubborn-interface','raw-lxc-interface','privileged-guest']:
 lines=['hostname: lifeos-050-daily-recovery','onboot: 0','unprivileged: '+('0' if case=='privileged-guest' else '1')]
 if case!='already-disconnected':lines.append('net0: name=eth0,bridge=vmbr0')
 if case in ['two-interfaces','stubborn-interface']:lines.append('net1: name=eth1,bridge=vmbr1')
 if case=='raw-lxc-interface':lines.append('lxc.net.0.type: veth')
 calls=[]
 def run(argv,label,**options):
  calls.append({'label':label,'command':argv})
  if argv[1]=='config':return '\n'.join(lines)+'\n'
  if '--delete' in argv:
   key=argv[argv.index('--delete')+1]
   if not (case=='stubborn-interface' and key=='net1'):lines[:]=[x for x in lines if not x.startswith(key+':')]
  return ''
 error=None
 try:exec(code,{'run':run,'vmid':110,'re':re})
 except AssertionError:error='AssertionError'
 remaining=[x for x in lines if re.match(r'^(net\d+:|lxc\.net\.)',x)]
 should_refuse=case in ['stubborn-interface','raw-lxc-interface','privileged-guest']
 correct=(error is not None) if should_refuse else (error is None and not remaining)
 results.append({'case':case,'status':'PASS' if correct else 'FAIL','refused':error is not None,'remaining_interfaces':remaining,'calls':calls,'remote_calls':False,'guest_booted':False})
report={'status':'PASS' if all(x['status']=='PASS' for x in results) else 'FAIL','cases':results}
label='before' if args.before else 'after';(r/('network-isolation-'+label+'.json')).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if args.require_fixed:assert report['status']=='PASS'
