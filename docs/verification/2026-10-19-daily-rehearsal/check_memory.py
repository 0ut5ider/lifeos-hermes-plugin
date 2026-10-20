# ABOUTME: Reports the HTTP memory connections of a Hermes profile and whether each stored token still binds.
# ABOUTME: Prints counts, grants, and file hashes only; it never prints a token or a token digest.
import hashlib, json, sys, time
from pathlib import Path

profile = Path(sys.argv[1])
config_path = profile / 'lifeos-memory.json'
config = json.loads(config_path.read_text())
store = json.loads((profile / 'lifeos-memory-http-credentials.json').read_text())
settings = config.get('http_mcp', {})
binding = hashlib.sha256(json.dumps([str(config_path.absolute()), config['root'], config['principal'],
                                     settings.get('epoch'), settings.get('public_url')]).encode()).hexdigest()
now = time.time()
print('root', config['root'])
print('http enabled', settings.get('enabled'), 'ownership', config.get('ownership_enabled'), 'sharing', config.get('sharing_enabled'))
print('public_url', settings.get('public_url'))
clients = {name: grant for name, grant in config.get('clients', {}).items() if grant.get('transport') == 'http'}
for name, grant in sorted(clients.items()):
    tokens = [entry for entry in store['tokens'].values() if entry.get('grant') == name]
    live = [entry for entry in tokens if entry['expires_at'] > now]
    print(f"client {name} enabled={grant.get('enabled')} read={grant.get('read')} write={grant.get('write')} "
          f"projects={grant.get('projects')} tokens={len(tokens)} live={len(live)} "
          f"bound={sum(entry.get('binding') == binding for entry in live)}")
for name in ('lifeos-memory.json', 'lifeos-memory-http-credentials.json', 'lifeos-memory-contexts.json', '.env', 'config.yaml'):
    print('sha256', name, hashlib.sha256((profile / name).read_bytes()).hexdigest()[:16])
