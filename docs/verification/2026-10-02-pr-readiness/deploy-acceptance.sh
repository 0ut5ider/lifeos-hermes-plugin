#!/usr/bin/env bash
# ABOUTME: Installs the reviewed plugin package into the isolated acceptance account only.
# ABOUTME: Retains the previous runtime and restarts its four dedicated user services.
set -euo pipefail
cd /home/lifeos-plugin-install-probe/acceptance-20261002
export HOME=$PWD
export HERMES_HOME=$HOME/.hermes
export XDG_RUNTIME_DIR=/run/user/1007
export DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1007/bus
runtime=$HERMES_HOME/plugins/lifeos-hook-bridge
archive=$HOME/.local/state/pr-readiness-36727e5
stage=$HERMES_HOME/plugins/.lifeos-readiness-36727e5
services=(lifeos-acceptance-dashboard.service hermes-gateway.service lifeos-acceptance-native.service lifeos-acceptance-pulse.service)
test ! -e "$archive"
test ! -e "$stage"
mkdir -m 700 "$archive" "$stage"
tar -xzf /tmp/pr-readiness-plugin-20261002.tar.gz -C "$stage"
systemctl --user stop "${services[@]}"
mv "$runtime" "$archive/plugin-before"
mv "$stage" "$runtime"
systemctl --user start "${services[@]}"
systemctl --user is-active "${services[@]}"
printf '%s\n' "Previous runtime: $archive/plugin-before"
