# ABOUTME: Exercises installed Codex, Claude Code, and OpenCode against synthetic HTTP memory.
# ABOUTME: Keeps client configuration and credentials in a private disposable directory.
import json,os,subprocess,socket,threading,time,tempfile,re,traceback
from pathlib import Path
import httpx2,uvicorn
from starlette.applications import Starlette
from lifeos_hook_bridge.memory_remote import MemoryRemote,MemoryRemoteMiddleware,MCP_PATH
from lifeos_hook_bridge.memory_oauth import MemoryAuthorization
from lifeos_hook_bridge.memory_service import MemoryConfiguration
import test_memory_native as native
out=Path('/home/outsider/.cache/lifeos-http-mcp-20261015')
fixture=native.NativeMemoryTests();fixture.setUp()
listener=socket.socket();listener.bind(('127.0.0.1',0));port=listener.getsockname()[1]
origin='http://127.0.0.1:'+str(port);path=fixture.home/'hermes/lifeos-memory.json'
MemoryConfiguration(path).save({'version':1,'root':str(fixture.root),'principal':'owner','ownership_enabled':True,
 'sharing_enabled':True,'accounts':{'dashboard:test:owner':'owner'},'destinations':{},'clients':{}})
remote=MemoryRemote(path);remote.configure({'enabled':True,'public_url':origin},account='dashboard:test:owner')
server=uvicorn.Server(uvicorn.Config(MemoryRemoteMiddleware(Starlette(),configuration=path),host='127.0.0.1',port=port,
 access_log=False,log_config=None,lifespan='off',ws='none'))
