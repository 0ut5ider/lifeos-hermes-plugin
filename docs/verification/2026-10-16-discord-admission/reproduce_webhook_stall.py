# ABOUTME: Measures event-loop progress against the exact synchronous webhook caller.
# ABOUTME: Loads an isolated baseline module without changing the shared native fixture.
import os,sys,subprocess
from pathlib import Path
c=Path(__file__).parent;r=Path('/home/outsider/Projects/Hermes_agent/LifeOS_plugin')
s=(c/'hermes/gateway/platforms/webhook.py').read_text()
a='await asyncio.to_thread(self._mirror_delivery, platform_name, str(chat_id), content, delivery, thread_id)'
b='self._mirror_delivery(platform_name, str(chat_id), content, delivery, thread_id)'
assert s.count(a)==1
(c/'baseline_webhook.py').write_text(s.replace(a,b))
e=os.environ.copy();e.update(LIFEOS_HERMES_SOURCE=str(c/'hermes'),LIFEOS_MEMORY_SOURCE=str(c/'native-source'),PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=f'{r}:{r}/tests:{c}/hermes')
code="""import importlib.util,sys,unittest
spec=importlib.util.spec_from_file_location('gateway.platforms.webhook','/home/outsider/.cache/lifeos-discord-admission-20261016/baseline_webhook.py')
module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
suite=unittest.defaultTestLoader.loadTestsFromName('test_discord_notification_mirror.DiscordNotificationMirrorTests.test_webhook_mirror_checks_run_outside_the_gateway_event_loop')
result=unittest.TextTestRunner(verbosity=2).run(suite);sys.exit(not result.wasSuccessful())
"""
with (c/'webhook-stall-before.stdout').open('w') as o,(c/'webhook-stall-before.stderr').open('w') as x:
 p=subprocess.run(['/home/outsider/.cache/lifeos-daily-promotion-20261014/frozen-test-environment/bin/python','-c',code],cwd=r,env=e,stdout=o,stderr=x,timeout=60)
print('baseline exit',p.returncode);print((c/'webhook-stall-before.stderr').read_text());assert p.returncode==1
