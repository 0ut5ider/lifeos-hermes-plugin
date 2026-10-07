# ABOUTME: Isolates which field of the Hermes title request makes private FlashNext fail.
# ABOUTME: Replays the recorded body with one field changed at a time and prints only status codes.
import json, re, urllib.request, urllib.error
from pathlib import Path
token = re.findall(r'^  api_key:\s*"?([^"\s]+)"?\s*$', (Path.home() / '.hermes/config.yaml').read_text(), re.M)[0]
rows = json.load(open(Path.home() / 'route/main-requests-private.json'))
body = next(r['body'] for r in rows if r['body'].get('reasoning_effort') == 'none')
def send(variant):
    request = urllib.request.Request('http://192.168.8.90:42071/v1/chat/completions', json.dumps(variant).encode(),
        {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token})
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return response.status
    except urllib.error.HTTPError as error:
        return error.code
variants = {
    'recorded': body,
    'effort medium': {**body, 'reasoning_effort': 'medium'},
    'effort low': {**body, 'reasoning_effort': 'low'},
    'no effort': {k: v for k, v in body.items() if k != 'reasoning_effort'},
    'no response_format': {k: v for k, v in body.items() if k != 'response_format'},
    'effort medium, no response_format': {**{k: v for k, v in body.items() if k != 'response_format'}, 'reasoning_effort': 'medium'},
}
for name, variant in variants.items():
    print(name, send(variant), flush=True)
