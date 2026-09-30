# ABOUTME: Executes one native LifeOS request under a host-bound current context policy.
# ABOUTME: Uses the governed service without importing or starting the Hermes runtime.

from __future__ import annotations

import argparse
import importlib
import json
import os
from pathlib import Path
import sys
import types

if __package__:
    from .memory_policy import SessionContext
    from .memory_service import MemoryConfiguration, MemoryService
else:
    package = types.ModuleType("lifeos_memory_plugin")
    package.__path__ = [str(Path(__file__).resolve().parent)]
    sys.modules[package.__name__] = package
    policy = importlib.import_module(package.__name__ + ".memory_policy")
    service = importlib.import_module(package.__name__ + ".memory_service")
    SessionContext, MemoryConfiguration, MemoryService = policy.SessionContext, service.MemoryConfiguration, service.MemoryService


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--configuration", type=Path, required=True)
    options = parser.parse_args()
    operation = ""
    try:
        request = json.loads(sys.stdin.read(131073))
        if not isinstance(request, dict) or set(request) != {"operation", "arguments"} or not isinstance(request["arguments"], dict):
            raise ValueError("Invalid native memory request")
        operation = request["operation"]
        context = json.loads(os.environ.get("LIFEOS_MEMORY_CONTEXT", "{}"))
        if not isinstance(context, dict) or set(context) != {"transport", "author", "destination", "visibility", "participants", "model_route", "session_id"}:
            raise ValueError("Native memory requires host-bound conversation metadata")
        if any(not isinstance(value, str) for key, value in context.items() if key != "participants"):
            raise ValueError("Invalid native conversation metadata")
        if not isinstance(context["participants"], list) or any(not isinstance(value, str) for value in context["participants"]):
            raise ValueError("Invalid native conversation audience")
        context["participants"] = tuple(context["participants"])
        result = MemoryService(MemoryConfiguration(options.configuration)).native(SessionContext(**context), request["operation"], request["arguments"])
    except (ValueError, OSError) as error:
        result = ({"results": [], "markdownBlock": "", "totalSearched": 0, "cached": False, "unavailable": str(error)}
                  if operation == "retrieve" else {"ok": False, "code": "EINVAL_PATH" if operation == "read" else "EWRITE_FAILED", "message": str(error)})
    sys.stdout.write(json.dumps(result) + "\n")


if __name__ == "__main__":
    main()
