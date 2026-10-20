# ABOUTME: Probes that standalone recovery refuses a retained removal plan without recovery_login.
# ABOUTME: Uses the real RemovalStateTests fixture; patches only the interactive prompts and launch.
import sys, json, io, contextlib
from unittest import mock
sys.path.insert(0,'tests')
import test_removal_state as fixture
from optional.lifeos_release_manager import removal_recovery, memory_workflow
t=fixture.RemovalStateTests();t.setUp()
try:
    marker=json.loads((t.profile/'.lifeos-removal.json').read_text())
    print('plan has recovery_login:', 'recovery_login' in t.plan)
    launched=[]
    argv=['recover',str(t.profile),t.job.name,'recover',marker['signature']]
    err=io.StringIO()
    with mock.patch.object(sys,'argv',argv),mock.patch('builtins.input',return_value='owner'),\
         mock.patch('getpass.getpass',return_value='synthetic-password'),\
         mock.patch.object(memory_workflow,'launch',lambda *a:launched.append(a)),contextlib.redirect_stderr(err):
        code=removal_recovery.main()
    print('exit:',code,'stderr:',err.getvalue().strip(),'launched:',launched)
    # Why it refused: call recovery_login on the plan value directly.
    try: removal_recovery.recovery_login(t.plan.get('recovery_login'),t.plan['owner'])
    except Exception as e: print('recovery_login refuses:',type(e).__name__,e)
finally:
    t.doCleanups()
