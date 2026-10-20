#!/bin/bash
# ABOUTME: Applies one source mutation at a time to a scratch copy of the plugin and runs the transition tests.
# ABOUTME: A mutation that leaves the tests passing marks a gap in the tests.
set -u
SRC=/home/outsider/Projects/Hermes_agent/LifeOS_plugin
W=$HOME/agent-scratch/r3-mutants
PY=/home/outsider/.cache/lifeos-daily-promotion-20261014/frozen-test-environment/bin/python
H=/home/outsider/.cache/lifeos-release-0.7.3-20261016/archive-integration-wgrx453d/package/hermes
mutate() {
  rm -rf $W; mkdir -p $W; cp -r $SRC/optional $SRC/tests $W/
  $PY - "$W/optional/lifeos_release_manager/$1" "$2" "$3" <<'PY'
import sys
path, old, new = sys.argv[1:]
text = open(path).read()
assert old in text, old
open(path, 'w').write(text.replace(old, new, 1))
PY
  out=$(cd $W && TMPDIR=$HOME/agent-scratch/tmp LIFEOS_HERMES_SOURCE=$H PYTHONPATH=$W:$H $PY -B -m unittest discover -s tests -p "test_inplace_[ps]*.py" -k TransitionTests -k ParseShowTests 2>&1 | tail -1)
  echo "$4 -> $out"
}
mutate inplace_preparation.py "FORWARDER_BYTES = 1024 * 1024" "FORWARDER_BYTES = 1024 * 1024" "baseline (no change)"
mutate inplace_preparation.py "check_service_launchers(home, replaced=('gateway',) if replace else ())" "check_service_launchers(home, replaced=())" "always replaced=()"
mutate inplace_preparation.py "            _check_replaced_drop_ins(unit, values)
" "" "no drop-in check for replaced unit"
mutate inplace_preparation.py " ; ignore_errors=', entry)" " ;', entry)" "argv regex stops at first ' ;'"
mutate inplace_preparation.py "part.strip('\\'\"')" "part" "no quote stripping"
mutate inplace_preparation.py "UNIT_COMMANDS = ('ExecStartPre', 'ExecStart', 'ExecStartPost')" "UNIT_COMMANDS = ('ExecStart',)" "only ExecStart"
mutate inplace_preparation.py "UNIT_COMMANDS = ('ExecStartPre', 'ExecStart', 'ExecStartPost')" "UNIT_COMMANDS = ('ExecStartPre', 'ExecStart')" "no ExecStartPost"
mutate inplace_preparation.py "for entry in values.get(key, '').splitlines():" "for entry in values.get(key, '').splitlines()[-1:]:" "only last entry per key"
mutate inplace_services.py "values[key] = values[key] + '\\n' + value if key in values else value" "values[key] = value" "parse_show last wins"
