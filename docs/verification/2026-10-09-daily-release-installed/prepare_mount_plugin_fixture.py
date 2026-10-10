# ABOUTME: Prepares a fresh native source with the corrected Mount list insertion.
# ABOUTME: Reuses the verified native dependency tree without changing historical sources.
from pathlib import Path
import sys
sys.path.insert(0, str(Path.cwd()))
from lifeos_hook_bridge.install_source import prepare_lifeos, SUPPORTED_LIFEOS_COMMIT, LIFEOS_PATCHES
root=Path('/home/outsider/.cache/lifeos-daily-text-20261007/mount-plugin-sequence-first')
root.mkdir()
prepare_lifeos('/home/outsider/.cache/lifeos-daily-text-20261007/channel-sources/lifeos', root/'lifeos', SUPPORTED_LIFEOS_COMMIT, Path('lifeos_hook_bridge/patches').resolve(), LIFEOS_PATCHES)
(root/'lifeos/LifeOS/install/node_modules').symlink_to('/home/outsider/.cache/lifeos-daily-text-20261007/conduit-capture-first/lifeos/LifeOS/install/node_modules', target_is_directory=True)
print('Prepared the corrected pinned native candidate')
