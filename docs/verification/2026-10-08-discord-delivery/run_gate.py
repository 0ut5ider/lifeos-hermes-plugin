# ABOUTME: Verifies private Discord delivery against prepared sources and separate SDK and simulated test environments.
# ABOUTME: Saves every child result and a durable combined completion marker.
import importlib.metadata
import json
import os
from pathlib import Path
import signal
import subprocess
import sys

root=Path(__file__).resolve().parents[3]
evidence=Path(__file__).resolve().parent
hermes=Path(sys.argv[1]).resolve()
lifeos=Path(sys.argv[2]).resolve()
environment=dict(os.environ,PYTHONPATH=os.pathsep.join((str(root),str(root/'tests'),str(hermes))),
                 LIFEOS_MEMORY_SOURCE=str(lifeos),LIFEOS_HERMES_REBUILD_SOURCE=str(hermes))
inherited_sigint=str(signal.getsignal(signal.SIGINT))
signal.signal(signal.SIGINT,signal.default_int_handler)
native_modules=['tests/hermes_cli/test_required_policy_hooks.py','tests/gateway/test_discord_send.py',
    'tests/gateway/test_discord_attachment_receipts.py','tests/plugins/platforms/test_discord_gate_isolation.py',
    'tests/gateway/test_discord_clarify_buttons.py','tests/gateway/test_discord_view_base_parity.py']
commands=[
    ('package-final',root,['-W','error','-m','unittest','test_discord_private_delivery','test_discord_audience',
        'test_plugin_lifecycle','test_hermes_memory_provider','test_patch_bundle','-v']),
    ('sdk-channel-final',hermes,['-W','error','-m','unittest','tests.gateway.test_discord_guild_channel_only','-v']),
    ('native-final',hermes,['-m','pytest',*native_modules,'-q','-W','error']),
    ('install-final',root,['-m','unittest','test_capability_validation','test_install_step',
        'test_hermes_install_source','test_lifeos_install_source','test_hermes_patch_regeneration','-v']),
]
results=[]
for name,cwd,arguments in commands:
    with (evidence/(name+'.txt')).open('w') as output:
        completed=subprocess.run([sys.executable,*arguments],cwd=cwd,env=environment,
                                 stdout=output,stderr=subprocess.STDOUT,check=False)
    results.append({'name':name,'exit_code':completed.returncode})
    print(json.dumps(results[-1]),flush=True)
receipt={'results':results,'inherited_sigint':inherited_sigint,'versions':{name:importlib.metadata.version(name)
    for name in ('discord.py','aiohttp','pytest')}}
(evidence/'gate-results.json').write_text(json.dumps(receipt,indent=2)+'\n')
code=0 if all(row['exit_code']==0 for row in results) else 1
(evidence/'focused.done').write_text(str(code)+'\n')
sys.exit(code)
