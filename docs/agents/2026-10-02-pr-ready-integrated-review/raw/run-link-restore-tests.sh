#!/usr/bin/env bash
# ABOUTME: Runs isolated integrated review checks with pinned local source fixtures.
# ABOUTME: Saves raw verification output and an exit-status completion marker.
cd /home/outsider/Projects/Hermes_agent/LifeOS_plugin || exit 1
export LIFEOS_MEMORY_SOURCE=/home/outsider/.cache/lifeos-plugin-memory/source-gate-20261002-mount-release/lifeos/LifeOS/install
export LIFEOS_HERMES_SOURCE=/home/outsider/.cache/lifeos-plugin-memory/source-gate-20261002-mount-release/hermes
export PYTHONPATH=.:tests:$LIFEOS_HERMES_SOURCE
/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python -W error::ResourceWarning -m unittest test_update_transaction -v > docs/agents/2026-10-02-pr-ready-integrated-review/raw/link-restore-tests.txt 2>&1
printf '%s\n' "$?" > docs/agents/2026-10-02-pr-ready-integrated-review/raw/link-restore-tests.done
