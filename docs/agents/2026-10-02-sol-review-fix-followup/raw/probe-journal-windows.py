# ABOUTME: Checks completed recovery reconciliation and the adjacent apply stop interval.
# ABOUTME: Uses disposable files and real killed children with simulated service callbacks.
import json,os,signal,subprocess,sys,tempfile
from pathlib import Path
from unittest.mock import patch
from test_update_transaction import UpdateTransactionTests
from lifeos_hook_bridge.update_transaction import apply_update,recover_update
from lifeos_hook_bridge.dashboard import plugin_api as api
results={}
with tempfile.TemporaryDirectory(prefix='journal-windows-') as directory:
    root=Path(directory)
    for scenario in ('recovery_completed_before_status','apply_stop_before_journal'):
        job=root/scenario/'jobs/update-synthetic';job.mkdir(parents=True)
        helper=UpdateTransactionTests()
        installed,profile,prior,selected,reference,baseline,_=helper.fixture(root/scenario/'program')
        snapshot=job/'snapshot'
        events,stop,start,mount,renew,verify=helper.callbacks(profile,baseline)
        stopped=job/'synthetic-stopped'
        if scenario=='recovery_completed_before_status':
            apply_update(installed,profile,prior,selected,reference,baseline,snapshot,stop=stop,start=start,mount=mount,renew=renew,verify=verify)
            manifest=json.loads((snapshot/'manifest.json').read_text());manifest['state']='restore_stopping'
            (snapshot/'manifest.json').write_text(json.dumps(manifest))
            (installed/'LIFEOS/MEMORY/user.txt').write_text('Synthetic later memory')
            (profile/'config.yaml').write_text('Synthetic later profile')
            code='import os,signal,sys\nfrom pathlib import Path\nfrom lifeos_hook_bridge.update_transaction import recover_update\nrecover_update(Path(sys.argv[1]),stop=lambda:None,start=lambda:None,verify=lambda:None)\nos.kill(os.getpid(),signal.SIGKILL)\n'
            args=[str(snapshot)];job_state='recovering'
        else:
            code='import os,signal,sys\nfrom pathlib import Path\nfrom lifeos_hook_bridge.update_transaction import apply_update\ndef stop():\n Path(sys.argv[8]).write_text("synthetic service stopped")\n os.kill(os.getpid(),signal.SIGKILL)\napply_update(*[Path(a) for a in sys.argv[1:8]],stop=stop,start=lambda:None,mount=lambda:None,renew=lambda a,b:None,verify=lambda:None)\n'
            args=list(map(str,(installed,profile,prior,selected,reference,baseline,snapshot,stopped)));job_state='applying'
        command=[sys.executable,'-c',code,*args]
        child=subprocess.run(command,text=True,capture_output=True)
        (job/'request.json').write_text(json.dumps({'installed':str(installed),'hermes_home':str(profile)}))
        (job/'status.json').write_text(json.dumps({'state':job_state,'unit':'synthetic-dead-worker'}))
        api.LIFEOS_UPDATE_ROOT=job.parent;api.INSTALLED_ROOT=installed;api.HERMES_HOME=profile
        with patch.object(api.subprocess,'run',return_value=subprocess.CompletedProcess([],3,'inactive\n','')):
            status=api.get_lifeos_update_status()
            refusals={}
            if scenario=='apply_stop_before_journal':
                for action,fn in [('restore',api._restore_lifeos_update_locked),('recover',api._recover_lifeos_update_locked)]:
                    try:fn('dashboard:synthetic-owner')
                    except api.HTTPException as error:refusals[action]={'status':error.status_code,'detail':error.detail}
        direct='not retried'
        if scenario=='apply_stop_before_journal':
            try:recover_update(snapshot,stop=lambda:None,start=lambda:None,verify=lambda:None)
            except Exception as error:direct=str(error)
        results[scenario]={'command':command,'child_exit':child.returncode,'stdout':child.stdout,'stderr':child.stderr,'transaction_state':json.loads((snapshot/'manifest.json').read_text())['state'],'dashboard':status,'stopped_marker':stopped.is_file(),'refusals':refusals,'direct_recovery':direct,'hook':(installed/'hooks/owned.ts').read_text(),'memory':(installed/'LIFEOS/MEMORY/user.txt').read_text(),'profile':(profile/'config.yaml').read_text()}
        assert child.returncode==-signal.SIGKILL and child.stderr==''
        if scenario=='recovery_completed_before_status':
            assert status['state']=='applied' and status['transaction_state']=='applied'
            assert results[scenario]['hook']=='owned-v2' and results[scenario]['memory']=='Synthetic later memory' and results[scenario]['profile']=='Synthetic later profile'
        else:
            assert status['state']=='interrupted' and status['transaction_state']=='prepared'
            assert stopped.is_file() and refusals['recover']['status']==409
print(json.dumps(results,indent=2))
