# ABOUTME: Checks a PermissionRequest update against a disposable Hermes MCP server.
# ABOUTME: Confirms the installed bridge passes modified arguments to the real server.

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

from hermes_cli import plugins as plugins_mod
from tools.mcp_tool_discovery import register_mcp_servers
from tools.mcp_tool_lifecycle import shutdown_mcp_servers
from tools.registry import registry


SERVER = '''import json,os
from pathlib import Path
from mcp.server import MCPServer
server=MCPServer("probe")
@server.tool()
def echo(value: str) -> str:
    with Path(os.environ["PROBE_LOG"]).open("a") as stream:
        stream.write(json.dumps({"value":value})+"\\n")
    return value
server.run("stdio")
'''


def main() -> None:
    source = Path(__file__).resolve().parents[1]
    installed = Path.home() / ".hermes/plugins/lifeos-hook-bridge"
    assert (installed / "bridge.py").read_bytes() == (source / "lifeos_hook_bridge/bridge.py").read_bytes()
    with tempfile.TemporaryDirectory(prefix="lifeos-mcp-rewrite-") as directory:
        root = Path(directory)
        home = root / "hermes"
        plugin = home / "plugins/lifeos-hook-bridge"
        plugin.parent.mkdir(parents=True)
        shutil.copytree(installed, plugin)
        (home / "config.yaml").write_text("plugins:\n  enabled:\n    - lifeos-hook-bridge\n")
        tool_log = root / "tool.jsonl"
        server = root / "server.py"
        server.write_text(SERVER)
        server_config = {"command": sys.executable, "args": [str(server)], "env": {"PROBE_LOG": str(tool_log)}}
        output = {"hookSpecificOutput": {"hookEventName": "PermissionRequest", "decision": {
            "behavior": "allow", "updatedInput": {"value": "MODIFIED"},
        }}}
        hook = root / "rewrite.py"
        hook.write_text(
            "import json,sys\n"
            "assert json.load(sys.stdin)['tool_input']=={'value':'ORIGINAL'}\n"
            f"print(json.dumps({output!r}))\n"
        )
        settings = root / "settings.json"
        settings.write_text(json.dumps({"hooks": {"PermissionRequest": [{
            "matcher": "mcp__probe__echo", "hooks": [
                {"type": "command", "command": f"{sys.executable} {hook}"},
            ],
        }]}}))
        previous = {key: os.environ.get(key) for key in ("HERMES_HOME", "LIFEOS_HOOK_SETTINGS")}
        os.environ["HERMES_HOME"] = str(home)
        os.environ["LIFEOS_HOOK_SETTINGS"] = str(settings)
        try:
            plugins_mod._reset_plugin_managers_for_tests()
            tools = register_mcp_servers({"probe": server_config})
            assert "mcp__probe__echo" in tools, tools
            details = plugins_mod._get_pre_tool_call_directive_details(
                "mcp__probe__echo", {"value": "ORIGINAL"}, session_id="rewrite-mcp",
            )
            assert details.action is None, details
            assert details.modified_args == {"value": "MODIFIED"}, details
            result = json.loads(registry.dispatch("mcp__probe__echo", details.modified_args))
            calls = [json.loads(line) for line in tool_log.read_text().splitlines()]
            assert calls == [{"value": "MODIFIED"}], (result, calls)
            print(json.dumps({"effective_args": details.modified_args, "server_calls": calls}, indent=2))
        finally:
            shutdown_mcp_servers()
            plugins_mod._reset_plugin_managers_for_tests()
            for key, value in previous.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value


if __name__ == "__main__":
    main()
