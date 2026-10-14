#!/bin/bash
# ABOUTME: Prepares the exact public integration release through the installed native Hermes command.
# ABOUTME: Retains detached preparation output and completion without selecting active programs.
set -u
umask 077
promotion_output=/home/lifeos-hermes/releases/qualification-0.4.3
mkdir -p "$promotion_output"
export HOME=/home/lifeos-hermes
export HERMES_HOME=/home/lifeos-hermes/.hermes
export PATH=/home/lifeos-hermes/.local/bin:/usr/bin:/bin
export XDG_RUNTIME_DIR="/run/user/$(id -u)"
export DBUS_SESSION_BUS_ADDRESS="unix:path=$XDG_RUNTIME_DIR/bus"
cd "$HERMES_HOME" || exit 1
hermes lifeos-release prepare --version 0.4.3 > "$promotion_output/public-preparation.stdout" 2> "$promotion_output/public-preparation.stderr"
promotion_status=$?
printf '%s\n' "$promotion_status" > "$promotion_output/public-preparation.done"
exit "$promotion_status"
