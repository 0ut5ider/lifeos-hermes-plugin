#!/bin/bash
# ABOUTME: Experiment 3 for the PR 3 follow-up review: installer behavior with pre-existing symlinks.
# ABOUTME: Runs install.py from the c083037 export against throwaway profiles under /tmp.
set -u
INSTALL=/tmp/pr3review/src/optional/lifeos-memory-sharing/install.py
B=/tmp/pr3review/exp3
rm -rf "$B"; mkdir -p "$B"
run() { echo "\$ $*"; "$@" 2>&1 | tail -2; echo "exit=$?"; }

echo "== 3a: component directory is a symlink to another directory (install)"
mkdir -m 700 "$B/p1" "$B/elsewhere1"
ln -s "$B/elsewhere1" "$B/p1/lifeos-memory-sharing"
run python3 "$INSTALL" --hermes-home "$B/p1"
ls -la "$B/elsewhere1"

echo "== 3b: dangling symlink as component directory (install)"
mkdir -m 700 "$B/p2"
ln -s "$B/missing" "$B/p2/lifeos-memory-sharing"
run python3 "$INSTALL" --hermes-home "$B/p2"

echo "== 3c: installed file is a symlink to an outside file (install)"
mkdir -m 700 "$B/p3" "$B/p3/lifeos-memory-sharing"
echo "outside content" > "$B/outside3.txt"
ln -s "$B/outside3.txt" "$B/p3/lifeos-memory-sharing/memory_sharing.py"
run python3 "$INSTALL" --hermes-home "$B/p3"
echo "outside3.txt now: $(cat "$B/outside3.txt")"; ls -la "$B/p3/lifeos-memory-sharing"

echo "== 3d: component directory is a symlink (remove)"
mkdir -m 700 "$B/p4" "$B/elsewhere4"
echo "not the component" > "$B/elsewhere4/memory_sharing.py"
ln -s "$B/elsewhere4" "$B/p4/lifeos-memory-sharing"
run python3 "$INSTALL" --hermes-home "$B/p4" --remove
echo "elsewhere4 after remove:"; ls -la "$B/elsewhere4"

echo "== 3e: remove after a load created __pycache__"
mkdir -m 700 "$B/p5"
python3 "$INSTALL" --hermes-home "$B/p5" >/dev/null
(cd /tmp/pr3review/src && python3 -c "
import sys; from pathlib import Path
from lifeos_hook_bridge.memory_preferences import load_sharing_component
load_sharing_component(Path('$B/p5/lifeos-memory-sharing'))")
run python3 "$INSTALL" --hermes-home "$B/p5" --remove
find "$B/p5" | sort
