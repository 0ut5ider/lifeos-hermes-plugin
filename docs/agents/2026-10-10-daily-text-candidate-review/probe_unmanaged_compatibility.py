# ABOUTME: Separates standalone native compatibility from contradictory managed test contexts.
# ABOUTME: Exercises actual native rejection, promotion, and mining without a connector or context.
import json
from test_memory_staging import MemoryStagingTests
from test_memory_knowledge_harvest import MemoryKnowledgeHarvestTests
results=[]
for operation in ('reject','promote','harvest'):
    fixture=MemoryKnowledgeHarvestTests() if operation=='harvest' else MemoryStagingTests()
    fixture.setUp()
    try:
        r=fixture.call(managed=False,context=False) if operation=='harvest' else fixture.native_call(operation,fixture.selector,managed=False,context=False)
        results.append({'operation':operation,'exit_code':r.returncode,'stdout':r.stdout,'stderr':r.stderr})
        assert r.returncode==0,(operation,r.stdout,r.stderr)
        if operation=='harvest':assert not fixture.queue.exists() and fixture.note.exists()
        elif operation=='reject':assert not fixture.staged.exists()
        else:assert not fixture.staged.exists() and fixture.target.exists()
    finally:fixture.doCleanups()
print(json.dumps(results,indent=2))
