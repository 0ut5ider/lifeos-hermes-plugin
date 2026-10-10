# ABOUTME: Temporarily revokes the synthetic dashboard binding for a real browser refusal check.
# ABOUTME: Restores the retained binding and verifies that the rejected action leaves its fixture unchanged.
import importlib
import json
import os
from pathlib import Path
import sys

stage = Path('/home/lifeos-hermes/migration/2026-10-09/daily-text-581d76a7')
prepared = json.loads((stage / 'applications-prepared.json').read_text())
profile, root = Path(prepared['profile']), Path(prepared['installed'])
os.umask(0o077)
sys.path.insert(0, str(profile / 'plugins'))
configuration = importlib.import_module('lifeos-hook-bridge.memory_service').MemoryConfiguration(profile / 'lifeos-memory.json')
account = 'dashboard:basic:acceptance-owner'
retained = stage / 'browser-denial-binding-second.json'
if sys.argv[1:] == ['revoke']:
    assert not retained.exists()
    retained.write_text(json.dumps(configuration.load()['accounts'][account]) + '\n')
    configuration.update(lambda value: value['accounts'].pop(account))
    assert account not in configuration.load()['accounts']
elif sys.argv[1:] == ['restore']:
    binding = json.loads(retained.read_text())
    configuration.update(lambda value: value['accounts'].update({account: binding}))
    assert configuration.load()['accounts'][account] == binding
elif sys.argv[1:] == ['check']:
    import hashlib
    fixture = json.loads((stage / 'installed-browser-content-seventh-fixture.json').read_text())
    ledger = root / 'LIFEOS/MEMORY/STATE/content-pipeline/events.jsonl'
    assert hashlib.sha256(ledger.read_bytes()).hexdigest() == fixture['ledger_sha256']
    source = root.parent / 'Recordings/Inbox/daily-browser-seventh-synthetic.wav'
    assert source.exists()
else:
    raise ValueError('Choose revoke, restore, or check')
print(json.dumps({'status': 'PASS', 'operation': sys.argv[1], 'live_profile_changed': False}))
