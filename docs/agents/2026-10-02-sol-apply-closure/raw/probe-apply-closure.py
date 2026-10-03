# ABOUTME: Checks apply stop intent, direct recovery, and authenticated recovery admission.
# ABOUTME: Uses a killed child and separate disposable service and native owner fixtures.
import json,signal,subprocess,sys,tempfile
from pathlib import Path
from unittest.mock import patch
from test_update_transaction import UpdateTransactionTests
from test_memory_admin_dashboard import MemoryAdminDashboardTests
from lifeos_hook_bridge.update_transaction import recover_update
results={}
with tempfile.TemporaryDirectory(prefix='apply-closure-') as directory:
    root=Path(directory)
    helper=UpdateTransactionTests()
    installed,profile,prior,selected,reference,baseline,snapshot=helper.fixture(root)
    user_before=(installed/'LIFEOS/MEMORY/user.txt').read_bytes()
    profile_before={name:(profile/name).read_bytes() for name in ('config.yaml','SOUL.md')}
    baseline_before=baseline.read_bytes()
    marker=root/'synthetic-stopped'
    program='import os,signal,sys\nfrom pathlib import Path\nfrom lifeos_hook_bridge.update_transaction import apply_update\ndef stop():\n Path(sys.argv[8]).write_text("synthetic service stopped")\n os.kill(os.getpid(),signal.SIGKILL)\napply_update(*[Path(arg) for arg in sys.argv[1:8]],stop=stop,start=lambda:None,mount=lambda:None,renew=lambda a,b:None,verify=lambda:None)\n'
    command=[sys.executable,'-c',program,*map(str,(installed,profile,prior,selected,reference,baseline,snapshot,marker))]
    child=subprocess.run(command,text=True,capture_output=True,timeout=30)
    crashed_state=json.loads((snapshot/'manifest.json').read_text())['state']
    events,stop,start,_,_,_=helper.callbacks(profile,baseline)
    result=recover_update(snapshot,stop=stop,start=start,verify=lambda:events.append('verify'))
    results['apply_recovery']={'command':command,'child_exit':child.returncode,'stdout':child.stdout,'stderr':child.stderr,'service_boundary_stopped':marker.is_file(),'crashed_state':crashed_state,'recovered_state':result['state'],'recovery_events':events,'program_hook':(installed/'hooks/owned.ts').read_text(),'user_data_unchanged':(installed/'LIFEOS/MEMORY/user.txt').read_bytes()==user_before,'profile_unchanged':all((profile/name).read_bytes()==value for name,value in profile_before.items()),'baseline_unchanged':baseline.read_bytes()==baseline_before}
    assert child.returncode==-signal.SIGKILL and child.stderr=='' and crashed_state=='stopped'
    assert result['state']=='rolled_back' and events==['stop','start','verify']
    assert results['apply_recovery']['program_hook']=='owned-v1'
    assert all(results['apply_recovery'][name] for name in ('service_boundary_stopped','user_data_unchanged','profile_unchanged','baseline_unchanged'))

# Use actual dashboard authentication and grant creation in its native source fixture.
# Substitute only the systemd liveness and detached worker launch boundaries.
owner=MemoryAdminDashboardTests();owner.setUp()
try:
    owner.login();job=owner.interrupted_job()
    (job/'snapshot/manifest.json').write_text(json.dumps({'state':'stopped'}))
    (job/'status.json').write_text(json.dumps({'state':'applying','unit':'synthetic-dead-worker'}))
    with patch.object(owner.api.subprocess,'run',return_value=subprocess.CompletedProcess([],3,'inactive\n','')):
        status=owner.api.get_lifeos_update_status()
        with patch.object(owner.api,'_launch_lifeos_update') as launched:
            response=owner.post('/update/recover')
    request=json.loads((job/'request.json').read_text())
    authorization=Path(request['memory_authorization'])
    owner.addCleanup(owner.fixture.fixture.admin().revoke,owner.configuration,authorization)
    owner.fixture.fixture.admin().validate(owner.configuration,authorization,binding=owner.fixture.fixture.admin().job_binding(job,request,'recover'),check_binding=True,purpose='recover')
    results['authenticated_admission']={'dashboard_state':status['state'],'transaction_state':status['transaction_state'],'http_status':response.status_code,'response':response.json(),'recovery_launch_count':launched.call_count,'recover_bound_authorization_valid':True}
    assert status['state']=='interrupted' and status['transaction_state']=='stopped'
    assert response.status_code==200,response.text
    launched.assert_called_once_with(job,'recover')
finally:
    owner.doCleanups()
print(json.dumps(results,indent=2))
