# ABOUTME: Loads the optional SSH sharing component from the repository for tests.
# ABOUTME: Uses the same verified loader that the plugin uses for an installed component.
from pathlib import Path

from lifeos_hook_bridge.memory_preferences import load_sharing_component

COMPONENT = Path(__file__).parents[1] / 'optional/lifeos-memory-sharing'


def sharing():
    return load_sharing_component(COMPONENT)
