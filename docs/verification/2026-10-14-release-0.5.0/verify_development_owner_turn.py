# ABOUTME: Verifies actual synthetic memory tool effects across two installed Hermes conversations.
# ABOUTME: Compares native stream records and process outcomes without reading memory files.
import json
from pathlib import Path

root = Path(__file__).resolve().parent


def records(name):
    return [json.loads(line) for line in (root / name).read_text().splitlines()
        if line.startswith('{')]


remember = records('release-owner-turn-remember.txt')
search = records('release-owner-turn-search.txt')
processes = json.loads((root / 'release-owner-turn-processes.json').read_text())
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
assert calls[0]['input']['content'] == 'Synthetic daily acceptance verification code is STABLE-050-DEV-04EFE633.'
assert calls[0]['input']['request_id'] == 'stable-050-dev-04efe633'
results = [item for item in remember if item['type'] == 'tool_result']
assert len(results) == 1 and not results[0]['is_error']
receipt = json.loads(results[0]['output'])
assert receipt['status'] == 'committed'
assert receipt['writer'] == 'terminal:1008'
assert receipt['source']['session'] == sessions[0]
calls = [item for item in search if item['type'] == 'tool_use']
assert calls and all(item['name'] == 'lifeos_memory_search' for item in calls)
results = [item for item in search if item['type'] == 'tool_result']
assert len(results) == len(calls) and all(not item['is_error'] for item in results)
responses = [json.loads(item['output']) for item in results]
assert responses and responses[-1]['status'] == 'ok'
argument_refusals = successful_searches = 0
for found in responses:
    if found == {'status': 'rejected', 'reason': 'Memory tool arguments contain missing or unrecognized fields'}:
        argument_refusals += 1
        continue
    assert found['status'] == 'ok' and len(found['results']) == 1
    match = found['results'][0]
    assert match['reference'] == receipt['reference']
    assert match['content'] == 'Synthetic daily acceptance verification code is STABLE-050-DEV-04EFE633.'
    assert match['category'] == 'project' and match['project'] == 'release-0.5.0-qualification'
    assert match['writer'] == 'terminal:1008' and match['status'] == 'active'
    assert match['source']['session'] == sessions[0]
    successful_searches += 1
assert successful_searches > 0
report = {'status': 'PASS', 'model': 'flashnext-w4a16-fp8ple', 'sessions': sessions,
    'reference': receipt['reference'], 'writer': receipt['writer'],
    'actual_write_and_fresh_conversation_read_verified': True,
    'synthetic_data_only': True, 'development_profile_only': True, 'daily_server_changed': False,
    'discord_delivery_verified': False, 'scheduled_work_verified': False,
    'search_argument_refusals': argument_refusals, 'successful_searches': successful_searches,
    'process_elapsed_seconds': [item['elapsed_seconds'] for item in processes]}
identity = json.loads((Path.home() / '.hermes/integration-release.json').read_bytes())
assert identity['version'] == '0.5.0' and identity['commit'] == '04efe633296eb2b1a1d95561ca6d3e9516cd47dc'
assert identity['package_sha256'] == 'a6dd0e11b8fb1b5ae30345be20c955db02728839f7bc907f60a70944ad392813'
report['verification_active_identity'] = {key: identity[key] for key in ('version', 'commit', 'package_sha256')}
(root / 'release-owner-turn-verification.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
