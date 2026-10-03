# ABOUTME: Probes actual host dispatch and memory admission with disposable synthetic state.
# ABOUTME: Never invokes a model provider or imports a live runtime installation.
from pathlib import Path
from dataclasses import asdict
import json,os,sys
REPO=Path.cwd()
HOST=Path('/home/outsider/.cache/lifeos-plugin-memory/source-gate-20260930-provider/hermes')
sys.path.insert(0,str(REPO));sys.path.insert(0,str(REPO/'tests'))
from test_memory_runtime import MemoryRuntimeTests
from lifeos_hook_bridge.memory_service import MemoryConfiguration

def outcome(fn):
    try: return {'returned':fn()}
    except Exception as exc: return {'raised':type(exc).__name__,'message':str(exc)}

def run(name,fn):
    f=MemoryRuntimeTests(); f.setUp()
    old=dict(os.environ)
    try:
        os.environ['HOME']=str(f.fixture.home)
        os.environ['HERMES_HOME']=str(f.home)
        os.environ.pop('LIFEOS_MEMORY_CONTEXT',None)
        sys.path.insert(0,str(HOST))
        f.runtime.clear()
        print(json.dumps({'case':name,'result':fn(f)},sort_keys=True),flush=True)
    finally:
        f.runtime.clear();os.environ.clear();os.environ.update(old);f.doCleanups()

def worker_admission(f):
    from hermes_cli.plugins import PluginContext,PluginManifest,get_plugin_manager
    from hermes_cli.middleware import run_llm_execution_middleware
    from lifeos_hook_bridge.memory_provider import LifeOSMemoryProvider
    manager=get_plugin_manager();manager.discover_and_load()
    context=PluginContext(PluginManifest(name='synthetic-memory-review',version='1.0.0',description='Synthetic review'),manager)
    inside=[]
    def admission(**kwargs):
        f.runtime.admit(f.metadata(),**f.route,is_first_turn=True)
        inside.append(asdict(f.runtime.context()))
    context.register_hook('pre_prompt_admission',admission)
    context.register_middleware('llm_admission',f.runtime.check_call,required=True)
    try:
        hook_result=manager.invoke_hook('pre_prompt_admission',session_id='session')
        downstream=[]
        result=outcome(lambda:run_llm_execution_middleware({'model':'synthetic-model'},lambda req:downstream.append(True),**f.route,session_id='session'))
        provider=LifeOSMemoryProvider(f.path)
        return {'hook_result':hook_result,'inside_worker':inside,'parent_context':f.runtime.context(),
                'model_dispatch':result,'downstream_called':downstream,
                'provider_status':json.loads(provider.handle_tool_call('lifeos_memory_status',{},session_id='session'))}
    finally:manager.unload()

def disabled_after_admission(f):
    f.admit()
    f.configuration['ownership_enabled']=False
    f.configuration['accounts']={}
    MemoryConfiguration(f.path).save(f.configuration)
    return {'check_after_disable':outcome(lambda:f.runtime.check_call(request={'messages':[{'role':'system','content':'Synthetic retained private fact'}]},**dict(f.route,base_url='https://unapproved.example/v1'),session_id='session')),
            'bound_context_remains':f.runtime.context() is not None}

def removed_after_admission(f):
    f.admit();f.path.unlink()
    return {'check_after_removal':outcome(lambda:f.runtime.check_call(request={'messages':[{'role':'system','content':'Synthetic retained private fact'}]},**dict(f.route,base_url='https://unapproved.example/v1'),session_id='session'))}

run('actual_host_admission_worker_context',worker_admission)
run('ownership_disabled_with_retained_context',disabled_after_admission)
run('configuration_removed_with_retained_context',removed_after_admission)

def general_discovery(f):
    import shutil
    from hermes_cli.plugins import get_plugin_manager
    plugin=f.home/'plugins/lifeos-hook-bridge'
    plugin.parent.mkdir(parents=True)
    shutil.copytree(REPO/'lifeos_hook_bridge',plugin,ignore=shutil.ignore_patterns('__pycache__'))
    (f.home/'config.yaml').write_text('plugins:\n  enabled: [lifeos-hook-bridge]\nmemory:\n  provider: null\n')
    f.configuration['ownership_enabled']=False
    MemoryConfiguration(f.path).save(f.configuration)
    manager=get_plugin_manager();manager.discover_and_load()
    try:
        loaded=manager._plugins['lifeos-hook-bridge']
        return {'kind':loaded.manifest.kind,'enabled':loaded.enabled,'error':loaded.error,
                'module_loaded':loaded.module is not None,'registered_pre_prompt_hooks':len(manager._hooks.get('pre_prompt_admission',[]))}
    finally: manager.unload()

run('general_plugin_discovery_without_memory_selection',general_discovery)
