# ABOUTME: Verifies actual native index, Conduit insight, and Algorithm cache effects in the synthetic store.
# ABOUTME: Repeats the selected Algorithm owner command to prove complete current cache reuse without new publication.
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

stage = Path('/home/lifeos-hermes/migration/2026-10-09/daily-text-581d76a7')
prepared = json.loads((stage / 'applications-prepared.json').read_text())
profile, root = Path(prepared['profile']), Path(prepared['installed'])
os.umask(0o077)
receipt = json.loads((stage / 'installed-graph-job-second-user-index.txt').read_text())
index = root / 'LIFEOS/PULSE/state/user-index.json'
assert receipt['status'] == 'completed'
assert json.loads(receipt['output']) == json.loads(index.read_text())
assert len(receipt['output']) > 65536
insight = root / 'LIFEOS/USER/CONDUIT/insights/2026-10-09.json'
conduit = json.loads(insight.read_text())
assert conduit['model'] == 'haiku-tier' and conduit['level'] == 'low'
assert len(conduit['contentTypes']) == 2 and conduit['eventsConsidered'] == 4, list(conduit)
cache = root / 'LIFEOS/MEMORY/STATE/algorithm-tab-summary.json'
value = json.loads(cache.read_text())
assert len(value['files']) == 24 and value['overview']['markdown'].strip()
assert value['overview']['level'] == 'high'
assert all(card['markdown'].strip() for card in value['files'].values())
for path in (index, insight, cache): assert path.stat().st_mode & 0o777 == 0o600
identity = lambda path: (hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_ino, path.stat().st_mtime_ns)
before = identity(cache)
environment = {'HOME': str(root.parent), 'HERMES_HOME': str(profile),
    'PATH': str(stage / 'bin') + ':/home/lifeos-hermes/.local/bin:/usr/bin:/bin',
    'PYTHONPATH': str(stage / 'package/hermes'), 'LANG': 'C.UTF-8', 'TZ': 'America/Toronto',
    'LIFEOS_DIR': str(root / 'LIFEOS'), 'LIFEOS_HOOK_SETTINGS': str(root / 'settings.json'),
    'LIFEOS_NOTIFICATION_CHANNEL': 'headless', 'BUN_CONFIG_NO_AUTO_INSTALL': '1',
    'PYTHONDONTWRITEBYTECODE': '1'}
configuration = (profile / 'config.yaml').read_bytes()
started = time.monotonic()
result = subprocess.run([str(stage / 'bin/hermes'), 'lifeos-job', 'algorithm-summaries'],
    env=environment, cwd=profile, capture_output=True, text=True, timeout=570)
(stage / 'installed-algorithm-cache-reuse.txt').write_text(result.stdout + result.stderr)
assert (result.returncode, result.stderr) == (0, ''), result.stdout + result.stderr
outcome = json.loads(result.stdout)
assert outcome['status'] == 'completed'
generated = json.loads(outcome['output'])
assert generated == {'hash': value['overview']['chain_hash'], 'generated': 0, 'failed': False}, generated
assert identity(cache) == before
assert (profile / 'config.yaml').read_bytes() == configuration
report = {'status': 'PASS', 'index_output_characters': len(receipt['output']),
    'index_receipt_matches_cache': True, 'conduit_theme_count': len(conduit['contentTypes']),
    'conduit_events_considered': conduit['eventsConsidered'], 'conduit_level': conduit['level'],
    'algorithm_card_count': len(value['files']), 'algorithm_overview_characters': len(value['overview']['markdown']),
    'algorithm_overview_level': value['overview']['level'], 'algorithm_cache_reuse': generated,
    'cache_reuse_seconds': round(time.monotonic() - started, 3), 'cache_bytes_and_identity_preserved': True,
    'cache_modes': '0600', 'model_configuration_unchanged': True, 'live_profile_changed': False,
    'atlas_generation_verified': False, 'wire_efforts_observed': False}
(stage / 'installed-generation-effects.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
