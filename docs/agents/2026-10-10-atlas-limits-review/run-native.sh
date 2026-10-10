#!/bin/bash
set -u
cd /home/outsider/Projects/Hermes_agent/LifeOS_plugin
out=docs/agents/2026-10-10-atlas-limits-review
bun --no-install "$out/native-measure.ts" "$out/native-measurements.json" > "$out/native.stdout" 2> "$out/native.stderr"
result=$?
printf '%s\n' "$result" > "$out/native.exit"
touch "$out/native.done"
exit "$result"
