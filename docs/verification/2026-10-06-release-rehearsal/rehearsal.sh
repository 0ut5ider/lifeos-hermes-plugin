#!/bin/bash
# ABOUTME: Runs the complete page workflow on one guest as a release rehearsal.
# ABOUTME: Writes each response to ~/rehearsal and a done marker with the exit status.
set -u
export XDG_RUNTIME_DIR=/run/user/$(id -u)
R=~/rehearsal; mkdir -p $R; cd $R
log() { echo "$(date -u +%H:%M:%S) $*" | tee -a $R/steps.txt; }
call() { python3 ~/pageclient.py "$@"; }
status() { python3 -c "import json,sys;d=json.load(open(sys.argv[1]));print(d['status'])" "$1"; }
field() { python3 -c "import json,sys;d=json.load(open(sys.argv[1]))['body'];print(eval(sys.argv[2],{},{'b':d}))" "$1" "$2"; }
wait_update() { for i in $(seq 1 200); do call GET /installation/update > $1; s=$(field $1 'b.get("state")'); case $s in queued|preparing|applying|restoring|recovering) sleep 3;; *) echo $s; return;; esac; done; }
wait_host() { for i in $(seq 1 100); do call GET /installation/host-patch > $1; s=$(field $1 'b.get("state")'); case $s in staged|applying|restoring) sleep 3;; *) echo $s; return;; esac; done; }
wait_selection() { for i in $(seq 1 100); do sleep 5; call GET /installation/selection > $1 2>/dev/null || continue; s=$(field $1 'b["job"]["state"]' 2>/dev/null); case $s in queued|running|"") ;; *) echo $s; return;; esac; done; }
turn() { timeout 600 hermes chat -q "$1" 2>&1 | sed 's/\x1b\[[0-9;?]*[a-zA-Z]//g' > $2; sed -n '/☤ Hermes/,/Resume this session/p' $2 | grep -v '^\s*$' | sed -n 2,3p | tr -s ' '; }
for step in prepare apply finalize prepare-hermes apply-hermes; do call POST /installation/$step > $step.json; log "$step $(status $step.json)"; done
log "host $(wait_host host.json)"
systemctl --user restart hermes-dashboard; sleep 10
log "installation $(call GET /installation > installation.json; field installation.json 'b["lifeos"],b["hermes"],b["dashboard_restart_required"]')"
log "turn-installed: $(turn 'What is your name? One short sentence.' turn-installed.txt)"
call POST /memory/owner > claim.json; log "claim $(status claim.json)"
call POST /memory/fresh/start '{"principal_name":"Adrian","assistant_name":"Cerebo"}' > fresh-start.json; log "fresh-start $(status fresh-start.json)"
sleep 20
for i in $(seq 1 60); do call GET /memory/fresh/status > fresh-status.json; s=$(field fresh-status.json '" ".join(r["state"] for r in b["stores"])'); case $s in *preparing*|"") sleep 10;; *) break;; esac; done
log "fresh $(field fresh-status.json '[(r["identifier"],r["state"],r.get("active_facts")) for r in b["stores"]]')"
ID=$(field fresh-status.json 'b["stores"][0]["identifier"]')
call POST /installation/selection "{\"store\":\"$ID\"}" > select.json; log "select $(status select.json)"
log "selection $(wait_selection select-status.json)"
log "turn-selected: $(turn 'What is your name, and what is my name? Answer in one sentence.' turn-selected.txt)"
call POST /installation/selection/return > return.json; log "return $(status return.json)"
log "returned $(wait_selection return-status.json)"
log "turn-returned: $(turn 'What is your name? One short sentence.' turn-returned.txt)"
call POST /installation/prepare > update-prepare.json; log "update-prepare $(status update-prepare.json)"
call POST /installation/update > update.json; log "update $(status update.json)"
log "updated $(wait_update update-status.json)"
log "turn-updated: $(turn 'Reply with the single word READY.' turn-updated.txt)"
call POST /installation/update/restore > restore.json; log "restore $(status restore.json)"
log "restored $(wait_update restore-status.json)"
log "drift $(call GET /version-drift > drift.json; field drift.json 'b["changed_count"]')"
log "turn-restored: $(turn 'Reply with the single word READY.' turn-restored.txt)"
log "gateway $(systemctl --user is-active hermes-gateway)"
echo 0 > $R/done
