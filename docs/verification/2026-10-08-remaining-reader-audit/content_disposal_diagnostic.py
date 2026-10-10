# ABOUTME: Captures actual owner disposal exceptions and receipts in synthetic HTTP fixtures.
# ABOUTME: Retains diagnostics without changing native filesystem or admission behavior.
import importlib
import unittest
import test_memory_content_disposal as tests

original = tests.MemoryContentDisposalTests.setUp

def setup(test):
    original(test)
    test.fixture.login()
    test.fixture.client.get('/api/plugins/lifeos-hook-bridge/memory/pulse/state')
    module = importlib.import_module('lifeos_memory_settings.memory_content_disposal')
    dispose = module.dispose
    def diagnostic(*arguments, **values):
        try:
            return dispose(*arguments, **values)
        except Exception as error:
            print(type(error).__name__, str(error), flush=True)
            raise
    module.dispose = diagnostic
    test.addCleanup(setattr, module, 'dispose', dispose)
    access = importlib.import_module('lifeos_memory_settings.memory_access')
    operation = access.NativeMemory._operation
    def receipt(*arguments, **values):
        result = operation(*arguments, **values)
        print(result, flush=True)
        return result
    access.NativeMemory._operation = receipt
    test.addCleanup(setattr, access.NativeMemory, '_operation', operation)

tests.MemoryContentDisposalTests.setUp = setup
suite = unittest.defaultTestLoader.loadTestsFromModule(tests)
result = unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(not result.wasSuccessful())
