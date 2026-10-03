#!/usr/bin/env bash
# ABOUTME: Runs isolated integrated review checks with pinned local source fixtures.
# ABOUTME: Saves raw verification output and an exit-status completion marker.
cd /home/outsider/Projects/Hermes_agent/LifeOS_plugin || exit 1
export LIFEOS_MEMORY_SOURCE=/home/outsider/.cache/lifeos-plugin-memory/source-gate-20261002-mount-release/lifeos/LifeOS/install
export LIFEOS_HERMES_SOURCE=/home/outsider/.cache/lifeos-plugin-memory/source-gate-20261002-mount-release/hermes
export LIFEOS_PREPARE_HERMES_REPO="$LIFEOS_HERMES_SOURCE"
export LIFEOS_PREPARE_LIFEOS_REPO=/home/outsider/.cache/lifeos-plugin-memory/source-gate-20261002-mount-release/lifeos
export PYTHONPATH=.:tests:$LIFEOS_HERMES_SOURCE
/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python -m unittest test_memory_agent test_memory_history test_memory_model_calls test_memory_host test_memory_review test_prepare_sources.PrepareSourcesTests.test_real_sources_receive_every_patch_in_order -v > docs/agents/2026-10-02-pr-ready-integrated-review/raw/lifecycle-tests.txt 2>&1
printf '%s\n' "$?" > docs/agents/2026-10-02-pr-ready-integrated-review/raw/lifecycle-tests.done
