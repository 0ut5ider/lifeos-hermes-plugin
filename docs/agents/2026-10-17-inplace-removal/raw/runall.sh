#!/bin/bash
# Runs each test file separately and records pass/fail per file.
cd "$1"
export PYTHONPATH=$1:/home/outsider/.cache/lifeos-release-0.7.3-20261016/archive-integration-wgrx453d/package/hermes
PY=/home/outsider/.cache/lifeos-daily-promotion-20261014/frozen-test-environment/bin/python
out="$2"; : > "$out"
for f in tests/test_*.py; do
  n=$(basename $f)
  r=$(timeout 900 $PY -B -m unittest discover -s tests -p "$n" 2>&1 | tail -3 | tr '\n' ' ')
  echo "$n :: $r" >> "$out"
done
touch "$out.done"
