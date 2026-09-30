# ABOUTME: Checks whether required admission rejects an asynchronous callback it cannot run.
# ABOUTME: Uses the prepared source and a disposable plugin manager without network calls.
from pathlib import Path
import gc,json,os,sys,tempfile,warnings
with tempfile.TemporaryDirectory(prefix='memory-required-review-') as directory:
    os.environ['HOME']=directory
    os.environ['HERMES_HOME']=str(Path(directory)/'hermes')
    sys.path.insert(0,'/home/outsider/.cache/lifeos-plugin-memory/source-gate-20260930-provider/hermes')
    from hermes_cli.plugins import PluginContext,PluginManifest,get_plugin_manager
    from hermes_cli.middleware import run_llm_execution_middleware
    manager=get_plugin_manager();manager.discover_and_load()
    ctx=PluginContext(PluginManifest(name='synthetic-required-review',version='1.0.0',description='Synthetic review'),manager)
    attempted=[];dispatched=[]
    async def deny(**kwargs):
        attempted.append(True)
        raise ValueError('Synthetic required denial')
    try:
        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter('always')
            ctx.register_middleware('llm_admission',deny,required=True)
            result=run_llm_execution_middleware({},lambda req:dispatched.append(True))
            gc.collect()
        print(json.dumps({'case':'required_async_admission','body_executed':attempted,'downstream_dispatched':dispatched,
                          'returned':result,'warnings':[str(w.message) for w in captured]},sort_keys=True))
    finally:manager.unload()
