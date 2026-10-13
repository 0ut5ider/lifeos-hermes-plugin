# ABOUTME: Measures registration of the sealed candidate bridge through the actual native plugin loader.
# ABOUTME: Records command availability without invoking handlers or activating the candidate installation.
import faulthandler
import json
from pathlib import Path
import sys
import time

job = Path(sys.argv[1])
request = json.loads((job / 'request.json').read_bytes())
sys.path.insert(0, request['runtime']['source'])
from hermes_cli.plugins import PluginManager
from hermes_cli.plugins_manifest import parse_manifest_file

source = Path(sys.argv[3]) if len(sys.argv) > 3 else job / 'package/lifeos_hook_bridge'
manifest = parse_manifest_file(source / 'plugin.yaml', source, 'user', '')
manager = PluginManager(scope_key=request['profile'])
folder = Path(sys.argv[2])
with (folder / 'candidate-registration-stack.txt').open('w') as output:
    faulthandler.dump_traceback_later(8, file=output)
    started = time.monotonic()
    manager._load_plugin(manifest)
    faulthandler.cancel_dump_traceback_later()
plugin = manager._plugins[manifest.key]
value = {'plugin': manifest.name, 'version': manifest.version,
    'elapsed_seconds': time.monotonic() - started, 'error': plugin.error,
    'commands': sorted(manager._cli_commands), 'reference_candidate_commit': request['commit'],
    'tested_source': str(source), 'modified_source_experiment': len(sys.argv) > 3,
    'registration_only': True, 'installation_selected': False}
manager.unload()
(folder / 'candidate-registration.json').write_text(json.dumps(value, indent=2) + '\n')
print(json.dumps(value))
assert plugin.error is None and 'lifeos-version' in value['commands']
