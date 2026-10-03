# ABOUTME: Measures the real Hermes review fork after a memory-owned foreground turn.
# ABOUTME: Uses private synthetic profiles and loopback HTTP without changing plugin code.
from pathlib import Path
import json
import os
import subprocess
import sys

repository = Path('/home/outsider/Projects/Hermes_agent/LifeOS_plugin')
sys.path[:0] = [str(repository),str(repository/'tests')]
from test_memory_host import MemoryHostTests

fixture = MemoryHostTests()
fixture.setUp()
try:
    source = (repository/'tests/memory_host_calls.py').read_text().replace('str(Path(__file__).parents[1])','str(repository)')
    source = source.replace("sys.path[:0] =", "repository = Path('/home/outsider/Projects/Hermes_agent/LifeOS_plugin')\nsys.path[:0] =")
    source = source.replace("logger.addHandler(handler)","logger.addHandler(handler)\n    logging.getLogger('agent.background_review').addHandler(handler)")
    source = source.replace("        denied_writes = []", """        review_results=[]
        import threading
        def review_trace(frame,event,arg):
            if event=='return' and frame.f_code.co_name=='run_conversation':
                review_results.append(arg)
            return review_trace
        threading.settrace(review_trace)
        if settings.get('operation') == 'conversation':
            from agent.background_review import wait_for_background_review_run
            agent._spawn_background_review(conversation['messages'],review_skills=True,focus='Synthetic review probe',explicit=True)
            review_done = wait_for_background_review_run(agent,timeout=20)
            print(json.dumps({'background_done':review_done,'review_results':review_results}),file=diagnostics)
        denied_writes = []""")
    # Use the host lifecycle's actual completion event if the installed name differs.
    host = Path(os.environ['LIFEOS_HERMES_SOURCE'])
    definitions = (host/'agent/background_review.py').read_text()
    if 'def wait_for_background_review_run' not in definitions:
        source = source.replace('            from agent.background_review import wait_for_background_review_run\n','            import time\n')
        source = source.replace('            review_done = wait_for_background_review_run(agent,timeout=20)',"""            deadline = time.monotonic()+20
            while time.monotonic()<deadline and getattr(agent,'_background_review_run',None) is not None:
                time.sleep(0.05)
            review_done = getattr(agent,'_background_review_run',None) is None""")
    program = fixture.home/'background_probe.py'
    program.write_text(source)
    config = dict(fixture.fixture.host_config,memory={'provider':'lifeos-hook-bridge','memory_enabled':False,'user_profile_enabled':False},
                  plugins={'enabled':['lifeos-hook-bridge']})
    config['model']=dict(config['model'],streaming=False,context_length=131072)
    (fixture.home/'config.yaml').write_text(json.dumps(config))
    environment = {key:os.environ[key] for key in ('PATH','LANG','TZ') if key in os.environ}
    environment.update(HOME=str(fixture.fixture.fixture.fixture.home),HERMES_HOME=str(fixture.home),LIFEOS_HERMES_SOURCE=str(host),
                       LIFEOS_HOOK_SETTINGS=str(fixture.fixture.fixture.fixture.root/'settings.json'),BUN_CONFIG_NO_AUTO_INSTALL='1')
    result = subprocess.run([sys.executable,str(program)],env=environment,
               input=json.dumps({'route':fixture.fixture.route,'operation':'conversation','message':'Synthetic foreground request'}),
               text=True,capture_output=True,timeout=40)
    print(json.dumps({'returncode':result.returncode,'stdout':result.stdout,'stderr':result.stderr,
                     'requests':fixture.fixture.received}),flush=True)
finally:
    fixture.doCleanups()
