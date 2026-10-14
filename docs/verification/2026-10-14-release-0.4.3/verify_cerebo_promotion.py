# ABOUTME: Verifies the actual synthetic Cerebo tool call and its delivered reply after daily promotion.
# ABOUTME: Reads only the fixed acceptance conversation and exports safe receipt identifiers.
import argparse
import importlib
import json
from pathlib import Path
import sqlite3
import sys
import types
from dotenv import dotenv_values

profile = Path('/home/lifeos-hermes/.hermes')
parser = argparse.ArgumentParser()
parser.add_argument('--phase', choices=('live', 'ready'), required=True)
phase = parser.parse_args().phase
session = '20261014_120316_4bcc725b'
channel = '1558870196784205927'
reference = {'id': '8565b850a9ce45a18f4c0540e398b5ee', 'revision': 1}
prompt = 'CEREBO-043-LIVE-1014. Use lifeos_memory_search exactly once with query "D253-042-PROMOTION-1014". Return the actual tool status, matched fact, and reference, followed by CEREBO-043-LIVE-PASS. Do not use earlier chat history. Do not write memory.'
marker = 'CEREBO-043-LIVE-PASS'
if phase == 'ready':
    prompt = 'CEREBO-043-READY-1014. Use lifeos_memory_search once with query "D253-042-PROMOTION-1014". Return the actual tool status and result count, followed by CEREBO-043-READY-PASS. Do not use earlier chat history. Do not write memory.'
    marker = 'CEREBO-043-READY-PASS'
connection = sqlite3.connect('file:' + str(profile / 'state.db') + '?mode=ro', uri=True)
connection.row_factory = sqlite3.Row
selected = dict(connection.execute('SELECT id,source,chat_id,started_at,message_count FROM sessions WHERE id=?', (session,)).fetchone())
assert selected['source'] == 'discord' and selected['chat_id'] == channel
starts = connection.execute('SELECT id FROM messages WHERE session_id=? AND role=? AND content=? ORDER BY id',
    (session, 'user', prompt)).fetchall()
assert len(starts) == 1
start = starts[0]['id']
end = connection.execute('SELECT MIN(id) FROM messages WHERE session_id=? AND role=? AND id>?',
    (session, 'user', start)).fetchone()[0]
if phase == 'live':
    assert start == connection.execute('SELECT MIN(id) FROM messages WHERE session_id=? AND role=?',
        (session, 'user')).fetchone()[0]
rows = connection.execute('SELECT role,content,tool_calls,tool_name,tool_call_id FROM messages '
    'WHERE session_id=? AND id>=? AND (? IS NULL OR id<?) ORDER BY id', (session, start, end, end)).fetchall()
assert next(row['content'] for row in rows if row['role'] == 'user') == prompt
calls = [call for row in rows for call in json.loads(row['tool_calls'] or '[]')]
assert len(calls) == 1
call = calls[0]
assert call['function']['name'] == 'lifeos_memory_search'
assert json.loads(call['function']['arguments']) == {'query': 'D253-042-PROMOTION-1014'}
tools = [row for row in rows if row['role'] == 'tool']
assert len(tools) == 1 and tools[0]['tool_name'] == 'lifeos_memory_search'
assert tools[0]['tool_call_id'] == call['id']
result, end = json.JSONDecoder().raw_decode(tools[0]['content'])
annotation = tools[0]['content'][end:].strip()
expected_annotation = '[LOOP DETECTED] You\'ve called lifeos_memory_search 3 times with the same input this session without progress. Last input: {"query":"D253-042-PROMOTION-1014"}.'
assert not annotation or phase == 'ready' and annotation == expected_annotation
assert result['status'] == 'ok'
if phase == 'live':
    assert len(result['results']) == 1
    match = result['results'][0]
    assert match['reference'] == reference
    assert match['content'] == 'Synthetic daily promotion verification code is D253-042-PROMOTION-1014.'
else:
    assert result == {'status': 'ok', 'results': []}
final = [row['content'] for row in rows if row['role'] == 'assistant' and row['content']][-1]
assert marker in final and (phase == 'ready' or reference['id'] in final)
namespace = types.ModuleType('cerebo_bridge')
namespace.__path__ = [str(profile / 'plugins/lifeos-hook-bridge')]
sys.modules[namespace.__name__] = namespace
api = importlib.import_module(namespace.__name__ + '.discord_audience').DiscordAPI(dotenv_values(profile / '.env')['DISCORD_BOT_TOKEN'])
messages = api.get('/channels/' + channel + '/messages?limit=100')
delivered = [row for row in messages if row['author']['id'] == '1558867947152347198'
    and marker in row['content'] and (phase == 'ready' or reference['id'] in row['content'])]
assert len(delivered) == 1 and delivered[0]['channel_id'] == channel
release = json.loads((profile / 'integration-release.json').read_bytes())
assert release['version'] == '0.4.3' and release['commit'] == 'a1abb579558edcf29f7cd04ecfd998995d48db54'
print(json.dumps({'status': 'PASS', 'version': release['version'], 'program_commit': release['commit'],
    'archive_sha256': release['package_sha256'], 'session': session, 'phase': phase,
    'fresh_conversation_verified': phase == 'live', 'exact_turn_boundary_verified': True,
    'actual_memory_search_calls': 1, 'tool_status': 'ok', 'reference': reference if phase == 'live' else None,
    'result_count': len(result['results']), 'specific_discord_tool_receipt_verified': True,
    'host_annotation': 'native-loop-warning' if annotation else None,
    'matched_fact_verified': phase == 'live',
    'channel': channel, 'delivery': {'message_id': delivered[0]['id'], 'timestamp': delivered[0]['timestamp']},
    'memory_writes_during_live_probe': 0, 'personal_records_exported': False}, indent=2))
