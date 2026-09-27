# ABOUTME: Registers LifeOS hook callbacks with the Hermes plugin manager.
# ABOUTME: Loads the installed Claude hook settings from the LifeOS account.

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .bridge import HookBridge


def register(ctx: Any) -> None:
    settings = Path(os.environ.get("LIFEOS_HOOK_SETTINGS", str(Path.home() / ".claude/settings.json"))).expanduser()
    if not settings.is_file():
        raise FileNotFoundError(f"LifeOS Claude hook settings not found: {settings}")
    bridge = HookBridge(settings, settings.parent)
    ctx.register_hook("pre_tool_call", bridge.pre_tool_call)
    ctx.register_hook("pre_command_approval", bridge.command_approval)
    ctx.register_hook("augment_tool_result", bridge.augment_tool_result)
    ctx.register_hook("pre_llm_call", bridge.pre_llm_call)
    ctx.register_hook("pre_turn_stop", lambda final_response="", session_id="", attempt=0, **kwargs: bridge.stop(final_response, session_id, stop_hook_active=attempt > 0, **kwargs))
    ctx.register_hook("on_session_finalize", bridge.session_end)
    ctx.register_hook("api_request_error", bridge.api_request_error)
    ctx.register_hook("on_session_end", bridge.turn_end)
