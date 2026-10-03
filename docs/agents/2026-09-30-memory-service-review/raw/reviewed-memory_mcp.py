# ABOUTME: Serves the shared LifeOS memory tools over MCP standard input and output.
# ABOUTME: Binds each connection to a server-selected client and rechecks grants for every call.

from __future__ import annotations

import argparse
import importlib
from pathlib import Path
import sys
import types
from typing import Any

from mcp.server import MCPServer

if __package__:
    from .memory_service import MemoryConfiguration, MemoryService
else:
    package = types.ModuleType("lifeos_memory_plugin")
    package.__path__ = [str(Path(__file__).resolve().parent)]
    sys.modules[package.__name__] = package
    service = importlib.import_module(package.__name__ + ".memory_service")
    MemoryConfiguration, MemoryService = service.MemoryConfiguration, service.MemoryService


def create_server(configuration: Path, client: str) -> MCPServer:
    access = MemoryService(MemoryConfiguration(configuration))
    server = MCPServer("LifeOS memory", version="0.1.0", log_level="ERROR",
                       instructions="Use current references. Report saved, rejected, conflicting, and unavailable results accurately.")

    @server.tool()
    def lifeos_memory_status() -> dict[str, Any]:
        """Check this connection's lasting memory access and availability."""
        return access.call_client(client, "lifeos_memory_status", {})

    @server.tool()
    def lifeos_memory_search(query: str, limit: int = 20) -> dict[str, Any]:
        """Find permitted current facts and their references."""
        return access.call_client(client, "lifeos_memory_search", {"query": query, "limit": limit})

    @server.tool()
    def lifeos_memory_get(reference: dict[str, Any]) -> dict[str, Any]:
        """Read one current fact by its returned reference."""
        return access.call_client(client, "lifeos_memory_get", {"reference": reference})

    @server.tool()
    def lifeos_memory_remember(category: str, content: str, title: str, project: str, request_id: str) -> dict[str, Any]:
        """Save a permitted fact. Reuse request_id only for an identical retry."""
        return access.call_client(client, "lifeos_memory_remember", {
            "category": category, "content": content, "title": title, "project": project, "request_id": request_id,
        })

    @server.tool()
    def lifeos_memory_correct(reference: dict[str, Any], content: str, request_id: str) -> dict[str, Any]:
        """Correct one current fact. The superseded fact leaves ordinary recall."""
        return access.call_client(client, "lifeos_memory_correct", {
            "reference": reference, "content": content, "request_id": request_id,
        })

    @server.tool()
    def lifeos_memory_forget(reference: dict[str, Any], request_id: str) -> dict[str, Any]:
        """Exclude a fact from ordinary recall. Retained history and backups are not erased."""
        return access.call_client(client, "lifeos_memory_forget", {"reference": reference, "request_id": request_id})

    return server


def main() -> None:
    parser = argparse.ArgumentParser(description="LifeOS memory connection selected by the installation owner")
    parser.add_argument("--configuration", type=Path, required=True)
    parser.add_argument("--client", required=True)
    arguments = parser.parse_args()
    create_server(arguments.configuration, arguments.client).run(transport="stdio")


if __name__ == "__main__":
    main()
