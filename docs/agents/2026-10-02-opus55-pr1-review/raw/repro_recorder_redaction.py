# ABOUTME: Probes development recorder redaction against synthetic credential-like environment names.
# ABOUTME: Prints which synthetic values survive the recorder's safe() projection.
import json, sys
sys.path.insert(0, 'development')
from hook_capture.store import safe, declared_secrets
environment = {
    'OPENROUTER_API_KEY': 'synthetic-value-a1', 'ANTHROPIC_AUTH_TOKEN': 'synthetic-value-a2',
    'ANTHROPIC_KEY': 'synthetic-value-b1', 'GH_PAT': 'synthetic-value-b2', 'SSH_PASSPHRASE': 'synthetic-value-b3',
    'SLACK_WEBHOOK_URL': 'https://hooks.slack.com/services/T000/B000/synthetic-value-b4',
    'DATABASE_URL': 'postgres://user:synthetic-value-b5@localhost/db',
}
captured = {'argv': ['bun', 'hook.ts'], 'options': {'env': environment}}
secrets = list(declared_secrets(captured))
projected = json.dumps(safe(captured, secrets))
print(json.dumps({name: ('redacted' if value not in projected else 'RETAINED') for name, value in environment.items()}, indent=2))
