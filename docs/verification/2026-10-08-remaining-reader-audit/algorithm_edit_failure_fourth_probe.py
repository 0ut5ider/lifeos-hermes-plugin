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
        self.fixture.login()
        self.fixture.client.get('/api/plugins/lifeos-hook-bridge/memory/pulse/state')
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
        edits=importlib.import_module('lifeos_memory_settings.memory_algorithm_edit')
        matches=edits._matches
        def measured(memory,admitted,changes):
            mismatches=[]
            for row in admitted[1]:
                name,expected=row[:2]
                if name in changes: continue
                path=memory.root/name
                if expected is not None and path.exists():
                    info=path.stat()
                    current=(info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns)
                    if expected != current: mismatches.append({'path':name,'expected':expected,'current':current})
            result=matches(memory,admitted,changes)
            rows.append({'operation':'matches','matched':result,'fingerprint_mismatches':mismatches,
                'native_metadata_expected':next((row[1] for row in admitted[1] if len(row)==2 and row[1] is not None),None)})
            return result
        edits._matches=measured
        self.addCleanup(setattr,edits,'_matches',matches)
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
Path(__file__).with_name('algorithm-edit-failure-fourth-observation.json').write_text(json.dumps(rows,indent=2)+'\n')
raise SystemExit(0 if result.wasSuccessful() else 1)
