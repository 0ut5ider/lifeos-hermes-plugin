#!/usr/bin/env bash
# ABOUTME: Verifies native plugin list preparation and neighboring mount publication.
# ABOUTME: Records complete results against the corrected pinned source.
set -u
cd /home/outsider/Projects/Hermes_agent/LifeOS_plugin || exit 1
export PATH=/home/outsider/.bun/bin:$PATH
export PYTHONPATH=/home/outsider/Projects/Hermes_agent/LifeOS_plugin:/home/outsider/Projects/Hermes_agent/LifeOS_plugin/tests:/home/outsider/.cache/lifeos-daily-text-20261007/conduit-capture-first/hermes
export LIFEOS_MEMORY_SOURCE=/home/outsider/.cache/lifeos-daily-text-20261007/mount-plugin-sequence-first/lifeos/LifeOS/install
export LIFEOS_HERMES_SOURCE=/home/outsider/.cache/lifeos-daily-text-20261007/conduit-capture-first/hermes
export LIFEOS_PREPARE_LIFEOS_REPO=/home/outsider/.cache/lifeos-daily-text-20261007/channel-sources/lifeos
/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python -W error -m unittest -v test_mount_transaction test_selection_native_mount test_memory_administration test_memory_admin_install test_patch_bundle > docs/verification/2026-10-09-daily-release-installed/mount-plugin-sequence-second.txt 2>&1
result=$?
printf '%s\n' "$result" > docs/verification/2026-10-09-daily-release-installed/mount-plugin-sequence-second.done
exit "$result"
