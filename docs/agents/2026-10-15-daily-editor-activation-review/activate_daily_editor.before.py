# ABOUTME: Enables the governed Pulse core editor after exact daily promotion and owner source admission.
# ABOUTME: Preserves all other user configuration and verifies owner, anonymous, and sealed HTTP boundaries.
import hashlib,json,os,re,subprocess,tempfile,time,tomllib
from pathlib import Path

def enable_editor(content,expected_digest):
 assert hashlib.sha256(content).hexdigest()==expected_digest,'The user configuration changes before activation'
 before=tomllib.loads(content.decode())
 assert before['modules']['hermes'] is False
 sections=list(re.finditer(rb'(?m)^\[[^\r\n]+\][ \t]*(?:#[^\r\n]*)?\r?$',content))
 chosen=[(i,m) for i,m in enumerate(sections) if m.group().strip()==b'[modules]']
 assert len(chosen)==1
 i,m=chosen[0];end=sections[i+1].start() if i+1<len(sections) else len(content)
 section,count=re.subn(rb'(?m)^(hermes[ \t]*=[ \t]*)false([ \t]*(?:#[^\r\n]*)?\r?$)',rb'\g<1>true\2',content[m.end():end])
 assert count==1
 selected=content[:m.end()]+section+content[end:]
 expected=json.loads(json.dumps(before));expected['modules']['hermes']=True
 assert tomllib.loads(selected.decode())==expected
 return selected

def main():
 import httpx
 os.umask(0o077)
 home=Path('/home/lifeos-hermes');profile=home/'.hermes';stage=home/'releases/qualification-0.5.0'
 result=stage/'daily-editor-activation.json';assert not result.exists()
 verified=json.loads((stage/'daily-verification.json').read_bytes())
 admission=json.loads((stage/'daily-native-skill-review.json').read_bytes())
 assert verified['status']=='PASS' and verified['server']=='daily'
 assert admission['status']=='PASS' and admission['package_skill_digests_verified']==56 and admission['launcher_present'] is True
 operation=verified['operation'];assert admission['operation']==operation
 job=profile/'.lifeos-releases'/operation;request=json.loads((job/'request.json').read_bytes())
 assert request['version']=='0.5.0' and request['commit']=='04efe633296eb2b1a1d95561ca6d3e9516cd47dc'
 assert request['package_sha256']=='a6dd0e11b8fb1b5ae30345be20c955db02728839f7bc907f60a70944ad392813'
 os.environ.update(HOME=str(home),HERMES_HOME=str(profile),XDG_RUNTIME_DIR='/run/user/1000',
  DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/1000/bus',PATH=str(home/'.local/bin')+':/usr/bin:/bin')
 active=json.loads(subprocess.run([str(home/'.local/bin/hermes'),'lifeos-version'],capture_output=True,text=True,check=True,timeout=90).stdout)['active']
 assert active['verification']=='verified' and all(active[k]==request[k] for k in ('version','commit','package_sha256'))
 root=Path(json.loads((profile/'lifeos-memory.json').read_bytes())['root'])
 target=root/'LIFEOS/USER/CONFIG/PULSE.user.toml'
 assert target.is_file() and not target.is_symlink() and target.stat().st_uid==os.getuid()
 before=target.read_bytes();digest='566d9071a57fea08f5b5abf40bf6622bdc2009193fd29f652d9a63c53ca87003'
 selected=enable_editor(before,digest)
 morning=[row for row in tomllib.loads(before.decode())['job'] if row['name']=='life-morning-brief']
 assert len(morning)==1 and morning[0]['schedule']=='0 7 * * *' and morning[0]['enabled'] is True
 credentials=json.loads((home/'install-input/dashboard-access.json').read_bytes())
 with httpx.Client(base_url='http://127.0.0.1:18819',timeout=180,trust_env=False) as client:
  assert client.post('/auth/password-login',json={'provider':'basic',**credentials}).status_code==200
  me=client.get('/api/auth/me').json();assert me['provider']=='basic' and me['user_id']=='adrian'
  remount=client.post('/api/plugins/lifeos-hook-bridge/memory/remount',headers={'Origin':'http://127.0.0.1:18819'})
  assert remount.status_code==200
  mount=remount.json();assert mount['ok'] is True and mount['exitCode']==0 and mount['mount']['state']=='committed'
  state=json.loads(subprocess.run([str(home/'.local/bin/hermes'),'lifeos-release','status'],capture_output=True,text=True,check=True,timeout=90).stdout)
  op=next(row for row in state['operations'] if row['identifier']==operation)
  assert op['restore_available'] is False and op['recover_available'] is False,'The later owner mount must protect against prior-program restoration'
  backup=stage/'pulse-user-before-core-editor.private.toml';assert not backup.exists()
  with backup.open('xb') as output:output.write(before)
  backup.chmod(0o600)
  assert target.read_bytes()==before
  subprocess.run(['systemctl','--user','stop','com.lifeos.pulse.service'],check=True,capture_output=True)
  try:
   assert target.read_bytes()==before
   descriptor,name=tempfile.mkstemp(prefix='.pulse-editor-',dir=target.parent)
   try:
    with os.fdopen(descriptor,'wb') as output:
     os.fchmod(output.fileno(),0o600);output.write(selected);output.flush();os.fsync(output.fileno())
    os.replace(name,target)
   finally:
    if os.path.exists(name):os.unlink(name)
  finally:
   subprocess.run(['systemctl','--user','start','com.lifeos.pulse.service'],check=True,capture_output=True)
  subprocess.run(['systemctl','--user','restart','hermes-gateway.service'],check=True,capture_output=True)
  assert client.post('/auth/password-login',json={'provider':'basic',**credentials}).status_code==200
  pulse='http://127.0.0.1:18837';deadline=time.monotonic()+90
  while True:
   try:
    owner=client.get(pulse+'/api/hermes')
    if owner.status_code==200:break
   except httpx.TransportError:pass
   assert time.monotonic()<deadline,'The governed daily editor does not become ready'
   time.sleep(0.5)
  assert len(owner.json()['files'])==24 and owner.headers['cache-control']=='no-store'
  anonymous=httpx.get(pulse+'/api/hermes',timeout=30,trust_env=False);assert anonymous.status_code==401
  sealed=client.get(pulse+'/api/hermes/file/hermes-env');assert sealed.status_code==403
  assert target.read_bytes()==selected and target.stat().st_mode&0o777==0o600
  report={'status':'PASS','server':'daily','operation':operation,'program_commit':request['commit'],
   'archive_sha256':request['package_sha256'],'actual_owner_remount_status':200,'actual_owner_remount_state':'committed',
   'prior_release_restore_available':False,'owner_metadata_status':200,'declared_files':24,
   'anonymous_native_pulse_status':401,'sealed_read_status':403,'cache_control':'no-store',
   'user_configuration_before_sha256':digest,'user_configuration_after_sha256':hashlib.sha256(selected).hexdigest(),
   'only_modules_hermes_changed':True,'normal_morning_schedule':'0 7 * * *','manual_job_run':False,
   'private_previous_configuration_retained':True,'personal_file_content_requested':False,'personal_files_edited':False,
   'gateway_restarted_after_remount':True,'recovery_scope':'Protected complete guest checkpoint. The later owner mount blocks the earlier release program restore.'}
  result.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))

if __name__=='__main__':main()
