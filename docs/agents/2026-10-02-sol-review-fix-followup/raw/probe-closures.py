# ABOUTME: Reproduces the reviewed restore crash and source-label scenarios after correction.
# ABOUTME: Uses public native code, real process death, and synthetic service boundaries.
import json,os,signal,subprocess,sys,tempfile
from pathlib import Path
from unittest.mock import patch
from test_update_transaction import UpdateTransactionTests
from test_memory_source_labels import MemorySourceLabelTests
from test_memory_native import OWNER
from lifeos_hook_bridge.update_transaction import apply_update,restore_update,recover_update,validate_restore,UpdateTransactionError
from lifeos_hook_bridge.memory_canonical import corpus
OUT=Path(__file__).parent
results={}
with tempfile.TemporaryDirectory(prefix='restore-closure-') as directory:
    helper=UpdateTransactionTests()
    installed,profile,prior,selected,reference,baseline,snapshot=helper.fixture(Path(directory))
    events,stop,start,mount,renew,verify=helper.callbacks(profile,baseline)
    apply_update(installed,profile,prior,selected,reference,baseline,snapshot,stop=stop,start=start,mount=mount,renew=renew,verify=verify)
    stopped=Path(directory)/'synthetic-stopped'
    code='import os,signal,sys\nfrom pathlib import Path\nfrom lifeos_hook_bridge.update_transaction import restore_update\ndef stop():\n Path(sys.argv[2]).write_text("synthetic service stopped")\n os.kill(os.getpid(),signal.SIGKILL)\nrestore_update(Path(sys.argv[1]),stop=stop,start=lambda:None,verify=lambda:None)\n'
    child=subprocess.run([sys.executable,'-c',code,str(snapshot),str(stopped)],text=True,capture_output=True)
    before=json.loads((snapshot/'manifest.json').read_text())['state']
    (installed/'LIFEOS/MEMORY/user.txt').write_text('Synthetic later memory')
    (profile/'SOUL.md').write_text('Synthetic later profile')
    baseline_before=baseline.read_bytes()
    events.clear()
    recovered=recover_update(snapshot,stop=stop,start=start,verify=lambda:events.append('verify'))
    try:
        validate_restore(snapshot)
        later_restore='unexpectedly allowed'
    except UpdateTransactionError as error:
        later_restore=str(error)
    results['restore']={'child_exit':child.returncode,'child_stdout':child.stdout,'child_stderr':child.stderr,'service_boundary_stopped':stopped.is_file(),'durable_crash_state':before,'recovered_state':recovered['state'],'recovery_events':events,'selected_hook':(installed/'hooks/owned.ts').read_text(),'memory':(installed/'LIFEOS/MEMORY/user.txt').read_text(),'profile':(profile/'SOUL.md').read_text(),'baseline_unchanged':baseline.read_bytes()==baseline_before,'prior_still_exists':(snapshot/'live-prior').is_dir(),'selected_archive_created':(snapshot/'restored-selected').exists(),'later_restore':later_restore}
    assert child.returncode == -signal.SIGKILL and before=='restore_stopping'
    assert recovered['state']=='applied' and events==['start','verify']
    assert (installed/'hooks/owned.ts').read_text()=='owned-v2'
    assert results['restore']['memory']=='Synthetic later memory' and results['restore']['profile']=='Synthetic later profile'
    assert baseline.read_bytes()==baseline_before and later_restore!='unexpectedly allowed'

for scenario in ('private_filename','private_title','retired_filename','retired_title','operational_domain'):
    helper=MemorySourceLabelTests();helper.setUp()
    try:
        name='safe-source'; title='Safe synthetic title'; marker=''
        if scenario=='private_filename': name='<private>SYNTHETIC_PRIVATE_LABEL';marker='SYNTHETIC_PRIVATE_LABEL'
        elif scenario=='private_title':title='<private>SYNTHETIC_PRIVATE_TITLE';marker='SYNTHETIC_PRIVATE_TITLE'
        elif scenario=='retired_filename':helper.retire();name='Synthetic_retired_source_label';marker=name
        elif scenario=='retired_title':helper.retire();title='Synthetic retired source label';marker=title
        elif scenario=='operational_domain':
            saved=helper.fixture.remember('RULE: research','retire-domain','principal')
            helper.memory.forget(OWNER,saved['reference'],'forget-domain')
        path=helper.note(name,title)
        preview=helper.preferences.preview_adoption(account='dashboard:synthetic-owner')
        # Register directly to represent persisted registrations from before the fix.
        with helper.memory._transaction() as connection:
            helper.memory._record(connection,OWNER,path,'SafeSyntheticCurrentBody','project','lab',{'kind':'adopted'})
        try:
            canonical=corpus(helper.memory,OWNER,str(helper.root/'LIFEOS/MEMORY'))
        except Exception as error:
            canonical={'refused':type(error).__name__,'message':str(error)}
        try:
            knowledge,_=helper.preferences.knowledge_response('/api/knowledge',account='dashboard:synthetic-owner')
        except Exception as error:
            knowledge={'refused':type(error).__name__,'message':str(error)}
        search=helper.preferences.review('lifeos_memory_search',{'query':'SafeSyntheticCurrentBody'},account='dashboard:synthetic-owner')
        results[scenario]={'preview_records':len(preview['records']),'preview_marker_exposure':bool(marker and marker in json.dumps(preview)),'canonical':canonical,'knowledge':knowledge,'search':search}
        if scenario in ('private_filename','private_title','retired_filename'):
            assert not preview['records'] and marker not in json.dumps(preview)
            assert canonical['records']==[] and knowledge['body']['totalNotes']==0 and search['results']==[]
        elif scenario=='retired_title':
            assert canonical['refused']=='MemoryUnavailable'
        else:
            assert len(canonical['records'])==1 and knowledge['body']['totalNotes']==1 and len(search['results'])==1
    finally:
        helper.doCleanups()
print(json.dumps(results,indent=2))
