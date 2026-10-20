# ABOUTME: Enrolls a disposable HTTP memory connection through the bridge MemoryRemote code on a rehearsal host.
# ABOUTME: Writes the personal token to a private file and prints only the connection name and status.
import importlib.util, json, os, sys
from pathlib import Path

plugin = Path.home() / '.hermes/plugins/lifeos-hook-bridge'
spec = importlib.util.spec_from_file_location('lifeos_bridge_probe', plugin / '__init__.py',
                                              submodule_search_locations=[str(plugin)])
package = importlib.util.module_from_spec(spec); sys.modules['lifeos_bridge_probe'] = package
remote_module = importlib.import_module('lifeos_bridge_probe.memory_remote')
remote = remote_module.MemoryRemote(Path.home() / '.hermes/lifeos-memory.json')
result = remote.enroll({'client': sys.argv[3] if len(sys.argv) > 3 else 'rehearsal-probe', 'read': ['project'], 'write_project': False,
                        'projects': ['*'], 'model_route': 'rehearsal'}, account=sys.argv[1])
target = Path(sys.argv[2]); fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
os.write(fd, result['token'].encode()); os.close(fd)
print(json.dumps({'client': result['client'], 'status': result['status'], 'mcp_url': result['mcp_url']}))
