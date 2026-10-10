# ABOUTME: Prepares the pinned native candidate with interruptible scheduler shutdown.
# ABOUTME: Retains historical sources and reuses verified native dependency trees.
from pathlib import Path
import sys

sys.path.insert(0, str(Path.cwd()))
from lifeos_hook_bridge.install_source import prepare_lifeos, SUPPORTED_LIFEOS_COMMIT, LIFEOS_PATCHES

root = Path('/home/outsider/.cache/lifeos-daily-text-20261007/pulse-shutdown-first')
root.mkdir()
prepare_lifeos('/home/outsider/.cache/lifeos-daily-text-20261007/channel-sources/lifeos',
    root / 'lifeos', SUPPORTED_LIFEOS_COMMIT, Path('lifeos_hook_bridge/patches').resolve(), LIFEOS_PATCHES)
source = root / 'lifeos/LifeOS/install'
dependencies = Path('/home/outsider/.cache/lifeos-daily-text-20261007/conduit-capture-first/lifeos/LifeOS/install')
for relative in ('node_modules', 'LIFEOS/PULSE/node_modules', 'LIFEOS/PULSE/Observability/node_modules'):
    (source / relative).symlink_to(dependencies / relative, target_is_directory=True)
print('Prepared the pinned candidate with scheduler shutdown correction')
