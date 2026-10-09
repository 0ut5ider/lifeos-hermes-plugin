#!/usr/bin/env bash
# ABOUTME: Builds the exact prepared operational dashboard candidate.
# ABOUTME: Retains complete build output and its final status.
set -u
cd /home/outsider/.cache/lifeos-daily-text-20261007/manual-state-first/lifeos/LifeOS/install/LIFEOS/PULSE/Observability || exit 1
export PATH=/home/outsider/.bun/bin:$PATH
export NEXT_TELEMETRY_DISABLED=1
bun run build > /home/outsider/Projects/Hermes_agent/LifeOS_plugin/docs/verification/2026-10-08-remaining-reader-audit/manual-state-dashboard-build.txt 2>&1
result=$?
printf '%s\n' "$result" > /home/outsider/Projects/Hermes_agent/LifeOS_plugin/docs/verification/2026-10-08-remaining-reader-audit/manual-state-dashboard-build.done
exit "$result"
