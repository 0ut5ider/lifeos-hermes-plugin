#!/bin/bash
# ABOUTME: Interrupts a first in-place installation at fixed checkpoints, recovers it, and records each outcome.
# ABOUTME: Each case starts from the CT 112 base snapshot; results go to crash-results/<case>.txt.
set -uo pipefail
V=$(cd "$(dirname "$0")" && pwd); export TARGET=root@192.168.8.237 E2E_DIR=$HOME/agent-scratch/e2e-crash; OUT=$V/crash-results; mkdir -p $OUT
cases=("artifact-published 60" "programs-published 1" "dependencies-synchronized 1" "native-mounted 1")
for item in "${cases[@]}"; do
  set -- $item; point=$1; count=$2; name=$point-$count
  ssh root@192.168.8.101 'pct stop 112; pct rollback 112 base; pct start 112' >/dev/null 2>&1; sleep 10
  ssh $TARGET 'loginctl enable-linger owner; systemctl start user@1000.service' >/dev/null 2>&1
  if [ -z "${built:-}" ]; then $V/redeploy.sh >/dev/null; built=1; else NOBUILD=1 $V/redeploy.sh >/dev/null; fi
  {
    echo "== case $name"
    $V/run.sh prepare prepare install | tail -2
    J=$(ssh $TARGET 'basename $(ls -td /home/owner/.hermes/.lifeos-releases/*/ | head -1)')
    $V/run.sh crash crash $J $point $count | head -1
    echo "state after crash: $(ssh $TARGET cat /home/owner/.hermes/.lifeos-releases/$J/status.json)"
    echo "gateway after crash: $(ssh $TARGET runuser -u owner -- env XDG_RUNTIME_DIR=/run/user/1000 systemctl --user is-active hermes-gateway)"
    $V/run.sh recover recover $J | tail -1
    ssh $TARGET "until grep -qE '\"(applied|rolled_back|recovery_required|rejected)\"' /home/owner/.hermes/.lifeos-releases/$J/status.json && ! grep -q queued /home/owner/.hermes/.lifeos-releases/$J/status.json; do sleep 5; done"
    echo "state after recovery: $(ssh $TARGET cat /home/owner/.hermes/.lifeos-releases/$J/status.json)"
    ssh $TARGET "cat /home/owner/.hermes/.lifeos-releases/$J/worker-failure.json 2>/dev/null; runuser -u owner -- bash -lc 'export XDG_RUNTIME_DIR=/run/user/1000; hermes lifeos-release compatibility | python3 -c \"import json,sys;r=json.load(sys.stdin);print(\\\"host:\\\", r[\\\"state\\\"], [x[\\\"code\\\"] for x in r[\\\"reasons\\\"]])\"; echo gateway: \$(systemctl --user is-active hermes-gateway); hermes lifeos-version | head -c 160; echo; git -C ~/.hermes/hermes-agent status --porcelain | cut -c1-2 | sort | uniq -c | tr \"\\n\" \" \"; echo'"
  } > $OUT/$name.txt 2>&1
done
touch $OUT/.done
