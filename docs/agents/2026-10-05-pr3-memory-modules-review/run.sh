#!/usr/bin/env bash
# Arguments: output directory, run directory, model, effort.
codex exec --ignore-user-config \
  -m "$3" -c model_reasoning_effort="$4" \
  -s workspace-write --skip-git-repo-check \
  -C "$2" -o "$1/last-message.txt" \
  - < "$1/prompt.txt" > "$1/transcript.txt" 2>&1 &
echo $! > "$1/pid"
wait $!
echo $? > "$1/exit-code"
touch "$1/.done"
