# ABOUTME: Sends the recorded Hermes title request repeatedly to measure FlashNext's failure rate.
# ABOUTME: Prints only the status of each attempt, alone and alongside a concurrent main-sized request.
import json, re, threading, urllib.request, urllib.error
from pathlib import Path
token = re.findall(r'^  api_key:\s*"?([^"\s]+)"?\s*$', (Path.home() / '.hermes/config.yaml').read_text(), re.M)[0]
rows = json.load(open(Path.home() / 'route/main-requests-private.json'))
title = next(r['body'] for r in rows if r['body'].get('reasoning_effort') == 'none')
main = next(r['body'] for r in rows if r['body'].get('tools'))
def send(body):
    request = urllib.request.Request('http://192.168.8.90:42071/v1/chat/completions', json.dumps(body).encode(),
        {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token})
    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            return response.status
    except urllib.error.HTTPError as error:
        return error.code
alone = [send(title) for _ in range(10)]
print('alone', alone, flush=True)
concurrent = []
for _ in range(5):
    worker = threading.Thread(target=send, args=(main,))
    worker.start()
    concurrent.append(send(title))
    worker.join()
print('with concurrent main request', concurrent, flush=True)
