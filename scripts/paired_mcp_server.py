# ABOUTME: Exposes one synthetic Model Context Protocol tool for paired hook runs.
# ABOUTME: Uses newline JSON over stdio so both isolated accounts need no package install.

from __future__ import annotations

import json
import os
import sys


TOOL = {
    "name": "ping",
    "description": "Return the fixed PAIR_MCP_212 marker.",
    "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
}


def respond(request: dict) -> dict | None:
    identifier = request.get("id")
    if identifier is None:
        return None
    method = request.get("method")
    if method == "initialize":
        result = {
            "protocolVersion": request.get("params", {}).get("protocolVersion", "2025-03-26"),
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "lifeos-paired-probe", "version": "1.0.0"},
        }
    elif method == "tools/list":
        count = min(max(int(os.environ.get("PAIRED_MCP_TOOL_COUNT", "1")), 1), 150)
        result = {"tools": [TOOL, *(
            {**TOOL, "name": f"reference_{index:03d}"} for index in range(1, count)
        )]}
    elif method == "tools/call" and request.get("params", {}).get("name") == "ping":
        result = {"content": [{"type": "text", "text": "PAIR_MCP_212"}], "isError": False}
    else:
        return {"jsonrpc": "2.0", "id": identifier,
                "error": {"code": -32601, "message": "Method not found"}}
    return {"jsonrpc": "2.0", "id": identifier, "result": result}


def main() -> None:
    for line in sys.stdin:
        try:
            response = respond(json.loads(line))
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        if response is not None:
            print(json.dumps(response), flush=True)


if __name__ == "__main__":
    main()
