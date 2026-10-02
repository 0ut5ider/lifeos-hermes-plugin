#!/usr/bin/env bash
# ABOUTME: Runs isolated integrated review checks with pinned local source fixtures.
# ABOUTME: Saves raw verification output and an exit-status completion marker.
cd /home/outsider/Projects/Hermes_agent/LifeOS_plugin || exit 1
preparation_fixture=$(mktemp -d /tmp/lifeos-integrated-review-preparation.XXXXXX)
trap 'rm -rf "$preparation_fixture"' EXIT
git clone --quiet --no-checkout /home/outsider/.cache/lifeos-plugin-memory/source-gate-20261002-mount-release/hermes "$preparation_fixture/hermes" || exit 1
git -C "$preparation_fixture/hermes" checkout --quiet --detach 758ad514eb0e800547e015edf05aa18f78b78d82 || exit 1
git clone --quiet --no-checkout /home/outsider/.cache/lifeos-plugin-memory/source-gate-20261002-mount-release/lifeos "$preparation_fixture/lifeos" || exit 1
git -C "$preparation_fixture/lifeos" checkout --quiet --detach 5e2f2e8c0abde612da0e99c16c0d07d4ec21b88c || exit 1
export LIFEOS_PREPARE_HERMES_REPO="$preparation_fixture/hermes"
export LIFEOS_PREPARE_LIFEOS_REPO="$preparation_fixture/lifeos"
export PYTHONPATH=.:tests:/home/outsider/.cache/lifeos-plugin-memory/source-gate-20261002-mount-release/hermes
/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python -m unittest test_prepare_sources.PrepareSourcesTests.test_real_sources_receive_every_patch_in_order -v > docs/agents/2026-10-02-pr-ready-integrated-review/raw/preparation-test.txt 2>&1
printf '%s\n' "$?" > docs/agents/2026-10-02-pr-ready-integrated-review/raw/preparation-test.done
