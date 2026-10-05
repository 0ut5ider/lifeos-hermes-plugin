# ABOUTME: Experiment 2 for the PR 3 follow-up review: time of check versus time of use in the loader.
# ABOUTME: Swaps the component directory after the hash check and before exec_module opens the source again.
import hashlib as real_hashlib
import os
from pathlib import Path
import shutil
import sys

sys.path.insert(0, '/tmp/pr3review/src')
sys.dont_write_bytecode = True
from lifeos_hook_bridge import memory_preferences

REVIEWED = Path('/tmp/pr3review/src/optional/lifeos-memory-sharing/memory_sharing.py')
home = Path('/tmp/pr3review/exp2/home')
shutil.rmtree(home.parent, ignore_errors=True)
home.mkdir(parents=True)
os.chmod(home, 0o777)  # a shared-write Hermes home: the loader never checks the parent
component = home / 'lifeos-memory-sharing'
component.mkdir(mode=0o700)
shutil.copyfile(REVIEWED, component / 'memory_sharing.py'); os.chmod(component / 'memory_sharing.py', 0o600)
other = home / 'attacker-dir'
other.mkdir(mode=0o700)
(other / 'memory_sharing.py').write_text("SWAPPED = True\nclass MemorySharing: pass\n")


class SwappingHash:
    """Stands in for a racing writer: the swap happens right after the digest."""
    def sha256(self, data):
        digest = real_hashlib.sha256(data)
        os.rename(component, home / 'moved-away')
        os.rename(other, component)
        return digest


memory_preferences.hashlib = SwappingHash()
module = memory_preferences.load_sharing_component(component)
print('directory swap after hash:', 'SWAPPED CODE RAN' if getattr(module, 'SWAPPED', False) else 'reviewed source ran')
print('loader checks parent mode? parent mode is', oct(home.stat().st_mode & 0o777), '- load was accepted')