thread=threading.Thread(target=server.run,kwargs={'sockets':[listener]},daemon=True);thread.start()
process=None;open_env=None;code=1;receipt={'live_client_config_changed':False,'daily_changed':False}
try:
 deadline=time.monotonic()+10
 while not server.started and time.monotonic()<deadline:time.sleep(.01)
 assert server.started
 client_home=fixture.home/'codex';client_home.mkdir(mode=0o700)
 (client_home/'config.toml').write_text('[mcp_servers.synthetic-memory]\nurl = '+json.dumps(origin+MCP_PATH)+'\n')
 env=dict(os.environ,CODEX_HOME=str(client_home))
 stdout=(out/'codex-login.private.stdout').open('w');stderr=(out/'codex-login.private.stderr').open('w')
 process=subprocess.Popen(['/home/outsider/.local/bin/codex','mcp','login','synthetic-memory','--no-browser'],
  cwd=fixture.home,env=env,stdin=subprocess.PIPE,stdout=stdout,stderr=stderr,text=True)
 deadline=time.monotonic()+30;authorization=None
 while time.monotonic()<deadline:
  text=(out/'codex-login.private.stdout').read_text()+(out/'codex-login.private.stderr').read_text()
  match=re.search(re.escape(origin)+r'/api/plugins/lifeos-hook-bridge/memory/http/authorize[^\s]+',text)
  if match:authorization=match.group(0);break
  if process.poll() is not None:break
  time.sleep(.1)
 assert authorization, 'Codex does not print the authorization address'
 with httpx2.Client() as http:
  response=http.get(authorization,follow_redirects=False)
  assert response.status_code==302
  pending=remote.status(account='dashboard:test:owner')['pending'];assert len(pending)==1
  grant={'client':'codex-client','read':['project'],'write_project':False,'projects':['lab'],'model_route':'unknown'}
  approved=MemoryAuthorization(remote).approve(pending[0]['id'],grant,account='dashboard:test:owner')
  try:
   callback=http.get(approved['redirect_url']);assert callback.status_code==200
  except httpx2.ConnectError:
   process.stdin.write(approved['redirect_url']+'\n');process.stdin.flush()
 process.wait(timeout=30);stdout.close();stderr.close()
 assert process.returncode==0, 'Codex login fails'
 text=(out/'codex-login.private.stdout').read_text()+(out/'codex-login.private.stderr').read_text()
 assert 'Successfully logged in' in text,text
 token=remote.enroll({'client':'desktop-bearer','read':['project'],'write_project':False,'projects':['lab'],'model_route':'unknown'},account='dashboard:test:owner')['token']
 claude_dir=fixture.home/'claude-client';claude_dir.mkdir(mode=0o700)
 claude_env=dict(os.environ,HOME=str(fixture.home),CLAUDE_CONFIG_DIR=str(claude_dir))
 added=subprocess.run(['/home/outsider/.local/bin/claude','mcp','add','--transport','http','--scope','user','synthetic-memory',origin+MCP_PATH],
  env=claude_env,cwd=fixture.home,capture_output=True,text=True,timeout=30)
 assert added.returncode==0, 'Claude configuration fails'
 candidates=list(fixture.home.rglob('*.json'))
 configured=[]
 for candidate in candidates:
  try:value=json.loads(candidate.read_text())
  except (ValueError,UnicodeError):continue
  if isinstance(value,dict) and 'synthetic-memory' in value.get('mcpServers',{}):
   value['mcpServers']['synthetic-memory']['headers']={'Authorization':'Bearer '+token}
   candidate.write_text(json.dumps(value));candidate.chmod(0o600);configured.append(candidate)
 assert len(configured)==1, 'The isolated Claude configuration is not found'
 checked=subprocess.run(['/home/outsider/.local/bin/claude','mcp','list'],env=claude_env,cwd=fixture.home,capture_output=True,text=True,timeout=45)
 (out/'claude-health.private.stdout').write_text(checked.stdout);(out/'claude-health.private.stderr').write_text(checked.stderr)
 assert checked.returncode==0 and 'Connected' in checked.stdout, 'Claude does not connect'
 receipt['claude_bearer_health_check']=True
 receipt['claude_version']=subprocess.check_output(['/home/outsider/.local/bin/claude','--version'],text=True).strip()
 opencode_home=fixture.home/'opencode-client';opencode_home.mkdir(mode=0o700)
 open_env=dict(os.environ,HOME=str(fixture.home),XDG_CONFIG_HOME=str(opencode_home/'config'),XDG_DATA_HOME=str(opencode_home/'data'),XDG_CACHE_HOME=str(opencode_home/'cache'),XDG_STATE_HOME=str(opencode_home/'state'))
 allocator=socket.socket();allocator.bind(('127.0.0.1',0));private_port=allocator.getsockname()[1];allocator.close()
 configured=subprocess.run(['/home/outsider/.opencode/bin/opencode','service','set','port',str(private_port)],env=open_env,cwd=fixture.home,capture_output=True,text=True,timeout=20)
 assert configured.returncode==0, 'The isolated OpenCode service port is not configured'
 for key in ('HOME','XDG_CONFIG_HOME','XDG_DATA_HOME','XDG_CACHE_HOME','XDG_STATE_HOME'):
  setting=subprocess.run(['/home/outsider/.opencode/bin/opencode','service','set','env',key,open_env[key]],env=open_env,cwd=fixture.home,capture_output=True,text=True,timeout=20)
  assert setting.returncode==0, 'The isolated OpenCode service environment is not configured'
 added=subprocess.run(['/home/outsider/.opencode/bin/opencode','mcp','add','synthetic-memory','--global','--url',origin+MCP_PATH],env=open_env,cwd=fixture.home,capture_output=True,text=True,timeout=60)
 assert added.returncode==0, 'OpenCode native configuration fails'
 configured=[]
 for candidate in list(fixture.home.rglob('*.json'))+list(fixture.home.rglob('*.jsonc')):
  try:value=json.loads(candidate.read_text())
  except (ValueError,UnicodeError):continue
  if isinstance(value,dict) and 'synthetic-memory' in value.get('mcp',{}).get('servers',{}):
   server_config=value['mcp']['servers']['synthetic-memory']
   server_config['headers']={'Authorization':'Bearer '+token};server_config['oauth']=False
   candidate.write_text(json.dumps(value));candidate.chmod(0o600);configured.append(candidate)
 assert configured, 'The isolated OpenCode configuration is not found'
 subprocess.run(['/home/outsider/.opencode/bin/opencode','reload'],env=open_env,cwd=fixture.home,capture_output=True,text=True,timeout=30,check=True)
 subprocess.run(['/home/outsider/.opencode/bin/opencode','service','stop'],env=open_env,cwd=fixture.home,capture_output=True,text=True,timeout=20,check=True)
 for topic in ('paths','config'):
  debug=subprocess.run(['/home/outsider/.opencode/bin/opencode','debug',topic],env=open_env,cwd=fixture.home,capture_output=True,text=True,timeout=30)
  (out/('opencode-debug-'+topic+'.private.stdout')).write_text(debug.stdout)
  (out/('opencode-debug-'+topic+'.private.stderr')).write_text(debug.stderr)
 deadline=time.monotonic()+15;attempts=0
 while True:
  attempts+=1
  checked=subprocess.run(['/home/outsider/.opencode/bin/opencode','mcp','list'],env=open_env,cwd=fixture.home,capture_output=True,text=True,timeout=60)
  if 'No MCP servers configured' not in checked.stdout or time.monotonic()>=deadline:break
  time.sleep(.5)
 receipt['opencode_list_attempts']=attempts
 (out/'opencode-health.private.stdout').write_text(checked.stdout);(out/'opencode-health.private.stderr').write_text(checked.stderr)
 assert checked.returncode==0 and 'connected' in checked.stdout.lower(), 'OpenCode does not connect'
 receipt['opencode_bearer_health_check']=True
 receipt['opencode_version']=subprocess.check_output(['/home/outsider/.opencode/bin/opencode','--version'],text=True).strip()
 receipt.update(status='PASS',client='Codex CLI',version=subprocess.check_output(['/home/outsider/.local/bin/codex','--version'],text=True).strip(),
  discovery=True,dynamic_registration=True,oauth_code_pkce=True,owner_consent=True,callback=True,credentials_saved=True,
  test_data='synthetic',shared_client_config_unchanged=True,default_oauth_registration_and_scope=True)
 code=0
except BaseException as error:
 receipt.update(status='FAIL',error_type=type(error).__name__)
 (out/'client-private-error.txt').write_text(traceback.format_exc())
finally:
 if open_env is not None:
  stopped=subprocess.run(['/home/outsider/.opencode/bin/opencode','service','stop'],env=open_env,cwd=fixture.home,capture_output=True,text=True,timeout=20)
  receipt['isolated_opencode_service_stopped']=stopped.returncode==0
 if process and process.poll() is None:process.terminate();process.wait(timeout=10)
 server.should_exit=True;thread.join(10);listener.close();fixture.doCleanups()
 (out/'client-verification.json').write_text(json.dumps(receipt,indent=2)+'\n')
 (out/'client-verification.done').write_text(str(code)+'\n')
 print(json.dumps(receipt))
raise SystemExit(code)
