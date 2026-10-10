# ABOUTME: Runs native Hermes cancellation and Discord policy unit controls from the frozen package.
# ABOUTME: Records simulated transport scope separately from installed gateway and actual model acceptance.
from pathlib import Path
import os, subprocess, json, time
out=Path(__file__).parent
hermes=Path('/home/outsider/.cache/lifeos-atlas-20261010/daily-text-0.2.0-56b1af9f/hermes')
paths=['tests/gateway/test_stop_clarify_waiters.py','tests/gateway/test_clarify_cancellation_outcome.py',
 'tests/gateway/test_clarify_delivery_fallback.py','tests/tools/test_clarify_gateway.py','tests/tools/test_clarify_tool.py',
 'tests/gateway/test_discord_guild_channel_only.py','tests/gateway/test_discord_command_identity.py','tests/gateway/test_discord_sync_limit.py']
base=['/home/outsider/.cache/lifeos-atlas-20261010/native-test-python313/bin/python','-m','pytest','-W','error','-q']
started=time.monotonic()
results=[]
for path in paths:
    command=[*base,path]
    if path.endswith(('test_discord_guild_channel_only.py','test_discord_command_identity.py')):
        command=[base[0],'-c','import discord, discord.ext.commands; import pytest, sys; sys.exit(pytest.main(sys.argv[1:]))','-W','error','-q',path]
    r=subprocess.run(command,cwd=hermes,env=os.environ|{'PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':str(hermes)},capture_output=True,text=True)
    results.append({'command':command,'exit_code':r.returncode,'stdout':r.stdout,'stderr':r.stderr})
record={'commands':results,'exit_code':int(any(row['exit_code'] for row in results)),
 'elapsed_seconds':time.monotonic()-started,
 'scope':'Native unit controls include simulated Discord transport. Installed acceptance is separate.',
 'isolation':'One fresh pytest subprocess per file, as required by native tests/conftest.py. SDK controls preload real discord so gateway/conftest.py preserves its documented real-module branch.'}
(out/'native-controls.json').write_text(json.dumps(record,indent=2)+'\n')
(out/'native-controls.done').write_text(str(record['exit_code'])+'\n')
