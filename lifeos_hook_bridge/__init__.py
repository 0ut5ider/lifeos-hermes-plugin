# ABOUTME: Registers LifeOS hook callbacks with the Hermes plugin manager.
# ABOUTME: Loads the installed Claude hook settings from the LifeOS account.

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .bridge import HookBridge
from .model_tiers import configured_model_map


def register(ctx: Any) -> None:
    settings = Path(os.environ.get("LIFEOS_HOOK_SETTINGS", str(Path.home() / ".claude/settings.json"))).expanduser()
    if not settings.is_file():
        raise FileNotFoundError(f"LifeOS Claude hook settings not found: {settings}")
    bridge = HookBridge(
        settings, settings.parent,
        model_tiers_provider=lambda: configured_model_map(ctx.get_config),
    )
    ctx.register_hook("pre_tool_call", bridge.pre_tool_call)
    ctx.register_hook("post_tool_call", bridge.task_result)
    ctx.register_hook("pre_command_approval", bridge.command_approval)
    ctx.register_hook("augment_tool_result", bridge.augment_tool_result)
    ctx.register_hook("pre_llm_call", bridge.pre_llm_call)
    def stop(final_response="", session_id="", attempt=0, **kwargs):
        result = bridge.stop(final_response, session_id, stop_hook_active=attempt > 0, **kwargs)
        if result and ctx.get_config("stop_cap_policy", "claude") == "fail_closed":
            return {**result, "on_limit": "fail"}
        return result

    ctx.register_hook("pre_turn_stop", stop)
    ctx.register_hook("on_session_finalize", bridge.session_end)
    ctx.register_hook("api_request_error", bridge.api_request_error)
    ctx.register_hook("on_turn_result", bridge.turn_end)
