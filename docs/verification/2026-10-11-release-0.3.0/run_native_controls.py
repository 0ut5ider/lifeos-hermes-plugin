# ABOUTME: Runs pinned Hermes gateway and Discord controls against the final release source.
# ABOUTME: Preserves native subprocess isolation and records the simulated transport scope.
from pathlib import Path
import json
import os
import subprocess
import sys
import time

out=Path(__file__).parent;hermes=Path(sys.argv[1])/'hermes'
paths=['tests/gateway/test_stop_clarify_waiters.py','tests/gateway/test_clarify_cancellation_outcome.py',
 'tests/gateway/test_clarify_delivery_fallback.py','tests/tools/test_clarify_gateway.py','tests/tools/test_clarify_tool.py',
 'tests/gateway/test_discord_guild_channel_only.py','tests/gateway/test_discord_command_identity.py','tests/gateway/test_discord_sync_limit.py']
python='/home/outsider/.cache/lifeos-atlas-20261010/native-test-python313/bin/python'
started=time.monotonic();results=[]
for path in paths:
    command=[python,'-m','pytest','-W','error','-q',path]
    if path.endswith(('test_discord_guild_channel_only.py','test_discord_command_identity.py')):
        command=[python,'-c','import discord,discord.ext.commands;import pytest,sys;sys.exit(pytest.main(sys.argv[1:]))','-W','error','-q',path]
    result=subprocess.run(command,cwd=hermes,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=str(hermes)),capture_output=True,text=True,timeout=300)
    results.append({'command':command,'exit_code':result.returncode,'stdout':result.stdout,'stderr':result.stderr})
report={'commands':results,'exit_code':int(any(row['exit_code'] for row in results)),
    'elapsed_seconds':time.monotonic()-started,'source':str(hermes),
    'scope':'Native unit controls with simulated Discord transport. Installed acceptance remains separate.'}
(out/'native-controls.json').write_text(json.dumps(report,indent=2)+'\n')
(out/'native-controls.done').write_text(str(report['exit_code'])+'\n')
