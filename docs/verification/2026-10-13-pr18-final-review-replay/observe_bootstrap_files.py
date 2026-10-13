# ABOUTME: Verifies the installed default GitHub bootstrap against the corrected archive manager files.
# ABOUTME: Exports only public source provenance and source hash equality.
import hashlib
import json
from pathlib import Path
import sys
root=Path.home()/'.hermes/plugins/lifeos-release-manager'
expected=json.load(sys.stdin)
changed=[name for name,digest in expected.items() if not (root/name).is_file()
    or (root/name).is_symlink() or hashlib.sha256((root/name).read_bytes()).hexdigest()!=digest]
row=json.loads((root.parent/'.install-metadata.json').read_text())['lifeos-release-manager']
report={'version':'0.4.2-rc.3','manager_file_count':len(expected),'changed_files':changed,
    'native_revision':row['revision'],'native_source':row['source'],'native_selected_ref':row.get('ref'),
    'native_lifeos_absent':not (Path.home()/'.claude').exists(),
    'memory_ownership_configuration_present':(Path.home()/'.hermes/lifeos-memory.json').exists()}
assert row['source']=='https://github.com/0ut5ider/lifeos-hermes-plugin.git#optional/lifeos_release_manager'
assert row.get('ref') is None and not changed
print(json.dumps(report,indent=2))
