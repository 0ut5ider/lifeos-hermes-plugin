# ABOUTME: Verifies CLI admission handoff through the real bounded host dispatcher.
# ABOUTME: Uses temporary native configuration and records dispatch without calling a model.
from pathlib import Path
import json,os,sys
sys.path.insert(0,str(Path.cwd()));sys.path.insert(0,str(Path.cwd()/'tests'))
from test_memory_runtime import MemoryRuntimeTests
from lifeos_hook_bridge.memory_service import MemoryConfiguration
from lifeos_hook_bridge.memory_context import current_host_metadata,route_identity
f=MemoryRuntimeTests();f.setUp()
old=dict(os.environ)
try:
    os.environ['HOME']=str(f.fixture.home);os.environ['HERMES_HOME']=str(f.home)
    os.environ.pop('LIFEOS_MEMORY_CONTEXT',None)
    sys.path.insert(0,'/home/outsider/.cache/lifeos-plugin-memory/source-gate-20260930-native/hermes')
    from hermes_cli.plugins import PluginContext,PluginManifest,get_plugin_manager
    from hermes_cli.middleware import run_llm_execution_middleware
    from gateway.session_context import set_session_vars,clear_session_vars
    f.configuration['accounts'][f'terminal:{os.getuid()}']='owner'
    f.configuration['destinations'][f'terminal:{f.home}']={
        'visibility':'private','participants':['owner'],'read':['principal','assistant','project'],
        'write':['project'],'projects':['*'],'model_routes':[route_identity(**f.route)]}
    MemoryConfiguration(f.path).save(f.configuration)
    tokens=set_session_vars(platform='',session_id='terminal')
    f.runtime.clear()
    manager=get_plugin_manager();manager.discover_and_load()
    ctx=PluginContext(PluginManifest(name='terminal-memory-review',version='1.0.0',description='Synthetic review'),manager)
    ctx.register_hook('pre_prompt_admission',lambda **kw:f.runtime.admit(current_host_metadata(),**kw))
    ctx.register_middleware('llm_admission',f.runtime.check_call,required=True)
    try:
        admission=manager.invoke_hook('pre_prompt_admission',session_id='terminal',platform='cli',is_first_turn=True,**f.route)
        called=[]
        try:
            result=run_llm_execution_middleware({'model':'synthetic-model'},lambda req:called.append(True),session_id='terminal',platform='cli',**f.route)
            dispatch={'returned':result}
        except Exception as e:dispatch={'raised':type(e).__name__,'message':str(e),'cause':str(e.__cause__)}
        print(json.dumps({'case':'cli_worker_admission','metadata':current_host_metadata(),'admission_result':admission,
                          'state_recorded':'terminal' in f.runtime._states(),'dispatch':dispatch,'downstream':called},sort_keys=True))
    finally:manager.unload();clear_session_vars(tokens)
finally:
    f.runtime.clear();os.environ.clear();os.environ.update(old);f.doCleanups()
