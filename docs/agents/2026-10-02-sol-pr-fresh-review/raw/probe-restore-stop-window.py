# ABOUTME: Reproduces process death after gateway stop and before restore journal publication.
# ABOUTME: Uses disposable directory transactions and isolates the systemd status boundary.
import json, os, pathlib, signal, subprocess, sys, tempfile
from unittest.mock import patch
from test_update_transaction import UpdateTransactionTests
from lifeos_hook_bridge.update_transaction import apply_update, recover_update
from lifeos_hook_bridge.dashboard import plugin_api as api
OUT=pathlib.Path(__file__).resolve().parent
with tempfile.TemporaryDirectory(prefix='restore-window-',dir=OUT/'fixture-home/tmp') as directory:
    root=pathlib.Path(directory)
    job=root/'updates/update-synthetic';job.mkdir(parents=True)
    installed, profile, prior, selected, reference, baseline, snapshot=UpdateTransactionTests().fixture(root/'program')
    snapshot=job/'snapshot'
    events, stop, start, mount, renew, verify=UpdateTransactionTests().callbacks(profile,baseline)
    apply_update(installed,profile,prior,selected,reference,baseline,snapshot,stop=stop,start=start,mount=mount,renew=renew,verify=verify)
    marker=job/'service-stopped.txt'
    command=[sys.executable,'-c',
        'import os, signal, sys\nfrom pathlib import Path\nfrom lifeos_hook_bridge.update_transaction import restore_update\n'
        'def stopped():\n    Path(sys.argv[2]).write_text("The synthetic service boundary has stopped\\n")\n    os.kill(os.getpid(),signal.SIGKILL)\n'
        'restore_update(Path(sys.argv[1]),stop=stopped,start=lambda:None,verify=lambda:None)\n',str(snapshot),str(marker)]
    child=subprocess.run(command,capture_output=True,text=True)
    request={'installed':str(installed),'hermes_home':str(profile)}
    (job/'request.json').write_text(json.dumps(request))
    (job/'status.json').write_text(json.dumps({'state':'restoring','unit':'synthetic-dead-worker'}))
    api.LIFEOS_UPDATE_ROOT=job.parent;api.INSTALLED_ROOT=installed;api.HERMES_HOME=profile
    with patch.object(api.subprocess,'run',return_value=subprocess.CompletedProcess(['systemctl'],3,'inactive\n','')):
        status=api.get_lifeos_update_status()
        refusals={}
        for action,fn in [('restore',api._restore_lifeos_update_locked),('recover',api._recover_lifeos_update_locked)]:
            try:fn('dashboard:synthetic-owner')
            except api.HTTPException as error:refusals[action]={'status':error.status_code,'detail':error.detail}
    try:recover_update(snapshot,stop=lambda:None,start=lambda:None,verify=lambda:None)
    except Exception as error:direct_refusal=str(error)
    print(json.dumps({'command':command,'child_exit':child.returncode,'child_stdout':child.stdout,'child_stderr':child.stderr,
        'service_boundary_stopped':marker.exists(),'transaction_state':json.loads((snapshot/'manifest.json').read_text())['state'],
        'dashboard_status':status,'dashboard_refusals':refusals,'direct_recovery_refusal':direct_refusal,
        'installed_owned_hook':(installed/'hooks/owned.ts').read_text(),'profile_soul':(profile/'SOUL.md').read_text()},indent=2))
