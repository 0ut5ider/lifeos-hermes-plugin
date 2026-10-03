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

REQUEST_LIMIT = 131072
DIAGNOSTIC_REQUEST_LIMIT = 3 * 1024 * 1024

if __package__:
    from .memory_context import parse_context
    from .memory_service import MemoryConfiguration, MemoryService
else:
    package = types.ModuleType("lifeos_memory_plugin")
    package.__path__ = [str(Path(__file__).resolve().parent)]
    sys.modules[package.__name__] = package
    policy = importlib.import_module(package.__name__ + ".memory_context")
    service = importlib.import_module(package.__name__ + ".memory_service")
    parse_context, MemoryConfiguration, MemoryService = policy.parse_context, service.MemoryConfiguration, service.MemoryService


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--configuration", type=Path, required=True)
    options = parser.parse_args()
    operation = ""
    try:
        wire = sys.stdin.buffer.read(DIAGNOSTIC_REQUEST_LIMIT + 1)
        if len(wire) > DIAGNOSTIC_REQUEST_LIMIT:
            raise ValueError('The native memory request exceeds the input limit')
        request = json.loads(wire)
        if not isinstance(request, dict) or set(request) != {"operation", "arguments"} or not isinstance(request["arguments"], dict):
            raise ValueError("Invalid native memory request")
        operation = request["operation"]
        if operation != 'filter_diagnostic' and len(wire) > REQUEST_LIMIT:
            raise ValueError('The native memory request exceeds the input limit')
        if operation == 'pulse_http':
            http = importlib.import_module((__package__ or 'lifeos_memory_plugin') + '.memory_http')
            result = http.relay(MemoryConfiguration(options.configuration), request['arguments'])
        elif 'LIFEOS_MEMORY_ADMINISTRATION' in os.environ:
            result = MemoryService(MemoryConfiguration(options.configuration)).administrative(
                os.environ['LIFEOS_MEMORY_ADMINISTRATION'], request['operation'], request['arguments'])
        else:
            context = parse_context(json.loads(os.environ.get("LIFEOS_MEMORY_CONTEXT", "{}")))
            result = MemoryService(MemoryConfiguration(options.configuration)).native(context, request["operation"], request["arguments"])
    except (ValueError, OSError) as error:
        result = ({"results": [], "markdownBlock": "", "totalSearched": 0, "cached": False, "unavailable": str(error)}
                  if operation == "retrieve" else {"ok": False, "code": "EINVAL_PATH" if operation == "read" else "EWRITE_FAILED", "message": str(error)})
    sys.stdout.write(json.dumps(result) + "\n")


if __name__ == "__main__":
    main()
