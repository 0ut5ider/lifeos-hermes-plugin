# ABOUTME: Reads safe release states and actual systemd exit metadata on development.
# ABOUTME: Excludes command output, configuration contents, and personal records from the receipt.
import json,subprocess,sys
code='''from pathlib import Path
import json,os,subprocess,pwd
home=Path('/home/lifeos-hermes');owner=pwd.getpwnam('lifeos-hermes');identifier=IDENTIFIER
job=home/'.hermes/.lifeos-releases'/identifier;unit='lifeos-release-'+identifier+'.service'
value={'operation':identifier}
for label,name in [('status','status.json'),('program_transaction','program-snapshot/programs.json'),('worker_launch','worker-launch.json')]:
 p=job/name
 if p.exists():
  row=json.loads(p.read_bytes());value[label]=row.get('state') if label!='worker_launch' else {k:row[k] for k in ('kind','unit','pid') if k in row}
request=json.loads((job/'request.json').read_bytes());value['program_commit']=request['commit']
env=dict(os.environ,HOME=str(home),XDG_RUNTIME_DIR='/run/user/'+str(owner.pw_uid),DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/'+str(owner.pw_uid)+'/bus')
command=['/usr/sbin/runuser','-u','lifeos-hermes','--','systemctl','--user','show',unit,'-p','ActiveState','-p','SubState']
r=subprocess.run(command,env=env,capture_output=True,text=True,timeout=20);value['service']={line.split('=',1)[0]:line.split('=',1)[1] for line in r.stdout.splitlines() if '=' in line}
r=subprocess.run(['/usr/sbin/runuser','-u','lifeos-hermes','--','journalctl','--user','-o','json','--no-pager','USER_UNIT='+unit,'MESSAGE_ID=98e322203f7a4ed290d09fe03c09fe15'],env=env,capture_output=True,text=True,timeout=20)
rows=[json.loads(line) for line in r.stdout.splitlines() if line.startswith('{')]
value['journal_exits']=[{key:row[key] for key in ('__REALTIME_TIMESTAMP','MESSAGE_ID','EXIT_CODE','EXIT_STATUS','USER_UNIT') if key in row} for row in rows]
print(json.dumps(value))
'''.replace('IDENTIFIER',repr(sys.argv[1]))
r=subprocess.run(['ssh','root@192.168.8.252','python3','-B','-'],input=code,text=True,capture_output=True,check=True,timeout=45)
print(json.dumps(json.loads(r.stdout),indent=2))
