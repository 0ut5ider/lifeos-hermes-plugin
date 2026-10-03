# ABOUTME: Reproduces a retired source label in an excluded proposal diagnostic reason.
# ABOUTME: Asserts that the native owner response omits that retired label.
import json
from test_memory_source_labels import MemorySourceLabelTests
from test_memory_native import OWNER
from lifeos_hook_bridge.memory_proposals import QUEUE
helper=MemorySourceLabelTests();helper.setUp()
try:
    helper.retire()
    target=helper.root.parent/'Synthetic_retired_source_label.md'
    queue=helper.memory._path(QUEUE);queue.parent.mkdir(parents=True,exist_ok=True)
    queue.write_text(json.dumps({'id':'synthetic-foreign-proposal','status':'pending','target_kind':'operational-rule','target_file':str(target),'edit':'Safe synthetic proposal edit','confidence':0.8,'rationale':'Safe synthetic proposal rationale'})+'\n')
    normalized=helper.memory.filter_history(OWNER,'Synthetic retired source label','2099-01-01T00:00:00Z')
    preview=helper.preferences.preview_adoption(account='dashboard:synthetic-owner')
    result={'normalized_label_excluded':normalized['excluded'],'preview':preview,'marker_in_response':'Synthetic_retired_source_label' in json.dumps(preview),'ownership_enabled':helper.configuration.load()['ownership_enabled'],'sharing_enabled':helper.configuration.load()['sharing_enabled']}
    print(json.dumps(result,indent=2),flush=True)
    assert not result['marker_in_response'],'Retired filename enters the excluded proposal reason'
finally:
    helper.doCleanups()
