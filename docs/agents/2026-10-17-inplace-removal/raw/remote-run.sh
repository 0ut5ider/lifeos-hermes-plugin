#!/bin/bash
# Runs one driver action as owner with the selected Hermes environment interpreter; writes /tmp/<name>.out and .done.
name=$1; shift
export XDG_RUNTIME_DIR=/run/user/1000 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus
S=~/.hermes/hermes-agent
ENV=$(python3 -c 'import json,glob;print(json.load(open(glob.glob("/home/owner/.hermes/installs/*/facts.json")[0]))["packages"]["venv"]["environment"])')
rm -f /tmp/$name.done
cd ~
export PATH=$HOME/.local/bin:$PATH
(setsid nohup env HERMES_HOME=$HOME/.hermes PYTHONPATH=$S $ENV/bin/python -B /srv/lifeos-e2e/driver.py "$@" > /tmp/$name.out 2>&1; echo $? > /tmp/$name.done) </dev/null >/dev/null 2>&1 &
