# ABOUTME: Runs the retained real-filesystem characterization corpus against the previous bridge implementation.
# ABOUTME: Changes only module names in the test harness so synthetic policy roots apply to the retained source.
import importlib.util,json,sys,time,types,unittest
from pathlib import Path
out=Path(__file__).parent
name='lifeos_hook_bridge.review_before';spec=importlib.util.spec_from_file_location(name,out/'bridge_before.py');bridge=importlib.util.module_from_spec(spec);sys.modules[name]=bridge;spec.loader.exec_module(bridge)
text=(out/'test_config_inventory.py').read_text().replace('from lifeos_hook_bridge.bridge import HookBridge','from '+name+' import HookBridge').replace('lifeos_hook_bridge.bridge.POLICY_DIRECTORY',name+'.POLICY_DIRECTORY')
module=types.ModuleType('inventory_before_characterizations');exec(compile(text,str(out/'test_config_inventory.py'),'exec'),module.__dict__)
start=time.monotonic();result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(module))
summary={'tests':result.testsRun,'success':result.wasSuccessful(),'elapsed_seconds':time.monotonic()-start,'source_commit':'a5e4fbed','filesystem_and_test_assertions_unchanged':True}
(out/'before-characterizations.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2));assert result.wasSuccessful()
