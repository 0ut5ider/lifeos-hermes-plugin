# ABOUTME: Validates read-only canonical source bytes against current bundled patch identities.
# ABOUTME: Keeps native dependency reuse separate from complete prepared source manifest evidence.
from pathlib import Path
import json
from lifeos_hook_bridge.install_source import _tree_digest, validate_candidate, SUPPORTED_LIFEOS_COMMIT,LIFEOS_PATCHES,HERMES_PATCHES,SUPPORTED_HERMES_COMMIT
root=Path('/home/outsider/Projects/Hermes_agent/LifeOS_plugin')
prepared=Path('/home/outsider/.cache/lifeos-daily-text-20261007/daily-text-0.2.0-content-fixed')
lifeos=validate_candidate(prepared/'lifeos',SUPPORTED_LIFEOS_COMMIT,root/'patches',LIFEOS_PATCHES)
manifest=json.loads((prepared/'hermes/hermes-source-manifest.json').read_text())
hermes_tree=_tree_digest(prepared/'hermes','hermes-source-manifest.json')
assert manifest['base_commit']==SUPPORTED_HERMES_COMMIT,manifest
assert hermes_tree==manifest['tree_sha256'],(hermes_tree,manifest['tree_sha256'])
print(json.dumps({'lifeos_manifest_valid':True,'lifeos_tree_sha256':lifeos['tree_sha256'],'hermes_manifest_tree_valid':True,'hermes_tree_sha256':hermes_tree}))
