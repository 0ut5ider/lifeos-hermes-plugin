# ABOUTME: Rebuilds the complete pinned Hermes and LifeOS candidate after cancellation changes.
# ABOUTME: Verifies applied patch hashes and physical candidate contents with the installation validators.
import json
import argparse
from pathlib import Path
import subprocess
import sys

repository = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(repository))
from lifeos_hook_bridge.install_source import (prepare_hermes, prepare_lifeos,
    validate_hermes_candidate, validate_candidate, SUPPORTED_HERMES_COMMIT,
    SUPPORTED_LIFEOS_COMMIT, HERMES_PATCHES, LIFEOS_PATCHES)

parser = argparse.ArgumentParser()
parser.add_argument('--stage', type=Path,
    default=Path.home() / '.cache/lifeos-daily-text-20261007/cancellation-sources')
stage = parser.parse_args().stage.absolute()
stage.mkdir(mode=0o700)
base = stage / 'hermes-base'
subprocess.run(['git', 'clone', '--quiet', '--no-checkout', '--',
    str(stage.parent / 'channel-sources/hermes'), str(base)], check=True, capture_output=True)
subprocess.run(['git', 'checkout', '--quiet', '--detach', SUPPORTED_HERMES_COMMIT],
               cwd=base, check=True, capture_output=True)
patches = repository / 'lifeos_hook_bridge/patches'
prepare_hermes(base, stage / 'hermes', SUPPORTED_HERMES_COMMIT, patches, HERMES_PATCHES)
prepare_lifeos(str(stage.parent / 'channel-sources/lifeos'), stage / 'lifeos',
               SUPPORTED_LIFEOS_COMMIT, patches, LIFEOS_PATCHES)
result = {'hermes': validate_hermes_candidate(stage / 'hermes', SUPPORTED_HERMES_COMMIT, patches, HERMES_PATCHES),
          'lifeos': validate_candidate(stage / 'lifeos', SUPPORTED_LIFEOS_COMMIT, patches, LIFEOS_PATCHES)}
Path(__file__).with_name('prepared-sources.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'hermes_patches': len(result['hermes']['patches']),
                  'lifeos_patches': len(result['lifeos']['patches']), 'validated': True}))
