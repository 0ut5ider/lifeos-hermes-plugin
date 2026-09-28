#!/usr/bin/env bash
# ABOUTME: Routes reference LifeOS child calls to the private local model.
# ABOUTME: Maps LifeOS model tiers to the accepted effort settings for comparisons.

set -euo pipefail
set -a
source "$HOME/.config/lifeos-reference/model.env"
set +a

args=("$@")
requested_model=""
for (( i=0; i<${#args[@]}; i++ )); do
  case "${args[i]}" in
    --model)
      if (( i + 1 < ${#args[@]} )); then
        requested_model="${args[i+1]}"
        (( i+=1 ))
      fi
      ;;
    --model=*) requested_model="${args[i]#--model=}" ;;
  esac
done

case "$requested_model" in
  *haiku*) effort=low ;;
  *opus*|*fable*) effort=xhigh ;;
  *) effort=medium ;;
esac

has_effort=false
for (( i=0; i<${#args[@]}; i++ )); do
  case "${args[i]}" in
    --model)
      if (( i + 1 < ${#args[@]} )); then
        args[i+1]="$ANTHROPIC_MODEL"
        (( i+=1 ))
      fi
      ;;
    --model=*) args[i]="--model=$ANTHROPIC_MODEL" ;;
    --effort)
      if (( i + 1 < ${#args[@]} )); then
        args[i+1]="$effort"
        has_effort=true
        (( i+=1 ))
      fi
      ;;
    --effort=*)
      args[i]="--effort=$effort"
      has_effort=true
      ;;
  esac
done
if [[ "$has_effort" == false ]]; then
  args+=(--effort "$effort")
fi

exec "$HOME/.local/bin/claude" "${args[@]}"
