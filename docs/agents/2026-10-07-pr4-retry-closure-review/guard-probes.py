# ABOUTME: Records targeted mount guard and unit observation review checks.
# ABOUTME: Uses disposable selection fixtures without changing the repository implementation.
import json
from pathlib import Path
import test_installation_selection as native
import test_selection_profile_isolation as dashboard
from lifeos_hook_bridge import lifeos_installation
from lifeos_hook_bridge.selection_worker import _recover_mount
results=[]
for case in ('matching_target', 'foreign_root', 'foreign_profile', 'foreign_entry', 'foreign_workspace', 'public_journal', 'public_state', 'clear_matching_workspace', 'clear_later_edit'):
    fixture=native.InstallationSelectionTests()
    fixture.setUp()
    try:
        fixture.prepare_previous_mount()
        fixture.crash_native_mount('select-committed')
        journal=fixture.profile/'.lifeos-mount/operation.json'
        value=json.loads(journal.read_text())
        if case=='foreign_root': value['installed']=str(fixture.root/'third/.claude')
        if case=='foreign_profile': value['profile']=str(fixture.root/'third-profile')
        if case=='foreign_entry': value['entries'][0]['target']=str(fixture.root/'third/SOUL.md')
        if case=='foreign_workspace': value['workspace']=str(fixture.root/'third-workspace')
        journal.write_text(json.dumps(value))
        if case=='public_journal': journal.chmod(0o644)
        if case=='public_state': journal.parent.chmod(0o755)
        if case.startswith('clear_'): lifeos_installation.clear(fixture.profile)
        soul=fixture.profile/'SOUL.md'
        if case=='clear_later_edit': soul.write_text('Synthetic owner edit after clear')
        before=soul.read_bytes()
        rejected=False
        error=None
        try: _recover_mount(fixture.store/'.claude',fixture.profile,previous=fixture.account/'.claude')
        except RuntimeError as caught: rejected=True; error=str(caught)
        expected=case not in {'matching_target','clear_matching_workspace'}
        assert rejected==expected,(case,rejected,error)
        assert soul.read_bytes()==before,case
        results.append({'case':case,'rejected':rejected,'error':error,'soul_preserved':True})
    finally: fixture.doCleanups()
fixture=dashboard.SelectionProfileIsolationTests()
fixture.setUp()
try:
    job=fixture.job(fixture.b,'observation',state='queued',journal=False)
    saved={'state':'queued','unit':'synthetic-review-unit'}
    (job/'status.json').write_text(json.dumps(saved))
    before=(job/'status.json').read_bytes()
    for state in ('inactive','failed','active','activating','deactivating','reloading','maintenance','refreshing'):
        (fixture.home/'bin/systemctl').write_text('#!'+__import__('sys').executable+'\nprint('+repr('ActiveState='+state+'\nJob=')+')\n')
        observed=fixture.api._selection_job_status(job)
        expected='failed' if state in {'inactive','failed'} else 'queued'
        assert observed['state']==expected,(state,observed)
        assert (job/'status.json').read_bytes()==before,state
        results.append({'case':'unit_'+state,'observed':observed,'stored_status_preserved':True})
finally: fixture.doCleanups()
print(json.dumps(results,indent=2))
