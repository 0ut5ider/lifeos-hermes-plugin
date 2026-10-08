# ABOUTME: Generates the Hermes patch groups from a fully prepared source tree.
# ABOUTME: Assigns each changed file to one group and rejects unassigned files.

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

from lifeos_hook_bridge.install_source import SUPPORTED_HERMES_COMMIT


GROUPS = {
    "hermes-plugin-events.patch": (
        "hermes_cli/plugins.py", "hermes_cli/plugins_dispatch.py", "model_tools.py",
        "agent/learning_graph.py", "agent/learning_mutations.py", "tools/memory_tool.py",
        "tests/hermes_cli/test_plugins.py", "tests/hermes_cli/test_required_policy_hooks.py",
        "tests/hermes_cli/test_session_boundary_hooks.py", "tests/hermes_cli/test_stop_policy_dispatch.py",
        "tests/plugins/test_transform_tool_result_hook.py",
        "tests/agent/test_tool_result_context_hook.py",
    ),
    "hermes-turn-gates.patch": (
        "agent/conversation_compression.py", "agent/conversation_loop.py", "agent/session_persistence.py",
        "agent/turn_api_call.py", "agent/turn_context.py", "agent/turn_failure_copy.py",
        "agent/turn_final_response.py", "agent/turn_finalizer.py", "agent/turn_stop_gates.py",
        "tests/agent/test_prompt_hook_block.py", "tests/agent/test_turn_context.py",
        "tests/agent/test_verification_continuation_budget.py",
    ),
    "hermes-command-policy.patch": (
        "agent/terminal_approval_batch.py", "tools/approval.py", "tools/terminal_tool.py",
        "tools/code_execution_rpc.py", "tools/code_execution_tool.py", "tools/code_kernel.py",
        "tools/code_kernel_remote.py", "tests/agent/test_terminal_approval_batch.py",
        "tests/hermes_cli/test_approval_transport.py", "tests/test_lifeos_execute_code_session.py",
        "tests/tools/test_approval_plugin_hooks.py", "tests/tools/test_plugin_command_approval.py",
        "tests/tools/test_code_execution.py", "tests/tools/test_code_execution_file_rpc.py",
        "tests/tools/test_code_kernel.py", "tests/tools/test_code_kernel_remote.py",
    ),
    "hermes-session-lifecycle.patch": (
        "cli.py", "gateway/slash_commands_session.py", "gateway/run_agent_cache.py", "hermes_cli/cli_commands_mixin.py",
        "hermes_cli/cli_session_mixin.py", "hermes_cli/cli_tui_runtime_mixin.py",
        "tests/gateway/test_resume_command.py", "tests/gateway/test_stop_clarify_waiters.py",
        "plugins/platforms/discord/adapter.py", "tests/gateway/test_discord_command_identity.py",
        "tests/gateway/test_discord_connect.py", "tests/gateway/test_discord_sync_limit.py",
        "tests/gateway/test_discord_guild_channel_only.py",
        "tools/clarify_gateway.py", "tools/clarify_outcome.py", "tools/clarify_tool.py",
        "gateway/run_turn_runner.py", "gateway/run_turn_runner_clarify_delivery.py",
        "tests/gateway/test_clarify_cancellation_outcome.py", "tests/tools/test_clarify_gateway.py",
        "tests/gateway/test_clarify_delivery_fallback.py",
        "tests/hermes_cli/test_cli_resume_command.py",
    ),
    "hermes-child-routing.patch": ("tools/delegate_tool.py", "tests/test_lifeos_delegate_tier_route.py"),
    "hermes-strict-inference.patch": ("agent/auxiliary_client.py", "tests/test_lifeos_aux_no_fallback.py"),
    "hermes-remote-files.patch": (
        "tools/file_operations.py", "tools/file_tools.py", "tools/file_tools_read_tracking.py",
        "tests/tools/test_remote_file_staleness.py",
        "tests/test_lifeos_batch_schema.py",
    ),
    "hermes-cron-bootstrap.patch": ("cron/scheduler.py",),
    "hermes-required-middleware.patch": (
        "agent/auxiliary_hooks.py", "agent/turn_request_assembly.py", "hermes_cli/middleware.py",
        "hermes_cli/plugin_validate.py", "tests/hermes_cli/test_required_middleware.py",
    ),
    "hermes-web-result-status.patch": (
        "agent/display.py", "agent/tool_guardrails.py", "agent/tool_result_classification.py",
    ),
    "hermes-protected-instruction-approval.patch": ("tools/file_tools_write_guards.py",),
}


def rebuild(source: Path, output: Path) -> None:
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=source, text=True).strip()
    if revision != SUPPORTED_HERMES_COMMIT:
        raise ValueError("Prepared Hermes source uses another base revision")
    changed = set(subprocess.check_output(["git", "diff", "--name-only", "HEAD"], cwd=source, text=True).splitlines())
    assigned = [path for paths in GROUPS.values() for path in paths]
    if len(assigned) != len(set(assigned)) or changed != set(assigned):
        raise ValueError(f"Patch assignment differs: {sorted(changed ^ set(assigned))}")
    output.mkdir(parents=True, exist_ok=True)
    for name, paths in GROUPS.items():
        patch = subprocess.check_output(["git", "diff", "--binary", "HEAD", "--", *paths], cwd=source)
        (output / name).write_bytes(patch)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build the Hermes patch groups")
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rebuild(args.source, args.output)
