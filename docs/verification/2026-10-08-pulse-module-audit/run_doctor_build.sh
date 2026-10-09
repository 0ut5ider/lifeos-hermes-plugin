#!/usr/bin/env bash
# ABOUTME: Builds the prepared native dashboard without changing compiler settings or dependencies.
# ABOUTME: Retains complete build output and the process exit status.
set -u
export PATH=/home/outsider/.bun/bin:$PATH
export NEXT_TELEMETRY_DISABLED=1
cd /home/outsider/.cache/lifeos-daily-text-20261007/doctor-first/lifeos/LifeOS/install/LIFEOS/PULSE/Observability || exit 1
bun run build > /home/outsider/Projects/Hermes_agent/LifeOS_plugin/docs/verification/2026-10-08-pulse-module-audit/doctor-build.txt 2>&1
result=$?
printf '%s\n' "$result" > /home/outsider/Projects/Hermes_agent/LifeOS_plugin/docs/verification/2026-10-08-pulse-module-audit/doctor-build.done
exit "$result"
