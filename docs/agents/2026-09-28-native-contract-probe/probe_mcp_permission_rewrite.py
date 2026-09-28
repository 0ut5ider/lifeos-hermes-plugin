# ABOUTME: Measures Claude Code PermissionRequest updates to a disposable MCP tool call.
# ABOUTME: Runs a local stdio server and records the actual arguments received by the tool.

import json
import os
import pwd
import subprocess
import sys
import tempfile
from pathlib import Path


SERVER = '''import json,os,sys
from pathlib import Path
for line in sys.stdin:
    try:
        request=json.loads(line)
        method=request.get('method')
        if 'id' not in request:
            continue
        if method=='initialize':
            result={'protocolVersion':'2025-06-18','capabilities':{'tools':{}},'serverInfo':{'name':'parity-probe','version':'1.0.0'}}
        elif method=='tools/list':
            result={'tools':[{'name':'echo','description':'Record a value and return it','inputSchema':{'type':'object','properties':{'value':{'type':'string'}},'required':['value']}}]}
        elif method=='tools/call':
            arguments=request.get('params',{}).get('arguments',{})
            with Path(os.environ['PROBE_TOOL_LOG']).open('a') as stream: stream.write(json.dumps(arguments)+'\\n')
            result={'content':[{'type':'text','text':str(arguments.get('value',''))}]}
        else:
            result={}
        sys.stdout.write(json.dumps({'jsonrpc':'2.0','id':request['id'],'result':result})+'\\n')
        sys.stdout.flush()
    except Exception as error:
        print(str(error),file=sys.stderr)
'''


home = Path(pwd.getpwuid(os.getuid()).pw_dir)
mode = sys.argv[1] if len(sys.argv) > 1 else "allow"
with tempfile.TemporaryDirectory(prefix="parity-mcp-rewrite-", dir=home) as temporary:
    root = Path(temporary)
    server = root / "server.py"
    server.write_text(SERVER)
    tool_log = root / "tool.jsonl"
    config = root / "mcp.json"
    config.write_text(json.dumps({"mcpServers": {"probe": {
        "command": sys.executable, "args": [str(server)], "env": {"PROBE_TOOL_LOG": str(tool_log)},
    }}}))
    event_path = root / "event.json"
    post_path = root / "post.json"
    hook = root / "hook.py"
    post_hook = root / "post.py"
    hook.write_text(
        "import json,sys\nfrom pathlib import Path\n"
        "data=json.load(sys.stdin)\n"
        f"Path({str(event_path)!r}).write_text(json.dumps(data))\n"
        "decision={'behavior':'allow'}\n"
        f"if {mode!r} == 'rewrite': decision['updatedInput']={{'value':'MODIFIED'}}\n"
        "print(json.dumps({'hookSpecificOutput':{'hookEventName':'PermissionRequest',"
        "'decision':decision}}))\n"
    )
    post_hook.write_text(
        "import json,sys\nfrom pathlib import Path\n"
        f"Path({str(post_path)!r}).write_text(json.dumps(json.load(sys.stdin)))\n"
    )
    settings = root / "settings.json"
    settings.write_text(json.dumps({
        "hooks": {"PermissionRequest": [{
            "matcher": "mcp__probe__echo", "hooks": [{"type": "command", "command": f"python3 {hook}"}],
        }], "PostToolUse": [{
            "matcher": "mcp__probe__echo", "hooks": [{"type": "command", "command": f"python3 {post_hook}"}],
        }]},
        "permissions": {},
    }))
    environment = dict(os.environ)
    environment["PATH"] = f"{home / '.bun/bin'}:{home / '.local/bin'}:{environment.get('PATH', '')}"
    result = subprocess.run(
        [str(home / ".local/bin/lifeos-reference"), "-p",
         "Use the probe MCP echo tool exactly once with value ORIGINAL. Do not use other tools. Report its response.",
         "--output-format", "json", "--settings", str(settings), "--setting-sources", "",
         "--mcp-config", str(config), "--strict-mcp-config", "--permission-mode", "default",
         "--tools", "mcp__probe__echo", "--max-turns", "3"],
        cwd=root, env=environment, capture_output=True, text=True, timeout=180,
    )
    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError:
        output = {}
    event = json.loads(event_path.read_text()) if event_path.exists() else {}
    post = json.loads(post_path.read_text()) if post_path.exists() else {}
    calls = [json.loads(line) for line in tool_log.read_text().splitlines()] if tool_log.exists() else []
    print(json.dumps({
        "returncode": result.returncode,
        "mode": mode,
        "permission_hook_ran": event_path.exists(),
        "hook_tool_input": event.get("tool_input"),
        "post_tool_input": post.get("tool_input"),
        "server_calls": calls,
        "permission_denials": output.get("permission_denials"),
        "is_error": output.get("is_error"),
        "stderr_tail": result.stderr[-350:],
    }))
