# ABOUTME: Verifies actual native learning and fresh recall before and after provider return.
# ABOUTME: Retains raw model output privately and exports actual tool status and fact references.
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import time

from model_turn_assertions import verified_search

parser = argparse.ArgumentParser()
parser.add_argument('phase', choices=('learn', 'native-read', 'builtin-read'))
args = parser.parse_args()
home = Path('/home/lifeos-hermes')
profile = home / '.hermes'
assert os.getuid() == 1000 and Path.home() == home
os.umask(0o077)
output = home / 'install-input/model-turns' / ('native-learning-' + args.phase)
output.mkdir(mode=0o700)
fact = 'Synthetic fact learned while LifeOS owns memory is D244-NATIVE-LEARNED-1015.'
arguments = {'category': 'project', 'content': fact, 'title': 'Synthetic native learning acceptance',
    'project': 'portability-acceptance', 'request_id': 'native-learning-1015'}
queries = {
    'learn': 'Use lifeos_memory_remember exactly once with these exact arguments: ' + json.dumps(arguments)
        + '. Report only the actual tool status and reference. Do not use shell or files.',
    'native-read': 'Use lifeos_memory_search exactly once with query "synthetic fact learned while LifeOS owns memory". '
        'Return the matched fact and its reference. Do not use shell, files, or earlier chat history.',
    'builtin-read': 'What is the synthetic fact learned while LifeOS owned your lasting memory? '
        'Answer only its marker. Do not use tools, shell, files, or earlier chat history.'}
query = output / 'query.txt'
query.write_text(queries[args.phase] + '\n')
started = time.monotonic()
receipt = {'status': 'FAIL', 'phase': args.phase, 'fresh_session': True, 'daily_changed': False}
try:
    with (output / 'stdout.jsonl').open('wb') as stdout, (output / 'stderr.txt').open('wb') as stderr:
        result = subprocess.run([str(home / '.local/bin/hermes'), 'chat', '--query-file', str(query),
            '--oneshot', '--format', 'stream-json', '--max-turns', '4', '--run-budget', '120'],
            cwd=profile, stdout=stdout, stderr=stderr, timeout=180)
    events = []
    for line in (output / 'stdout.jsonl').read_text().splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if isinstance(event, dict):
            events.append(event)
    final = next((e for e in reversed(events) if e.get('type') == 'result'), {})
    calls = [e for e in events if e.get('type') == 'tool_use']
    results = [e for e in events if e.get('type') == 'tool_result']
    names = [e.get('name') for e in calls]
    expected = 'D244-NATIVE-LEARNED-1015'
    if args.phase == 'learn':
        actual = json.loads(results[0]['output']) if len(results) == 1 else {}
        reference = actual.get('reference', {})
        proof = (names == ['lifeos_memory_remember'] and calls[0].get('input') == arguments
            and len(results) == 1 and results[0].get('is_error') is False
            and results[0].get('name') == 'lifeos_memory_remember' and actual.get('status') == 'committed'
            and isinstance(reference.get('id'), str) and re.fullmatch('[0-9a-f]{32}', reference['id']) is not None
            and type(reference.get('revision')) is int and reference['revision'] > 0)
        receipt.update(actual_tool_status=actual.get('status'), reference=reference,
            exact_arguments=calls[0].get('input') == arguments if calls else False)
    elif args.phase == 'native-read':
        verified = verified_search(events, expected)
        proof = names == ['lifeos_memory_search'] and verified['verified'] and expected in final.get('text', '')
        receipt['actual_search'] = verified
    else:
        proof = not names and expected in final.get('text', '')
    receipt.update(exit_code=result.returncode, session_id=final.get('session_id'), tool_names=names,
        model_turn_executed=final.get('tokens', {}).get('output', 0) > 0, actual_proof=bool(proof))
    if result.returncode == 0 and final.get('exit_code') == 0 and receipt['model_turn_executed'] and proof:
        receipt['status'] = 'PASS'
except Exception as error:
    receipt['error_type'] = type(error).__name__
finally:
    receipt['elapsed_seconds'] = time.monotonic() - started
    (output / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    (output / 'observation.done').write_text('0\n' if receipt['status'] == 'PASS' else '1\n')
print(json.dumps(receipt))
raise SystemExit(0 if receipt['status'] == 'PASS' else 1)
