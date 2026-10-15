# ABOUTME: Checks native software ownership on the disposable installed guest without publishing changes.
# ABOUTME: Emits only program counts and a safe refusal, without reading memory records.
import importlib.util
import json
import os
from pathlib import Path
import sys
import types

profile=Path('/home/lifeos-hermes/.hermes')
job=profile/'.lifeos-releases/95b943fdc1244b5ea76ce96b6a56d723'
namespace=types.ModuleType('lifeos_removal_inventory_probe')
namespace.__path__=[str(profile/'plugins/lifeos-release-manager')]
sys.modules[namespace.__name__]=namespace
spec=importlib.util.spec_from_file_location(namespace.__name__+'.removal_inventory',Path(__file__).with_name('removal_inventory.py'))
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
from lifeos_removal_inventory_probe.release_stage import load_bridge
bridge=load_bridge(profile/'plugins/lifeos-hook-bridge')
request=json.loads((job/'request.json').read_bytes())
receipt={'guest':110,'address':'192.168.8.244','operation':job.name,'release':'0.5.0','published_changes':False}
try:
 result=module.native(Path(request['installed']),job/'package/lifeos/LifeOS/install',Path(request['runtime']['reference']),bridge=bridge)
 receipt.update(status='PASS',files=len(result['files']),dependency_roots=len(result['dependencies']),hook_receipt=result['hook_receipt'])
except ValueError as error:
 receipt.update(status='REFUSED',reason=str(error))
print(json.dumps(receipt))
