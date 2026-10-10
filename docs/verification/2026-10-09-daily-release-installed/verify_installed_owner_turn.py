# ABOUTME: Verifies actual synthetic memory tool effects across two installed Hermes conversations.
# ABOUTME: Compares native stream records and process outcomes without reading memory files.
import json
from pathlib import Path

root = Path(__file__).resolve().parent


def records(name):
    return [json.loads(line) for line in (root / name).read_text().splitlines()
        if line.startswith('{')]


remember = records('owner-turn-remember.txt')
search = records('owner-turn-search.txt')
processes = json.loads((root / 'owner-turn-processes.json').read_text())
assert len(processes) == 2 and all(item['exit_code'] == 0 for item in processes)
assert json.loads((root / 'applications-owner-turn-first-status.json').read_text())['exit_code'] == 0
sessions = []
for records_for_turn in (remember, search):
    initial = [item for item in records_for_turn if item['type'] == 'system']
    final = [item for item in records_for_turn if item['type'] == 'result']
    assert len(initial) == len(final) == 1
    assert initial[0]['model'] == 'flashnext-w4a16-fp8ple'
    assert final[0]['exit_code'] == 0
    assert initial[0]['session_id'] == final[0]['session_id']
    sessions.append(initial[0]['session_id'])
assert sessions[0] != sessions[1]
calls = [item for item in remember if item['type'] == 'tool_use']
assert len(calls) == 1 and calls[0]['name'] == 'lifeos_memory_remember'
assert calls[0]['input']['content'] == 'Synthetic daily acceptance verification code is D252-TEXT-4109.'
assert calls[0]['input']['request_id'] == 'daily-installed-owner-turn-4109'
results = [item for item in remember if item['type'] == 'tool_result']
assert len(results) == 1 and not results[0]['is_error']
receipt = json.loads(results[0]['output'])
assert receipt['status'] == 'committed'
assert receipt['writer'] == 'terminal:1008'
assert receipt['source']['session'] == sessions[0]
calls = [item for item in search if item['type'] == 'tool_use']
assert len(calls) == 1 and calls[0]['name'] == 'lifeos_memory_search'
results = [item for item in search if item['type'] == 'tool_result']
assert len(results) == 1 and not results[0]['is_error']
found = json.loads(results[0]['output'])
assert found['status'] == 'ok' and len(found['results']) == 1
match = found['results'][0]
assert match['reference'] == receipt['reference']
assert match['content'] == 'Synthetic daily acceptance verification code is D252-TEXT-4109.'
assert match['category'] == 'project' and match['project'] == 'daily-release-acceptance'
assert match['writer'] == 'terminal:1008' and match['status'] == 'active'
assert match['source']['session'] == sessions[0]
report = {'status': 'PASS', 'model': 'flashnext-w4a16-fp8ple', 'sessions': sessions,
    'reference': receipt['reference'], 'writer': receipt['writer'],
    'actual_write_and_fresh_conversation_read_verified': True,
    'synthetic_data_only': True, 'live_profile_changed': False,
    'discord_delivery_verified': False, 'scheduled_work_verified': False,
    'process_elapsed_seconds': [item['elapsed_seconds'] for item in processes]}
(root / 'owner-turn-verification.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
