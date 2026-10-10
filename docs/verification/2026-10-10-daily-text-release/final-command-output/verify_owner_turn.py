# ABOUTME: Verifies actual synthetic memory tool effects across two installed Hermes conversations.
# ABOUTME: Compares native stream records and process outcomes without reading memory files.
import json
from pathlib import Path

root = Path('/home/lifeos-hermes/migration/2026-10-09/daily-text-581d76a7')


def records(name):
    return [json.loads(line) for line in (root / name).read_text().splitlines()
        if line.startswith('{')]


remember = records('final-owner-turn-remember.txt')
search = records('final-owner-turn-search.txt')
processes = json.loads((root / 'final-owner-turn-processes.json').read_text())
assert len(processes) == 2 and all(item['exit_code'] == 0 for item in processes)

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
assert calls[0]['input']['content'] == 'Synthetic daily acceptance verification code is D252-TEXT-1020.'
assert calls[0]['input']['request_id'] == 'daily-final-installed-final-owner-turn-1020'
results = [item for item in remember if item['type'] == 'tool_result']
assert len(results) == 1 and not results[0]['is_error']
receipt = json.loads(results[0]['output'])
assert receipt['status'] == 'committed'
assert receipt['writer'] == 'terminal:1008'
assert receipt['source']['session'] == sessions[0]
calls = [item for item in search if item['type'] == 'tool_use']
assert calls and all(item['name'] == 'lifeos_memory_search' for item in calls)
results = [item for item in search if item['type'] == 'tool_result']
assert len(results) == len(calls) and not any(item['is_error'] for item in results)
responses = [json.loads(item['output']) for item in results]
rejected = [item for item in responses if item['status'] == 'rejected']
assert all(item['reason'] == 'Memory tool arguments contain missing or unrecognized fields' for item in rejected)
successful = [item for item in responses if item['status'] == 'ok']
assert successful and len(successful) + len(rejected) == len(responses)
found = successful[-1]
assert found['results']
match = found['results'][0]
assert match['reference'] == receipt['reference']
assert match['content'] == 'Synthetic daily acceptance verification code is D252-TEXT-1020.'
assert match['category'] == 'project' and match['project'] == 'daily-final-acceptance'
assert match['writer'] == 'terminal:1008' and match['status'] == 'active'
assert match['source']['session'] == sessions[0]
report = {'status': 'PASS', 'model': 'flashnext-w4a16-fp8ple', 'sessions': sessions,
    'reference': receipt['reference'], 'writer': receipt['writer'],
    'search_calls': len(calls), 'rejected_search_requests': rejected,
    'returned_matches': len(found['results']), 'highest_match_has_exact_saved_content': True,
    'actual_write_and_fresh_conversation_read_verified': True,
    'synthetic_data_only': True, 'live_profile_changed': False,
    'discord_delivery_verified': False, 'scheduled_work_verified': False,
    'process_elapsed_seconds': [item['elapsed_seconds'] for item in processes]}
(root / 'final-owner-turn-verification.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
