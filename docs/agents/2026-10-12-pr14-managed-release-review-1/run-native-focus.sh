#!/bin/bash
# ABOUTME: Runs selected native patch-port tests through Hermes official isolated runner.
# ABOUTME: Uses the existing test interpreter and an isolated synthetic account home.
review_dir=/home/outsider/Projects/Hermes_agent/LifeOS_plugin/docs/agents/2026-10-12-pr14-managed-release-review-1
review_home=$(mktemp -d)
HOME="$review_home" HERMES_PYTHON=/home/outsider/.cache/lifeos-hermes-managed-20261012/native-test-environment/bin/python bash /home/outsider/.cache/lifeos-hermes-managed-20261012/packages/0.4.0-dev.1-3a072309/hermes/scripts/run_tests.sh -j 4 tests/hermes_cli/test_plugin_policy_arguments.py tests/hermes_cli/test_plugin_async_dispatch.py tests/hermes_cli/test_required_middleware.py tests/gateway/test_discord_guild_channel_only.py > "$review_dir/native-focus.txt" 2>&1
review_exit=$?
printf '%s\n' "$review_exit" > "$review_dir/native-focus.done"
rm -rf "$review_home"
exit "$review_exit"
