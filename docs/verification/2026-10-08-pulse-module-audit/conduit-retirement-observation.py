import unittest
from pathlib import Path
from lifeos_hook_bridge.memory_access import NativeMemory
from test_memory_conduit import MemoryConduitTests
original = NativeMemory.forget

def observe(memory, *args, **kwargs):
    result = original(memory, *args, **kwargs)
    path = memory.root / 'LIFEOS/USER/CONDUIT/config.json'
    if path.exists():
        raw = path.read_bytes()
        before = path.stat().st_mtime_ns
        path.write_bytes(raw)
        print({'observation': 'fresh configuration after actual retirement', 'same_bytes': path.read_bytes() == raw,
            'timestamp_advanced': path.stat().st_mtime_ns > before})
    return result

NativeMemory.forget = observe
suite = unittest.defaultTestLoader.loadTestsFromName('test_memory_conduit.MemoryConduitTests.test_private_and_retired_events_do_not_contribute_labels_or_counts')
result = unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(0 if result.wasSuccessful() else 1)
