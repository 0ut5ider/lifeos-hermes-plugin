# ABOUTME: Exposes an actual failing MCP protocol operation for synthetic audit controls.
# ABOUTME: Shares the established discovery protocol and returns a bounded fixture error.
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.paired_mcp_server import respond

for line in sys.stdin:
    request = json.loads(line)
    if request.get('method') == 'tools/call':
        response = {'jsonrpc': '2.0', 'id': request['id'], 'error': {'code': -32000, 'message': 'PAIR_ACTUAL_MCP_FAILURE'}}
    else:
        response = respond(request)
    if response is not None:
        print(json.dumps(response), flush=True)
