#!/bin/bash
# Runs one driver action as the test owner on CT 111 and waits for it.
set -uo pipefail
T=root@192.168.8.236; name=$1; shift
scp -q /tmp/inplace-removal/remote-run.sh /tmp/inplace-removal/driver.py $T:/srv/lifeos-e2e/ && ssh $T 'chmod a+rx /srv/lifeos-e2e/remote-run.sh /srv/lifeos-e2e/driver.py'
ssh $T "runuser -u owner -- bash /srv/lifeos-e2e/remote-run.sh $name $*; until [ -f /tmp/$name.done ]; do sleep 3; done; echo exit=\$(cat /tmp/$name.done); tail -40 /tmp/$name.out"
