# ABOUTME: Experiment 4 for the PR 3 follow-up review: component loading under the dashboard package name.
# ABOUTME: Mirrors plugin_api._memory_preferences, which imports the plugin as lifeos_memory_settings.
import importlib
import os
from pathlib import Path
import shutil
import sys
import types

sys.dont_write_bytecode = True
PLUGIN_DIR = Path('/tmp/pr3review/src/lifeos_hook_bridge')
REVIEWED = Path('/tmp/pr3review/src/optional/lifeos-memory-sharing')

package = types.ModuleType('lifeos_memory_settings')
package.__path__ = [str(PLUGIN_DIR)]
sys.modules['lifeos_memory_settings'] = package
preferences_module = importlib.import_module('lifeos_memory_settings.memory_preferences')

target = Path('/tmp/pr3review/exp4/component')
shutil.rmtree(target.parent, ignore_errors=True)
target.mkdir(parents=True, mode=0o700)
shutil.copyfile(REVIEWED / 'memory_sharing.py', target / 'memory_sharing.py'); os.chmod(target / 'memory_sharing.py', 0o600)

module = preferences_module.load_sharing_component(target)
print('module name:', module.__name__)
print('MemoryConfiguration comes from:', module.MemoryConfiguration.__module__)
print('MemoryUnavailable identity matches the dashboard package:',
      module.MemoryUnavailable is sys.modules['lifeos_memory_settings.memory_access'].MemoryUnavailable)
again = preferences_module.load_sharing_component(target)
print('second load returns a new module object:', again is not module,
      '; sys.modules entry is the latest:', sys.modules['lifeos_memory_settings.memory_sharing'] is again)

# A plain-package import in the same process uses its own name and does not collide.
sys.path.insert(0, '/tmp/pr3review/src')
from lifeos_hook_bridge.memory_preferences import load_sharing_component as plain_loader
plain = plain_loader(target)
print('plain package module name:', plain.__name__, '; dashboard entry intact:',
      sys.modules['lifeos_memory_settings.memory_sharing'] is again)
