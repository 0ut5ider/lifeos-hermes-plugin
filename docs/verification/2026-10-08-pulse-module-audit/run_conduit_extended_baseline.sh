#!/usr/bin/env bash
# ABOUTME: Runs the prepared operational views and neighboring owner publication and relay checks.
# ABOUTME: Retains complete output and a completion status for detached execution.
set -u
cd /home/outsider/Projects/Hermes_agent/LifeOS_plugin || exit 1
export PATH=/home/outsider/.bun/bin:$PATH
export LIFEOS_MEMORY_SOURCE=/home/outsider/.cache/lifeos-daily-text-20261007/doctor-first/lifeos/LifeOS/install
export LIFEOS_HERMES_SOURCE=/home/outsider/.cache/lifeos-daily-text-20261007/doctor-first/hermes
export LIFEOS_PREPARE_HERMES_REPO=/home/outsider/.cache/lifeos-daily-text-20261007/channel-sources/hermes
export LIFEOS_PREPARE_LIFEOS_REPO=/home/outsider/.cache/lifeos-daily-text-20261007/channel-sources/lifeos
export LIFEOS_HARVEST_CONTROL_SOURCE=/home/outsider/.cache/lifeos-daily-text-20261007/background-control-source/LifeOS/install
export LIFEOS_FRESHNESS_CONTROL_SOURCE=/home/outsider/.cache/lifeos-daily-text-20261007/background-control-source/LifeOS/install
export LIFEOS_UPGRADE_CONTROL_SOURCE=/home/outsider/.cache/lifeos-daily-text-20261007/hypothesis-helpers-first/lifeos/LifeOS/install
export PYTHONPATH=/home/outsider/Projects/Hermes_agent/LifeOS_plugin:/home/outsider/Projects/Hermes_agent/LifeOS_plugin/tests
/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python -W error -m unittest -v test_memory_conduit.MemoryConduitTests.test_original_first_read_writes_native_defaults_and_preserves_daily_fields test_memory_conduit.MemoryConduitTests.test_anonymous_first_read_refuses_before_native_config_creation test_memory_conduit.MemoryConduitTests.test_owner_first_read_publishes_identical_native_defaults_privately test_memory_conduit.MemoryConduitTests.test_original_recent_insight_sources_and_missing_characterization test_memory_conduit.MemoryConduitTests.test_all_admitted_read_routes_preserve_native_fields test_memory_conduit.MemoryConduitTests.test_private_and_retired_events_do_not_contribute_labels_or_counts test_memory_conduit.MemoryConduitTests.test_excluded_current_insight_cannot_use_older_fallback test_memory_conduit.MemoryConduitTests.test_current_owner_origin_bearer_and_connector_govern_delivery test_memory_conduit.MemoryConduitTests.test_redirected_invalid_and_oversize_config_refuse test_memory_conduit.MemoryConduitTests.test_unknown_methods_and_selectors_refuse_without_initialization test_memory_conduit.MemoryConduitTests.test_complete_event_log_retains_native_counts_without_tail_truncation test_memory_conduit.MemoryConduitTests.test_exact_review_preserves_safe_old_config_and_event_bytes test_memory_conduit.MemoryConduitTests.test_actual_render_rechecks_sources_selection_descriptor_and_authority > docs/verification/2026-10-08-pulse-module-audit/conduit-extended-baseline.txt 2>&1
result=$?
printf '%s\n' "$result" > docs/verification/2026-10-08-pulse-module-audit/conduit-extended-baseline.done
exit "$result"
