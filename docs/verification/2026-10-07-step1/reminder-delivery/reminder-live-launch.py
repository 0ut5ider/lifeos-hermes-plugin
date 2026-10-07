# ABOUTME: Runs the private GitHub reminder acceptance through an isolated remote account.
# ABOUTME: Passes authentication through standard input and records the process result without credentials.
import shlex
import subprocess
from pathlib import Path
base='/var/tmp/lifeos-step1-20261006/delegation-callback-controls'
workspace='/home/lifeos-plugin-install-probe/workspace/paired-step1-20261006'
paths=base+':'+base+'/hermes-child-final:/home/lifeos-plugin-install-probe/workspace/hook-evidence-20261003/home/.hermes/installs/2cd77f30ab6c57b5/environments/de1515ba6e674677ba2da15650b65812/venv/lib/python3.14/site-packages'
command=['runuser','-u','lifeos-plugin-install-probe','--','env','-u','XDG_RUNTIME_DIR','PYTHONPATH='+paths,
'/var/tmp/lifeos-paired-context-response-final-20261005/python/bin/python3',base+'/installed_reminder_delivery_controls.py',
'--native',base+'/lifeos-review-final','--installed-settings',workspace+'/full-installed-review-pinned/.claude/settings.json',
'--gh',base+'/gh-reminder-probe','--bun','/var/tmp/lifeos-step1-20261006/bun-pinned-bin/bun',
'--repository','0ut5ider/lifeos-reminder-test','--home',workspace+'/reminder-live-20261007-c',
'--output',workspace+'/reminder-live-20261007-c-evidence']
token=subprocess.check_output(['gh','auth','token','--hostname','github.com','--user','0ut5ider'],text=True).strip()
result=subprocess.run(['ssh','-i','/home/outsider/.ssh/id_ed25519','-o','BatchMode=yes','root@192.168.8.252',shlex.join(command)],input=token,text=True)
Path('/home/outsider/.cache/lifeos-step1-20261007/reminder-live-launch.done').write_text(str(result.returncode)+'\n')
