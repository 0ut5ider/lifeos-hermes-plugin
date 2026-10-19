# ABOUTME: Calls the LifeOS HTTP memory MCP endpoint with a bearer token and reports status and search results.
# ABOUTME: Usage: mcp_probe.py <base-url> <host-header> <token-file> <query>; prints tool status only.
import json, sys, urllib.request

base, host, token_file, query = sys.argv[1:5]
token = open(token_file).read().strip()
url = base + '/api/plugins/lifeos-hook-bridge/memory/http/mcp'
session = None

def call(method, params=None, ident=None):
    global session
    body = {'jsonrpc': '2.0', 'method': method}
    if params is not None: body['params'] = params
    if ident is not None: body['id'] = ident
    headers = {'Authorization': 'Bearer ' + token, 'Host': host, 'Content-Type': 'application/json',
               'Accept': 'application/json, text/event-stream', 'MCP-Protocol-Version': '2025-06-18'}
    if session: headers['Mcp-Session-Id'] = session
    request = urllib.request.Request(url, json.dumps(body).encode(), headers, method='POST')
    with urllib.request.urlopen(request, timeout=60) as response:
        session = response.headers.get('Mcp-Session-Id') or session
        text = response.read().decode()
    if ident is None: return None
    for line in text.splitlines():
        if line.startswith('data:'): return json.loads(line[5:])
    return json.loads(text)

init = call('initialize', {'protocolVersion': '2025-06-18', 'capabilities': {},
                           'clientInfo': {'name': 'rehearsal-probe', 'version': '1'}}, 1)
print('server', init['result']['serverInfo']['name'])
call('notifications/initialized')
for ident, (name, arguments) in enumerate([('lifeos_memory_status', {}),
                                           ('lifeos_memory_search', {'query': query, 'limit': 3})], 2):
    result = call('tools/call', {'name': name, 'arguments': arguments}, ident)['result']
    payload = json.loads(result['content'][0]['text'])
    print(name, 'status', payload.get('status'), 'results', len(payload.get('results', [])),
          {k: payload[k] for k in ('read', 'write', 'projects') if k in payload})
