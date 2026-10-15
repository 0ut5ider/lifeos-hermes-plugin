# ABOUTME: Sequences synthetic interruption, recovery, final apply, and archive fixture preparation.
# ABOUTME: Stops on measured failure and retains per-action logs and completion markers.
import json, os, subprocess, time
from pathlib import Path
home=Path('/home/lifeos-hermes');stage=home/'releases/qualification-0.5.0'
env=dict(os.environ,**json.loads((home/'deployment/2026-10-14/environment.json').read_bytes()))
python=home/'.hermes/installs/995dd15ff6e15ed0/environments/65f4231f26e94a2d989e89eb96b98808/venv/bin/python'
def run(label,args):
 with (stage/(label+'.stdout')).open('w') as out,(stage/(label+'.stderr')).open('w') as err:
  r=subprocess.run(['/usr/sbin/runuser','-u','lifeos-hermes','--',str(python),'-B',*args],env=env,stdout=out,stderr=err,timeout=1800)
 (stage/(label+'.done')).write_text(str(r.returncode)+'\n')
 if r.returncode:raise RuntimeError(label+' fails')
code=1
try:
 deadline=time.monotonic()+360
 while not (stage/'daily-layout-interruption-preparation.done').exists():
  assert time.monotonic()<deadline
  time.sleep(1)
 assert (stage/'daily-layout-interruption-preparation.done').read_text().strip()=='0'
 run('interrupted-action',[str(stage/'start_rehearsal_interruption.py')])
 run('recovery-supervisor',[str(stage/'recover_rehearsal_interruption.py')])
 run('final-preparation',[str(stage/'prepare_rehearsal_phase.py'),'final-apply'])
 run('final-action',[str(stage/'run_rehearsal_action.py'),'apply','final-apply','final-applied'])
 prepared=json.loads((stage/'final-apply-preparation.json').read_bytes())
 package=home/'.hermes/.lifeos-releases'/prepared['preparation']['identifier']/'package'
 run('history-prepare',[str(stage/'history_guest_recovery.py'),'prepare',str(package)])
 code=0
finally:
 (stage/'recovery-sequence.done').write_text(str(code)+'\n')
