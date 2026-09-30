# ABOUTME: Serves the shared LifeOS memory tools over MCP standard input and output.
# ABOUTME: Binds each connection to a server-selected client and rechecks grants for every call.

from __future__ import annotations

import argparse
import asyncio
import json
from functools import partial
import importlib
from pathlib import Path
import sys
import types
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
import mcp_types as protocol

if __package__:
    from .memory_service import MemoryConfiguration, MemoryService, tool_schemas
else:
    package = types.ModuleType("lifeos_memory_plugin")
    package.__path__ = [str(Path(__file__).resolve().parent)]
    sys.modules[package.__name__] = package
    service = importlib.import_module(package.__name__ + ".memory_service")
    MemoryConfiguration, MemoryService = service.MemoryConfiguration, service.MemoryService
    tool_schemas = service.tool_schemas


def create_server(configuration: Path, client: str) -> Server:
    access = MemoryService(MemoryConfiguration(configuration))

    async def list_tools(context, parameters):
        return protocol.ListToolsResult(tools=[protocol.Tool(
            name=tool["name"], description=tool["description"], input_schema=tool["parameters"],
        ) for tool in tool_schemas()])

    async def call_tool(context, parameters):
        result = await asyncio.to_thread(partial(access.call_client, client, parameters.name, parameters.arguments or {}))
        return protocol.CallToolResult(content=[protocol.TextContent(type="text", text=json.dumps(result))],
                                       structured_content=result, is_error=False)

    return Server("LifeOS memory", version="0.1.0", on_list_tools=list_tools, on_call_tool=call_tool,
                  instructions="Use current references. Report saved, rejected, conflicting, and unavailable results accurately.")


async def serve(configuration: Path, client: str) -> None:
    server = create_server(configuration, client)
    async with stdio_server() as (reader, writer):
        await server.run(reader, writer, server.create_initialization_options())


def main() -> None:
    parser = argparse.ArgumentParser(description="LifeOS memory connection selected by the installation owner")
    parser.add_argument("--configuration", type=Path, required=True)
    parser.add_argument("--client", required=True)
    arguments = parser.parse_args()
    asyncio.run(serve(arguments.configuration, arguments.client))


if __name__ == "__main__":
    main()
