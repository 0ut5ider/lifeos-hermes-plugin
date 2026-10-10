# ABOUTME: Captures native edit failures and journal receipts inside synthetic owner fixtures.
# ABOUTME: Records operation names and fixed exceptions without request headers or model configuration.
import importlib
import json
from pathlib import Path
import unittest
import test_memory_algorithm_edits as original
rows=[]
class Diagnostics(original.MemoryAlgorithmEditTests):
    def setUp(self):
        super().setUp()
        module=importlib.import_module('lifeos_memory_settings.memory_access')
        for name in ('_native','_operation'):
            function=getattr(module.NativeMemory,name)
            def observed(memory,*args,_function=function,_name=name,**kwargs):
                try:
                    result=_function(memory,*args,**kwargs)
                    if _name=='_operation': rows.append({'operation':_name,'receipt':result})
                    elif args and args[0]=='algorithm_edit_render': rows.append({'operation':args[0],'result':result})
                    return result
                except Exception as error:
                    rows.append({'operation':str(args[0]) if args else _name,'exception':type(error).__name__,'message':str(error)})
                    raise
            setattr(module.NativeMemory,name,observed)
            self.addCleanup(setattr,module.NativeMemory,name,function)
        preferences=importlib.import_module('lifeos_memory_settings.memory_preferences')
        function=preferences.MemoryPreferences.edit_algorithm
        def observed(preferences,*args,**kwargs):
            try: return function(preferences,*args,**kwargs)
            except Exception as error:
                rows.append({'operation':'edit_algorithm','exception':type(error).__name__,'message':str(error)})
                raise
        preferences.MemoryPreferences.edit_algorithm=observed
        self.addCleanup(setattr,preferences.MemoryPreferences,'edit_algorithm',function)
suite=unittest.defaultTestLoader.loadTestsFromTestCase(Diagnostics)
result=unittest.TextTestRunner(verbosity=2).run(suite)
Path(__file__).with_name('algorithm-edit-failure-observation.json').write_text(json.dumps(rows,indent=2)+'\n')
raise SystemExit(0 if result.wasSuccessful() else 1)
