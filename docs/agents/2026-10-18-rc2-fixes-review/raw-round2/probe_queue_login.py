# ABOUTME: Probes that a queued removal stores the provider login in an owner-only request.json.
# ABOUTME: Uses the real release dashboard fixture and a recording launch; also checks a missing login refuses.
import sys, os, stat, json
sys.path.insert(0,'tests')
import test_release_dashboard as fixture
from optional.lifeos_release_manager import memory_workflow
from optional.lifeos_release_manager.dashboard.plugin_api import dashboard_login
t=fixture.ReleaseDashboardTests();t.setUp()
try:
    sel={'kind':'removal','identifier':'c'*32,'signature':'d'*64,'disable_discord':True}
    try: memory_workflow.queue(t.profile,sel,owner='dashboard:basic:owner',launch=lambda *a:None)
    except Exception as e: print('no login:',type(e).__name__,e)
    print('jobs after refusal:',sorted(p.name for p in (t.profile/'.lifeos-portability').iterdir()) if (t.profile/'.lifeos-portability').exists() else None)
    login=dashboard_login('dashboard:basic:owner')
    launched=[]
    try: print('queued:',memory_workflow.queue(t.profile,sel,owner='dashboard:basic:owner',launch=lambda *a:launched.append(a),login=login))
    except Exception as e: print('queue raised:',type(e).__name__,e)
    for job in (t.profile/'.lifeos-portability').iterdir():
        r=job/'request.json'
        print(job.name,'dir mode',oct(stat.S_IMODE(job.stat().st_mode)),'request mode',oct(stat.S_IMODE(r.stat().st_mode)),
              'login keys',sorted(json.loads(r.read_text()).get('login',{})))
        print('workflow_job ok:', memory_workflow.workflow_job(t.profile,job.name)[1]['login']['username'])
finally:
    t.doCleanups()
