# ABOUTME: Reproduces native delivery mirroring before the first governed foreground turn.
# ABOUTME: Uses synthetic memory, actual Hermes session persistence, and the real admission callback.
import io,json,logging,os,sys
from pathlib import Path
from types import SimpleNamespace
os.umask(0o077)
import test_memory_runtime
fixture=test_memory_runtime.MemoryRuntimeTests();fixture.setUp()
os.environ['HERMES_HOME']=str(fixture.home);os.environ['HOME']=str(fixture.fixture.home)
from hermes_state import SessionDB
from hermes_cli.plugins import PluginContext,PluginManifest,get_plugin_manager
from gateway.mirror import mirror_to_session
from gateway.session import SessionStore
from gateway.config import GatewayConfig
from agent.turn_context import _collect_pre_llm_call_context
manager=get_plugin_manager();manager.discover_and_load()
context=PluginContext(PluginManifest(name='synthetic-admission',version='1.0.0',description='Synthetic admission reproduction'),manager)
observed=[]
def admit(**kwargs):
 observed.append({'session':kwargs['session_id'],'is_first_turn':kwargs['is_first_turn']})
 fixture.runtime.admit(fixture.metadata(session=kwargs['session_id']),**kwargs)
context.register_hook('pre_prompt_admission',admit)
logger=logging.getLogger('agent.turn_context');log=io.StringIO();handler=logging.StreamHandler(log);logger.addHandler(handler)
try:
 store=SessionStore(fixture.home/'sessions',GatewayConfig())
 db=store._db
 db.create_session('notification-first','chat-a',chat_id='200',user_id='100',chat_type='dm')
 assert mirror_to_session('chat-a','200','Synthetic morning notice',source_label='cli',session_id='notification-first')
 history=store.load_transcript('notification-first');assert [x['role'] for x in history]==['assistant']
 result={}
 for sid,prior in [('notification-first',history),('fresh-first',[])]:
  agent=SimpleNamespace(session_id=sid,model=fixture.route['model'],provider=fixture.route['provider'],base_url=fixture.route['base_url'],api_mode=fixture.route['api_mode'],platform='chat-a')
  try:
   _collect_pre_llm_call_context(agent,effective_task_id='synthetic',turn_id='synthetic',original_user_message='Synthetic hello',messages=prior+[{'role':'user','content':'Synthetic hello'}],conversation_history=prior)
   result[sid]={'admission':'PASS'}
  except Exception as error:
   result[sid]={'admission':'REFUSED','error_type':type(error).__name__,'missing_verified_context':'no verified memory context' in str(error)}
 assert result['notification-first']['admission']=='REFUSED',result
 assert result['fresh-first']['admission']=='PASS',result
 assert observed==[{'session':'notification-first','is_first_turn':False},{'session':'fresh-first','is_first_turn':True}],observed
 print(json.dumps({'status':'REPRODUCED','native_mirror_roles':[x['role'] for x in history],'hook_metadata':observed,'outcomes':result,'production_changed':False,'personal_memory_read':False},indent=2))
finally:
 logger.removeHandler(handler);manager.unload();fixture.doCleanups()
