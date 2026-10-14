# ABOUTME: Probes native UTC event clocks and clock or execution admission failures.
# ABOUTME: Uses only synthetic cron metadata and compares the original validator.
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import hashlib
import json
from pathlib import Path
import subprocess
from lifeos_hook_bridge.morning_observation import morning_execution

start = datetime(2026,10,14,18,2,tzinfo=ZoneInfo("America/Toronto"))
end = start + timedelta(minutes=15)
started = start + timedelta(seconds=53,milliseconds=6)
completed = start + timedelta(minutes=1,seconds=19,milliseconds=76)
channel="1558870196784205927"
state={"lastResult":"ok","lastRun":int(completed.timestamp()*1000),"consecutiveFailures":0}

def row(at, delay, msg, **extra):
    body={"subsystem":"cron","msg":msg,"ts":at.astimezone(timezone.utc).isoformat().replace("+00:00","Z"),**extra}
    return json.dumps({"__REALTIME_TIMESTAMP":str(int(at.timestamp()*1000000)+delay),"MESSAGE":json.dumps(body)})

s=row(started,212,"Running: life-morning-brief")
c=row(completed,475,"life-morning-brief completed; dispatched to log",outputPreview=json.dumps({"status":"delivered","channel_id":channel}))
old={}
exec(subprocess.check_output(["git","show","5907909e:lifeos_hook_bridge/morning_observation.py"],text=True),old)
results={}
try:
    old["morning_execution"]("\n".join([s,c]),state,start,end,channel)
except ValueError as error:
    results["old_exact_timing"]={"status":"EXPECTED_REFUSAL","error":str(error)}
else:
    raise AssertionError("The original validator must fail the measured synthetic timings")
results["utc_Z_clock"]={"status":"PASS","receipt":morning_execution("\n".join([s,c]),state,start,end,channel)}
scenarios={
 "duplicate_start": ([s,s,c],state),
 "duplicate_completion": ([s,c,c],state),
 "stale_state": ([s,c],dict(state,lastRun=state["lastRun"]-1)),
 "state_after_bound": ([s,c],dict(state,lastRun=state["lastRun"]+5001)),
 "negative_capture_delay": ([s,row(completed,-1,"life-morning-brief completed",outputPreview=json.dumps({"status":"delivered","channel_id":channel}))],state),
 "late_capture": ([s,row(completed,5000001,"life-morning-brief completed",outputPreview=json.dumps({"status":"delivered","channel_id":channel}))],state),
 "start_after_completion": ([row(completed+timedelta(seconds=1),0,"Running: life-morning-brief"),c],state),
 "completion_outside_window": ([s,row(end+timedelta(microseconds=1),0,"life-morning-brief completed",outputPreview=json.dumps({"status":"delivered","channel_id":channel}))],state),
 "completion_missing_clock": ([s,json.dumps({"__REALTIME_TIMESTAMP":str(int(completed.timestamp()*1000000)),"MESSAGE":json.dumps({"subsystem":"cron","msg":"life-morning-brief completed","outputPreview":"{}"})})],state),
 "completion_naive_clock": ([s,row(completed,0,"life-morning-brief completed",ts=completed.replace(tzinfo=None).isoformat(),outputPreview="{}")],state),
 "wrong_channel": ([s,row(completed,0,"life-morning-brief completed",outputPreview=json.dumps({"status":"delivered","channel_id":"1"}))],state),
}
for name,(rows,current) in scenarios.items():
    try: morning_execution("\n".join(rows),current,start,end,channel)
    except ValueError as error: results[name]={"status":"EXPECTED_REFUSAL","error":str(error)}
    else: raise AssertionError(name+" unexpectedly passed")
receipt=json.loads(Path("docs/verification/2026-10-14-evening-observation/automatic-rescheduled-verification.json").read_bytes())
digest=hashlib.sha256(Path("lifeos_hook_bridge/morning_observation.py").read_bytes()).hexdigest()
assert receipt["validator_sha256"] == digest
assert receipt["initial_installed_observer"]["status"] == "FAIL"
assert receipt["original_0700_wall_clock_observed"] is False
assert receipt["status"] == "PASS"
assert receipt["version"] == "0.4.3"
results["safe_receipt_provenance"]={"status":"PASS","validator_sha256":digest,"initial_failure_preserved":True,"0700_observed":False}
print(json.dumps(results,indent=2))
