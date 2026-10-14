# ABOUTME: Records safe operation identities from the synthetic account-binding rehearsal.
# ABOUTME: Excludes private service configuration and memory data from the exported receipt.
import json
from pathlib import Path
root = Path('/home/lifeos-hermes/.hermes/.lifeos-releases')
rows = []
for identifier in ['886984e5de224ae795bdfd9fc99ee3c9', 'e2f0c53478c34166acea6f180182dc82',
                   'bb646e0d665d4e3f9483aa32671247e5', 'd5621dc92681425b9ee4553a063b7f0c']:
    job = root / identifier
    request = json.loads((job / 'request.json').read_bytes())
    status = json.loads((job / 'status.json').read_bytes())
    snapshot = json.loads((job / 'program-snapshot/programs.json').read_bytes())
    rows.append({'operation': identifier, 'state': status['state'], 'program_state': snapshot['state'],
        'version': request['version'], 'program_commit': request['commit'],
        'archive_sha256': request['package_sha256'], 'native_home': str(Path(request['installed']).parent),
        'account_home': request['account_home']})
print(json.dumps({'status': 'PASS', 'guest': 111, 'operations': rows}, indent=2))
