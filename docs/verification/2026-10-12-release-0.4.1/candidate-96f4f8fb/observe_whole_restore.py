# ABOUTME: Reports safe backup and restore task progress from the authorized Proxmox controller.
# ABOUTME: Exports numeric progress and release metadata without backup contents or task narration.
import subprocess,json
code=r'''from pathlib import Path
import subprocess,json,re,datetime
folder=Path('/root/lifeos-release-0.4.1');out=folder/'history-restore';value={'time':datetime.datetime.now(datetime.timezone.utc).isoformat()}
for name in ['history-restore.done']:
 p=folder/name
 if p.exists():value[name]=p.read_text().strip()
for name in ['process.done']:
 p=out/name
 if p.exists():value[name]=p.read_text().strip()
if (out/'operations.json').exists():value['operations']=json.loads((out/'operations.json').read_bytes())[-3:]
r=subprocess.run(['pvesh','get','/nodes/pve-tr1950x/tasks','--source','active','--output-format','json'],capture_output=True,text=True,timeout=30)
value['active_task_query_exit']=r.returncode
value['active_tasks']=[]
if r.returncode==0:
 for row in json.loads(r.stdout):
  if (row.get('type'),row.get('id')) not in [('vzdump','101'),('vzrestore','110')]:continue
  task={key:row[key] for key in ('type','id','upid','starttime') if key in row}
  log=subprocess.run(['pvesh','get','/nodes/pve-tr1950x/tasks/'+row['upid']+'/log','--start','0','--limit','500','--output-format','json'],capture_output=True,text=True,timeout=30)
  task['log_query_exit']=log.returncode
  if log.returncode==0:
   entries=json.loads(log.stdout)
   progress=[float(match[1]) for entry in entries if (match:=re.search(r'(\d+(?:\.\d+)?)%',entry.get('t','')))]
   if progress:task['last_percent']=progress[-1]
   metrics=[{'action':match[1],'amount':float(match[2]),'unit':match[3]} for entry in entries
    for match in re.finditer(r'(processed|uploaded|downloaded)\s+(\d+(?:\.\d+)?)\s*(TiB|GiB|MiB|KiB|GB|MB|bytes)',entry.get('t',''))]
   if metrics:task['last_numeric_progress']=metrics[-2:]
  value['active_tasks'].append(task)
print(json.dumps(value))
'''
r=subprocess.run(['ssh','root@192.168.8.101','python3','-B','-'],input=code,text=True,capture_output=True,check=True,timeout=60)
print(json.dumps(json.loads(r.stdout),indent=2))
