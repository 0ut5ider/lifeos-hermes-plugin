# ABOUTME: Prepares and checks inert Content data in the isolated synthetic acceptance store.
# ABOUTME: Verifies native browser action effects without decoding media or reading live memory.
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys

stage = Path('/home/lifeos-hermes/migration/2026-10-09/daily-text-581d76a7')
root = Path(json.loads((stage / 'applications-prepared.json').read_text())['installed'])
os.umask(0o077)
identifier = 'dailysynthetic4115'
source = root.parent / 'Recordings/Inbox/daily-browser-fifth-synthetic.wav'
sidecar = Path(str(source) + '.md')
artifact = root / ('LIFEOS/MEMORY/STATE/content-pipeline/artifacts/' + identifier + '/transcript.md')
ledger = root / 'LIFEOS/MEMORY/STATE/content-pipeline/events.jsonl'
prepared = stage / 'installed-browser-content-fifth-fixture.json'
sha = lambda content: hashlib.sha256(content).hexdigest()
if sys.argv[1:] == ['prepare']:
    assert not prepared.exists()
    for path in (source, sidecar, artifact): assert not path.exists()
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_bytes(b'Synthetic browser Content fixture. No media decoding.\n')
    sidecar.write_text('Synthetic browser sidecar.\n')
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text('Synthetic browser derivative.\n')
    row = {'v': 1, 'ts': datetime.now(timezone.utc).isoformat(), 'id': identifier,
        'op': 'upsert', 'src': 'synthetic-acceptance', 'fields': {'id': identifier,
        'title': 'Synthetic browser fifth Content acceptance', 'path': str(source),
        'created': datetime.now(timezone.utc).isoformat(), 'stage': 'inbox',
        'stage_status': 'pending', 'requested_run': None}}
    with ledger.open('a') as stream: stream.write(json.dumps(row) + '\n')
    value = {'identifier': identifier, 'source_sha256': sha(source.read_bytes()),
        'sidecar_sha256': sha(sidecar.read_bytes()), 'ledger_bytes': ledger.stat().st_size,
        'ledger_sha256': sha(ledger.read_bytes())}
    prepared.write_text(json.dumps(value, indent=2) + '\n')
    print(json.dumps({'prepared': True, 'identifier': identifier}))
elif sys.argv[1:] == ['verify']:
    value = json.loads(prepared.read_text())
    after = ledger.read_bytes()
    assert sha(after[:value['ledger_bytes']]) == value['ledger_sha256']
    assert not source.exists() and not sidecar.exists() and not artifact.parent.exists()
    assert sha((source.parent / '.trash' / source.name).read_bytes()) == value['source_sha256']
    assert sha((sidecar.parent / '.trash' / sidecar.name).read_bytes()) == value['sidecar_sha256']
    events = [json.loads(line) for line in after[value['ledger_bytes']:].decode().splitlines()]
    events = [row for row in events if row['id'] == identifier]
    assert len(events) == 2 and [row['op'] for row in events] == ['upsert', 'delete'], events
    assert events[0]['fields']['requested_run'] == 'regular', events
    report = {'status': 'PASS', 'run_and_disposal_events': events, 'prior_ledger_preserved': True,
        'source_and_sidecar_trashed_intact': True, 'derivatives_removed': True,
        'media_processing_verified': False, 'live_profile_changed': False}
    (stage / 'installed-browser-content-fifth-effects.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))
else:
    raise ValueError('Choose prepare or verify')
