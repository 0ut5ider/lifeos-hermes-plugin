# ABOUTME: Checks source labels in early adoption diagnostic paths and error reasons.
# ABOUTME: Uses native synthetic owner fixtures with ownership and sharing disabled.
import json
from pathlib import Path
from test_memory_source_labels import MemorySourceLabelTests
from test_memory_native import OWNER
from lifeos_hook_bridge.memory_proposals import QUEUE
results={}
for scenario in ('private_early_body','retired_early_body','safe_early_body','retired_foreign_proposal_reason'):
    helper=MemorySourceLabelTests();helper.setUp()
    try:
        helper.retire()
        if scenario=='retired_foreign_proposal_reason':
            target=helper.root.parent/'Synthetic_retired_source_label.md'
            queue=helper.memory._path(QUEUE);queue.parent.mkdir(parents=True,exist_ok=True)
            row={'id':'synthetic-foreign-proposal','status':'pending','target_kind':'operational-rule','target_file':str(target),'edit':'Safe synthetic proposal edit','confidence':0.8,'rationale':'Safe synthetic proposal rationale'}
            queue.write_text(json.dumps(row)+'\n')
            marker='Synthetic_retired_source_label'
            normalized=helper.memory.filter_history(OWNER,'Synthetic retired source label','2099-01-01T00:00:00Z')
        else:
            name={'private_early_body':'<private>SYNTHETIC_PRIVATE_REJECTED_LABEL','retired_early_body':'Synthetic_retired_source_label','safe_early_body':'safe-rejected-source'}[scenario]
            path=helper.note(name)
            path.write_text(path.read_text().replace('SafeSyntheticCurrentBody','Synthetic retired source label'))
            marker=name.removeprefix('<private>')
        preview=helper.preferences.preview_adoption(account='dashboard:synthetic-owner')
        results[scenario]={'records':preview['records'],'excluded':preview['excluded'],'marker_in_response':marker in json.dumps(preview),'signature':preview['signature']}
        if scenario=='retired_foreign_proposal_reason':results[scenario]['normalized_label_excluded']=normalized['excluded']
        else:
            assert preview['records']==[] and preview['excluded']
            if scenario=='safe_early_body':assert preview['excluded'][0]['path'].endswith('safe-rejected-source.md')
            else:assert not results[scenario]['marker_in_response'] and preview['excluded'][0]['path']=='[excluded source]'
    finally:
        helper.doCleanups()
print(json.dumps(results,indent=2))
