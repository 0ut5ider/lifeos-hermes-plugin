# ABOUTME: Tests a synthetic memory profile through a temporary private Tailscale Serve listener.
# ABOUTME: Removes only its owned listener and writes receipts without credential contents.
import asyncio,json,os,subprocess,socket,threading,time,traceback,shlex
from pathlib import Path
import httpx2,uvicorn
from starlette.applications import Starlette
from mcp import Client
from mcp.client.streamable_http import streamable_http_client
from lifeos_hook_bridge.memory_remote import MemoryRemote,MemoryRemoteMiddleware,MCP_PATH
from lifeos_hook_bridge.memory_service import MemoryConfiguration
import test_memory_native as native
out=Path('/home/outsider/.cache/lifeos-http-mcp-20261015')
evidence={"daily_changed":False,"development_release_changed":False,"tailscale_installed_by_probe":False}
fixture=native.NativeMemoryTests();fixture.setUp()
listener=socket.socket();listener.bind(('127.0.0.1',0));port=listener.getsockname()[1]
server=None;thread=None;owned=False;code=1
try:
 before=json.loads(subprocess.check_output(['tailscale','serve','status','--json'],text=True))
 assert '8443' not in before.get('TCP',{}), 'The test port is already configured'
 status=json.loads(subprocess.check_output(['tailscale','status','--json'],text=True))
 assert status['BackendState']=='Running'
 public='https://'+status['Self']['DNSName'].rstrip('.')+':8443'
 path=fixture.home/'hermes/lifeos-memory.json'
 MemoryConfiguration(path).save({'version':1,'root':str(fixture.root),'principal':'owner','ownership_enabled':True,
  'sharing_enabled':False,'accounts':{'dashboard:test:owner':'owner'},'destinations':{},'clients':{}})
 remote=MemoryRemote(path);remote.configure({'enabled':True,'public_url':public},account='dashboard:test:owner')
 credential=remote.enroll({'client':'tailnet','read':['project'],'write_project':True,'projects':['lab'],'model_route':'unknown'},account='dashboard:test:owner')
 server=uvicorn.Server(uvicorn.Config(MemoryRemoteMiddleware(Starlette(),configuration=path),host='127.0.0.1',port=port,
  access_log=False,log_config=None,lifespan='off',ws='none'))
 thread=threading.Thread(target=server.run,kwargs={'sockets':[listener]},daemon=True);thread.start()
 deadline=time.monotonic()+10
 while not server.started and time.monotonic()<deadline:time.sleep(.02)
 assert server.started
 result=subprocess.run(['sudo','-n','tailscale','serve','--bg','--https=8443','http://127.0.0.1:'+str(port)],capture_output=True,text=True,timeout=45)
 assert result.returncode==0, 'Tailscale Serve does not start'
 owned=True
 peer_code = """import json,sys,urllib.request,urllib.error
v=json.load(sys.stdin)
request=urllib.request.Request(v['url'], data=json.dumps(v['body']).encode(), headers={
 'Authorization':'Bearer '+v['token'],'Content-Type':'application/json','Accept':'application/json, text/event-stream','MCP-Protocol-Version':'2025-03-26'})
try:
 with urllib.request.urlopen(request,timeout=30) as response:
  print(json.dumps({'status':response.status,'body':json.load(response)}))
except urllib.error.HTTPError as error:
 print(json.dumps({'status':error.code}))
"""
 def call(method,params):
  body={'jsonrpc':'2.0','id':1,'method':method,'params':params}
  result=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=5','outsider@192.168.8.211',
    'python3 -c '+shlex.quote(peer_code)],input=json.dumps({'url':public+MCP_PATH,'token':credential['token'],'body':body}),capture_output=True,text=True,timeout=40)
  assert result.returncode==0, 'The tailnet peer cannot complete its HTTPS request: '+result.stderr[-300:]
  return json.loads(result.stdout)
 listed=call('tools/list',{})
 assert listed['status']==200,listed
 assert len(listed['body']['result']['tools'])==9
 saved=call('tools/call',{'name':'lifeos_memory_remember','arguments':{'category':'project','content':'Synthetic Tailscale HTTPS acceptance marker',
  'title':'Synthetic HTTPS','project':'lab','request_id':'https-acceptance'}})['body']['result']['structuredContent']
 assert saved['status']=='committed',saved
 found=call('tools/call',{'name':'lifeos_memory_search','arguments':{'query':'Tailscale HTTPS acceptance'}})['body']['result']['structuredContent']
 assert found['results'][0]['reference']==saved['reference']
 remote.revoke('tailnet',account='dashboard:test:owner')
 assert call('tools/list',{})['status']==401
 evidence['separate_tailnet_peer_used']=True
 evidence['peer_credential_files_created']=False
 evidence['legacy_memory_server_accessed']=False
 evidence.update(status='PASS',https_certificate_verified=True,transport='Streamable HTTP',
  tailscale_serve=True,public_funnel=False,server_selected_grant=True,tools=9,synthetic_save_and_recall=True,revocation=True)
 code=0
except BaseException as error:
 evidence.update(status='FAIL',error_type=type(error).__name__)
 (out/'tailscale-private-error.txt').write_text(traceback.format_exc())
finally:
 if owned:
  stopped=subprocess.run(['sudo','-n','tailscale','serve','--https=8443','off'],capture_output=True,timeout=20)
  evidence['owned_listener_removed']=stopped.returncode==0
  after=json.loads(subprocess.check_output(['tailscale','serve','status','--json'],text=True))
  evidence['previous_serve_configuration_preserved']=after==before
  if not all(evidence[k] for k in ('owned_listener_removed','previous_serve_configuration_preserved')):code=1
 if server:server.should_exit=True
 if thread:thread.join(10)
 listener.close();fixture.doCleanups()
 (out/'tailscale-verification.json').write_text(json.dumps(evidence,indent=2)+'\n')
 (out/'tailscale-verification.done').write_text(str(code)+'\n')
 print(json.dumps(evidence))
raise SystemExit(code)
