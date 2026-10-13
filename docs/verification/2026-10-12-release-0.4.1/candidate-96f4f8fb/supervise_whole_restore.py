# ABOUTME: Supervises the actual development guest backup and isolated restore qualification.
# ABOUTME: Writes process completion outside the interactive session without touching the daily guest.
import subprocess,os
from pathlib import Path
os.umask(0o077)
folder=Path('/root/lifeos-release-0.4.1')
env=dict(os.environ,LIFEOS_STABLE_PYTHON='/home/lifeos-hermes/.hermes/.lifeos-releases/87561ff313e348508c3c7e1331b838be/python-environment/bin/python',LIFEOS_STABLE_OPERATION='87561ff313e348508c3c7e1331b838be',PYTHONDONTWRITEBYTECODE='1')
with (folder/'history-restore-launch.stdout').open('wb') as stdout,(folder/'history-restore-launch.stderr').open('wb') as stderr:
 result=subprocess.run(['python3','-B','/root/proxmox_history_restore_041_96f4f8fb.py'],env=env,stdout=stdout,stderr=stderr)
(folder/'history-restore.done').write_text(str(result.returncode)+chr(10))
