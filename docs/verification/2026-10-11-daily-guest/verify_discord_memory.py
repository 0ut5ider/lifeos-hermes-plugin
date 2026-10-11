# ABOUTME: Verifies actual Cerebo memory tools in two separate synthetic Discord sessions.
# ABOUTME: Retains scoped tool receipts and confirms governed cleanup before daily use.
import importlib
import json
import os
from pathlib import Path
import sqlite3
import sys
import urllib.request

from dotenv import dotenv_values

home = Path('/home/lifeos-hermes')
profile = home / '.hermes'
evidence = home / 'deployment/2026-10-11'
os.umask(0o077)
os.environ.update(json.loads((evidence / 'environment.json').read_text()))
sys.path[:0] = [str(profile / 'plugins'), str(home / 'runtime/hermes')]
module = lambda name: importlib.import_module('lifeos-hook-bridge.' + name)
saved_session = '20261011_133758_2630a29c'
recall_session = '20261011_133952_a6694676'
prior_session = '20261011_121558_feea1717'
content = 'Synthetic daily setup verification code is D253-CEREBO-1011.'
states = json.loads((profile / 'lifeos-memory-contexts.json').read_text())
assert prior_session not in states
assert saved_session in states and recall_session in states
connection = sqlite3.connect('file:' + str(profile / 'state.db') + '?mode=ro', uri=True)
connection.row_factory = sqlite3.Row
sessions = []
receipts = []
for session_id in (saved_session, recall_session):
    row = dict(connection.execute('SELECT id,source,chat_id,parent_session_id,started_at,ended_at,'
        'end_reason,message_count,tool_call_count FROM sessions WHERE id=?', (session_id,)).fetchone())
    assert row['source'] == 'discord' and row['chat_id'] == '1558870196784205927'
    sessions.append(row)
    rows = connection.execute('SELECT role,content,tool_calls,tool_name,tool_call_id FROM messages '
        'WHERE session_id=? ORDER BY id', (session_id,)).fetchall()
    if session_id == recall_session:
        first_user = next(item['content'] for item in rows if item['role'] == 'user')
        assert first_user == ('Use lifeos_memory_search to find D253-CEREBO-1011. '
            'Return the matched fact and reference. Do not use earlier chat history.')
    calls = {}
    for item in rows:
        for call in json.loads(item['tool_calls'] or '[]'):
            calls[call['id']] = {'name': call['function']['name'],
                'arguments': json.loads(call['function']['arguments'])}
        if item['role'] == 'tool':
            call = calls[item['tool_call_id']]
            assert call['name'] == item['tool_name']
            result, offset = json.JSONDecoder().raw_decode(item['content'])
            annotation = item['content'][offset:].strip()
            assert not annotation or annotation.startswith('[LOOP DETECTED]')
            receipts.append({'session_id': session_id, **call, 'result': result,
                'host_annotation': annotation})

assert [row['name'] for row in receipts] == ['lifeos_memory_remember', 'lifeos_memory_search',
    'lifeos_memory_forget', 'lifeos_memory_search']
saved, recalled, forgotten, cleared = receipts
assert saved['arguments'] == {'category': 'project', 'content': content,
    'title': 'Synthetic daily setup acceptance', 'project': 'daily-release-acceptance',
    'request_id': 'daily-discord-acceptance-1011'}
assert saved['result']['status'] == 'committed'
reference = saved['result']['reference']
assert reference == {'id': '5ef768b788a94926ab2b889689f64f91', 'revision': 1}
assert saved['result']['source']['session'] == saved_session
assert recalled['result']['status'] == 'ok' and len(recalled['result']['results']) == 1
match = recalled['result']['results'][0]
assert match['reference'] == reference and match['content'] == content
assert match['source']['session'] == saved_session and match['status'] == 'active'
assert sessions[0]['end_reason'] == 'session_reset'
assert sessions[1]['end_reason'] == 'session_reset'
assert saved_session != recall_session
assert forgotten['arguments'] == {'reference': reference, 'request_id': 'daily-discord-cleanup-1011'}
assert forgotten['result']['status'] == 'committed'
assert forgotten['result']['reference'] == {'id': reference['id'], 'revision': 2}
assert cleared['result'] == {'status': 'ok', 'results': []}
for searched in (recalled, cleared):
    assert searched['arguments']['query'] == 'D253-CEREBO-1011'
fresh = dict(connection.execute('SELECT id,started_at,message_count FROM sessions '
    "WHERE source='discord' AND chat_id='1558870196784205927' ORDER BY started_at DESC LIMIT 1").fetchone())
assert fresh['id'] not in (saved_session, recall_session, prior_session)
assert fresh['message_count'] == 0 and fresh['started_at'] >= sessions[1]['ended_at']
message_ids = {'save': '1558896828135641200', 'recall': '1558897345184403457',
    'cleanup': '1558897747703373856', 'fresh_reset': '1558898016637952093'}
request = urllib.request.Request(
    'https://discord.com/api/v10/channels/1558870196784205927/messages?limit=100',
    headers={'Authorization': 'Bot ' + dotenv_values(profile / '.env')['DISCORD_BOT_TOKEN'],
        'User-Agent': 'LifeOS-Deployment/1.0'})
with urllib.request.urlopen(request, timeout=15) as response:
    messages = {row['id']: row for row in json.load(response)}
delivered = {}
for phase, message_id in message_ids.items():
    row = messages[message_id]
    assert row['author']['id'] == '1558867947152347198'
    assert row['channel_id'] == '1558870196784205927'
    delivered[phase] = {'message_id': message_id, 'timestamp': row['timestamp'],
        'content': row['content']}
assert reference['id'] in delivered['save']['content']
assert reference['id'] in delivered['recall']['content'] and content in delivered['recall']['content']
assert 'result count 0' in delivered['cleanup']['content']
assert 'Session reset! Starting fresh.' in delivered['fresh_reset']['content']

selected = module('memory_service').MemoryConfiguration(profile / 'lifeos-memory.json').load()
assert selected['ownership_enabled'] and not selected['sharing_enabled']
memory = module('memory_access').NativeMemory(Path(selected['root']))
with memory._transaction() as native:
    active = native.execute("SELECT COUNT(*) FROM records WHERE status='active'").fetchone()[0]
report = {'status': 'PASS', 'save_session': saved_session, 'recall_session': recall_session,
    'separate_sessions_verified': True, 'exact_save_call_count': 1, 'save_status': 'committed',
    'recall_status': 'ok', 'reference': reference, 'exact_content_recalled': True,
    'cleanup_status': 'committed', 'post_cleanup_search_results': 0, 'active_facts': active,
    'prior_unverified_session_refused': prior_session, 'prior_session_has_verified_context': False,
    'sessions': sessions, 'fresh_daily_session': fresh, 'discord_delivery': delivered,
    'tool_receipts': receipts}
(evidence / 'discord-memory-verification.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
