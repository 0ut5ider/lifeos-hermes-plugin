# ABOUTME: Exercises the installed Codex OAuth client against a synthetic HTTP memory server.
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
process=None;code=1;receipt={'live_client_config_changed':False,'daily_changed':False}
try:
 deadline=time.monotonic()+10
 while not server.started and time.monotonic()<deadline:time.sleep(.01)
 assert server.started
 client_home=fixture.home/'codex';client_home.mkdir(mode=0o700)
 (client_home/'config.toml').write_text('[mcp_servers.synthetic-memory]\nurl = '+json.dumps(origin+MCP_PATH)+'\n')
 env=dict(os.environ,CODEX_HOME=str(client_home))
 stdout=(out/'codex-login.private.stdout').open('w');stderr=(out/'codex-login.private.stderr').open('w')
 process=subprocess.Popen(['/home/outsider/.local/bin/codex','mcp','login','synthetic-memory','--no-browser','--scopes','lifeos:memory','--oauth-client-registration','dcr'],
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
 receipt.update(status='PASS',client='Codex CLI',version=subprocess.check_output(['/home/outsider/.local/bin/codex','--version'],text=True).strip(),
  discovery=True,dynamic_registration=True,oauth_code_pkce=True,owner_consent=True,callback=True,credentials_saved=True,
  test_data='synthetic',shared_client_config_unchanged=True)
 code=0
except BaseException as error:
 receipt.update(status='FAIL',error_type=type(error).__name__)
 (out/'client-private-error.txt').write_text(traceback.format_exc())
finally:
 if process and process.poll() is None:process.terminate();process.wait(timeout=10)
 server.should_exit=True;thread.join(10);listener.close();fixture.doCleanups()
 (out/'client-verification.json').write_text(json.dumps(receipt,indent=2)+'\n')
 (out/'client-verification.done').write_text(str(code)+'\n')
 print(json.dumps(receipt))
raise SystemExit(code)
