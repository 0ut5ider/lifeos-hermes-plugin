#!/usr/bin/env bash
# ABOUTME: Runs isolated integrated review checks with pinned local source fixtures.
# ABOUTME: Saves raw verification output and an exit-status completion marker.
cd /home/outsider/Projects/Hermes_agent/LifeOS_plugin || exit 1
preparation_fixture=$(mktemp -d /home/outsider/.cache/lifeos-plugin-memory/integrated-review-preparation.XXXXXX)
trap 'rm -rf "$preparation_fixture"' EXIT
git clone --quiet --bare --shared /home/outsider/.cache/lifeos-plugin-memory/source-gate-20261002-mount-release/hermes "$preparation_fixture/hermes" || exit 1
git --git-dir="$preparation_fixture/hermes" update-ref refs/heads/review-preparation 758ad514eb0e800547e015edf05aa18f78b78d82 || exit 1
git --git-dir="$preparation_fixture/hermes" symbolic-ref HEAD refs/heads/review-preparation || exit 1
git clone --quiet --bare --shared /home/outsider/.cache/lifeos-plugin-memory/source-gate-20261002-mount-release/lifeos "$preparation_fixture/lifeos" || exit 1
git --git-dir="$preparation_fixture/lifeos" update-ref refs/heads/review-preparation 5e2f2e8c0abde612da0e99c16c0d07d4ec21b88c || exit 1
git --git-dir="$preparation_fixture/lifeos" symbolic-ref HEAD refs/heads/review-preparation || exit 1
export LIFEOS_PREPARE_HERMES_REPO="$preparation_fixture/hermes"
export LIFEOS_PREPARE_LIFEOS_REPO="$preparation_fixture/lifeos"
export TMPDIR="$preparation_fixture"
export PYTHONPATH=.:tests:/home/outsider/.cache/lifeos-plugin-memory/source-gate-20261002-mount-release/hermes
/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python -m unittest test_prepare_sources.PrepareSourcesTests.test_real_sources_receive_every_patch_in_order -v > docs/agents/2026-10-02-pr-ready-integrated-review/raw/preparation-test.txt 2>&1
printf '%s\n' "$?" > docs/agents/2026-10-02-pr-ready-integrated-review/raw/preparation-test.done
