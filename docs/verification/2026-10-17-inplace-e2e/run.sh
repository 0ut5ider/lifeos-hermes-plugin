#!/bin/bash
# ABOUTME: Runs one qualification driver action as the test owner on the container and waits for it.
# ABOUTME: Prints the exit status and the last lines of the action output.
# Run one driver action as the test owner on the container and wait for its result.
set -uo pipefail
T=root@192.168.8.233; name=$1; shift
ssh $T "rm -f /tmp/$name.done; runuser -u owner -- bash -lc 'export XDG_RUNTIME_DIR=/run/user/1000 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus; S=~/.hermes/hermes-agent; PY=\$(ls ~/.hermes/installs/*/environments/*/venv/bin/python | head -1); cd ~; (setsid nohup env HERMES_HOME=~/.hermes PYTHONPATH=\$S \$PY -B /srv/lifeos-e2e/driver.py $* > /tmp/$name.out 2>&1; echo \$? > /tmp/$name.done) </dev/null >/dev/null 2>&1 &'; until [ -f /tmp/$name.done ]; do sleep 3; done; echo exit=\$(cat /tmp/$name.done); tail -25 /tmp/$name.out"
