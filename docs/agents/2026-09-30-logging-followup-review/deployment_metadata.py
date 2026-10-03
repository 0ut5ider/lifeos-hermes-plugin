# ABOUTME: Counts deployment metadata without exporting captured conversation content.
# ABOUTME: Reads observer manifests and identity fields with the standard library only.
import collections
import gzip
import hashlib
import json
from pathlib import Path

home = Path.home()
config_path = home / '.config/lifeos-development-capture/config.json'
config = json.loads(config_path.read_text())
root = Path(config['root'])
development = home / 'workspace/development-hook-capture/development'
current = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (development / 'hook_capture').glob('*.py')}
result = {'observer_manifest_matches': current == config.get('capture_sources'),
          'observer_manifest_actual': current,
          'config_mode': oct(config_path.stat().st_mode & 0o777),
          'root_mode': oct(root.stat().st_mode & 0o777),
          'runtime_fingerprints_match': all(hashlib.sha256(Path(p).read_bytes()).hexdigest() == v for p, v in config['fingerprints'].items()),
          'plugin_root': config['plugin_root'], 'host_root': config['host_root']}
stages = collections.Counter()
statuses = collections.Counter()
identities = {}
loss = {}
manifests = collections.Counter()
invalid = 0
for path in root.glob('runs/*/events/*/*.jsonl'):
    for line in path.read_bytes().splitlines():
        try:
            row = json.loads(line)
            stages[row['stage']] += 1
            if row.get('status'):
                statuses[row['status']] += 1
            if row['stage'].startswith('host.'):
                counts = identities.setdefault(row['stage'], {'events': 0, 'session_id': 0, 'turn_id': 0})
                counts['events'] += 1
                counts['session_id'] += bool(row.get('session_id'))
                counts['turn_id'] += bool(row.get('turn_id'))
            key = (row['run_id'], row['process_id'])
            loss[key] = max(loss.get(key, 0), row.get('prior_capture_failures', 0))
            if row['stage'] == 'process.initialized' and row.get('data_ref'):
                content = json.loads(gzip.decompress((root / row['data_ref']['path']).read_bytes()))
                recorded = content.get('capture_sources_actual') or content.get('config', {}).get('capture_sources', {})
                manifests[hashlib.sha256(json.dumps(recorded, sort_keys=True).encode()).hexdigest()] += 1
        except Exception:
            invalid += 1
result.update(events=sum(stages.values()), stage_counts=dict(stages), status_counts=dict(statuses),
              host_identity_counts=identities, reported_losses=sum(loss.values()), metadata_read_errors=invalid,
              process_manifest_versions=dict(manifests))
print(json.dumps(result, indent=2, sort_keys=True))
