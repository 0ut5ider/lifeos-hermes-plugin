# ABOUTME: Verifies exact managed release ownership on the disposable guest without selecting programs.
# ABOUTME: Exports generation and software counts only, without credentials or personal data.
import importlib.util
import json
from pathlib import Path
import sys
import types

profile=Path('/home/lifeos-hermes/.hermes')
namespace=types.ModuleType('lifeos_removal_generation_probe')
namespace.__path__=[str(profile/'plugins/lifeos-release-manager')]
sys.modules[namespace.__name__]=namespace
spec=importlib.util.spec_from_file_location(namespace.__name__+'.removal_generation',Path(__file__).with_name('removal_generation.py'))
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
from lifeos_removal_generation_probe.release_stage import load_bridge
bridge=load_bridge(profile/'plugins/lifeos-hook-bridge')
receipt={'guest':110,'address':'192.168.8.244','published_changes':False}
try:
 result=module.selected(profile,Path('/home/lifeos-hermes/.claude'),bridge=bridge)
 receipt.update(status='PASS',release=result['request']['version'],generation=result['job'].name,
  bridge_files=len(result['bridge_files']),manager_files=len(result['manager_files']),launchers=len(result['launchers']),
  hermes_commit=result['request']['commit'])
except (ValueError,OSError) as error:receipt.update(status='REFUSED',reason=str(error))
print(json.dumps(receipt))
