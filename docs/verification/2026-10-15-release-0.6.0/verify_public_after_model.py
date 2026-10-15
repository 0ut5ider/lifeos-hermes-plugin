# ABOUTME: Rechecks the actual public installation after the fresh model verification finishes.
# ABOUTME: Binds sealed programs and preserved model choices to the successful model receipt.
import hashlib
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import types

from ruamel.yaml import YAML

if sys.flags.optimize or os.getuid() != 1000:
    raise RuntimeError('Use assertions and the disposable guest owner')
home = Path('/home/lifeos-hermes')
profile = home / '.hermes'
identifier = 'a8486ae6890a41ceaf29202cb5dce463'
sys.path.insert(0, str(profile / '.lifeos-releases' / identifier / 'hermes'))
namespace = types.ModuleType('public_after_model')
namespace.__path__ = [str(profile / 'plugins/lifeos-release-manager')]
sys.modules[namespace.__name__] = namespace
cli = importlib.import_module(namespace.__name__ + '.cli')
worker = importlib.import_module(namespace.__name__ + '.release_worker')
job, request = cli.operation(profile, identifier)
assert cli.read_private(job / 'status.json')['state'] == 'applied'
receipt_path = home / 'install-input/fresh-public-verification/receipt.json'
model = json.loads(receipt_path.read_bytes())
assert model['status'] == 'PASS' and model['operation'] == identifier
assert model['actual_model_round_trip'] is True
assert model['public_catalog_certificate_verified'] is True
plan = importlib.import_module(namespace.__name__ + '.release_operation').validate_plan(job, request)
bridge = worker.recovery_bridge(job, profile)
baseline = bridge.memory_module('version_drift').default_baseline_path(Path(request['installed']).parent)
mount = bridge.memory_module('mount_transaction').MountTransaction(Path(request['installed']), profile, baseline)
worker.check_restore(job, request, plan, mount)
config = YAML(typ='safe').load((profile / 'config.yaml').read_bytes())
settings = config['plugins']['entries']['lifeos-hook-bridge']['settings']
selected = {'model': config['model'], 'tiers': {key: settings[key]
    for tier in ('haiku', 'sonnet', 'opus', 'fable')
    for key in (tier + '_model', tier + '_effort')}}
digest = hashlib.sha256(json.dumps(selected, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
assert digest == model['model_mapping_sha256']
version = subprocess.run([str(home / '.local/bin/hermes'), 'lifeos-version'],
    capture_output=True, text=True, check=True, timeout=90)
active = json.loads(version.stdout)['active']
assert active == model['active_identity']
assert active['verification'] == 'verified' and active['modified_files'] == []
receipt = {'status': 'PASS', 'operation': identifier,
    'program_commit': request['commit'], 'archive_sha256': request['package_sha256'],
    'prior_model_receipt_sha256': hashlib.sha256(receipt_path.read_bytes()).hexdigest(),
    'model_session': model['model_session'], 'sealed_programs_verified_after_model': True,
    'selected_model_and_tiers_unchanged_after_model': True, 'active_identity': active,
    'production_guest_changed': False}
output = home / 'install-input/fresh-public-post-model-verification.json'
with output.open('x') as handle:
    json.dump(receipt, handle, indent=2)
    handle.write('\n')
print(json.dumps(receipt))
