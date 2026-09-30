# ABOUTME: Inspects capture health and deployment provenance without exporting content.
# ABOUTME: Emits counts and booleans while all production artifacts remain on their host.

import collections
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess


home = Path.home()
development = home / 'workspace/development-hook-capture/development'
config = json.loads((home / '.config/lifeos-development-capture/config.json').read_text())
root = Path(config['root'])
current = {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
           for path in (development / 'hook_capture').glob('*.py')}
result = {
    'uid': os.getuid(),
    'config_mode': oct((home / '.config/lifeos-development-capture/config.json').stat().st_mode & 0o777),
    'root_mode': oct(root.stat().st_mode & 0o777),
    'observer_source_manifest_matches_disk': config.get('capture_sources') == current,
    'runtime_fingerprints_match_disk': all(Path(path).is_file() and hashlib.sha256(Path(path).read_bytes()).hexdigest() == expected
        for path, expected in config['fingerprints'].items()),
    'runtime_fingerprint_count': len(config['fingerprints']),
    'hermes_revision': subprocess.check_output(['git', '-C', config['host_root'], 'rev-parse', 'HEAD'], text=True).strip(),
}
secrets = set()
sensitive = re.compile(r'(^|_)(password|passwd|secret|token|api_?key|(?:access|refresh|auth)_?token|private_?key|client_?secret)($|_)|^authorization$|^cookie$|^set.cookie$', re.I)
for line in (home / '.hermes/.env').read_text().splitlines():
    if '=' in line and not line.lstrip().startswith('#'):
        key, value = line.split('=', 1)
        value = value.strip().strip('"\'')
        if sensitive.search(key) and len(value) >= 8:
            secrets.add(value)
stages = collections.Counter()
with_turn = collections.Counter()
with_session = collections.Counter()
statuses = collections.Counter()
failures = {}
artifact_refs = set()
for path in root.glob('runs/*/events/*/*.jsonl'):
    for line in path.read_text().splitlines():
        try:
            row = json.loads(line)
        except ValueError:
            continue
        stages[row['stage']] += 1
        if row.get('turn_id'):
            with_turn[row['stage']] += 1
        if row.get('session_id'):
            with_session[row['stage']] += 1
        if row.get('status'):
            statuses[row['status']] += 1
        failures[row['process_id']] = max(failures.get(row['process_id'], 0), row.get('prior_capture_failures', 0))
        if row.get('data_ref'):
            artifact_refs.add(row['data_ref']['path'])
leak_artifacts = 0
integrity_errors = 0
artifact_bytes = 0
for relative in artifact_refs:
    try:
        raw = gzip.decompress((root / relative).read_bytes())
        artifact_bytes += len(raw)
        text = raw.decode()
        # Only counts leave the host. This does not claim exhaustive credential detection.
        if any(secret in text for secret in secrets):
            leak_artifacts += 1
    except Exception:
        integrity_errors += 1
result.update({
    'events': sum(stages.values()), 'stage_counts': dict(stages), 'status_counts': dict(statuses),
    'host_stage_identity_counts': {stage: {'events': count, 'with_turn_id': with_turn[stage], 'with_session_id': with_session[stage]}
        for stage, count in stages.items() if stage.startswith('host.')},
    'known_credential_literal_artifact_matches': leak_artifacts,
    'credential_scan_is_exhaustive': False,
    'referenced_artifacts': len(artifact_refs), 'referenced_artifact_bytes': artifact_bytes,
    'artifact_read_errors': integrity_errors, 'reported_capture_failures': sum(failures.values()),
})
print(json.dumps(result, indent=2, sort_keys=True))
