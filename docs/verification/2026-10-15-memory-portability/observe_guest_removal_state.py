# ABOUTME: Exports safe installed removal journals, software presence, and retained file identities.
# ABOUTME: Avoids native records, credentials, narration, and unrelated service logs.
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument('identifier')
parser.add_argument('--label', required=True)
args = parser.parse_args()
home = Path('/home/lifeos-hermes')
profile = home / '.hermes'
assert os.getuid() == 1000 and Path.home() == home
assert len(args.identifier) == 32 and all(c in '0123456789abcdef' for c in args.identifier)
assert args.label and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.label)
os.umask(0o077)
job = profile / '.lifeos-portability' / args.identifier
receipt = {'workflow': args.identifier, 'daily_changed': False, 'read_only': True}
for name, path in {'workflow_status': job / 'status.json',
                   'publication_status': job / 'removal/operation.json',
                   'workflow_receipt': job / 'receipt.json'}.items():
    if path.is_file():
        value = json.loads(path.read_bytes())
        receipt[name] = {k: value[k] for k in ('state', 'signature', 'application_verified',
            'builtin_memory_retained', 'native_data_retained', 'stock_commit', 'stock_patches',
            'discord_disabled', 'recovery_command') if k in value}
proof = job / 'removal/fresh-agent-verification.json'
if proof.is_file():
    value = json.loads(proof.read_bytes())
    receipt['fresh_constructor'] = {k: value[k] for k in ('format', 'provider', 'fresh_agent_verified',
        'model_turn_executed', 'active_plugins', 'native_providers') if k in value}
receipt['builtin_files'] = {name: {'bytes': (profile / 'memories' / name).stat().st_size,
    'sha256': hashlib.sha256((profile / 'memories' / name).read_bytes()).hexdigest()}
    for name in ('MEMORY.md', 'USER.md')}
receipt['active_software_present'] = {name: (profile / 'plugins' / name).exists()
    for name in ('lifeos', 'lifeos-hook-bridge', 'lifeos-release-manager')}
receipt['native_configuration_present'] = (profile / 'lifeos-memory.json').exists()
receipt['removal_marker_present'] = (profile / '.lifeos-removal.json').exists()
receipt['recovery_helper_present'] = (job / 'removal/recover').is_file()
receipt['services'] = {}
for unit in ('hermes-gateway.service', 'hermes-dashboard.service', 'com.lifeos.pulse.service'):
    result = subprocess.run(['systemctl', '--user', 'show', unit, '--property=ActiveState',
        '--property=SubState', '--property=LoadState', '--property=UnitFileState'],
        capture_output=True, text=True, timeout=30)
    receipt['services'][unit] = dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)
output = home / 'install-input/removal-observations'
output.mkdir(mode=0o700, exist_ok=True)
(output / (args.label + '.json')).write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt))
