# ABOUTME: Captures real agent turns and their local HTTP requests from synthetic fixtures.
# ABOUTME: Keeps the admitted native receipt and denied-author outcome available for review.
from pathlib import Path
import json
import sys

repository = Path.cwd()
sys.path[:0] = [str(repository),str(repository/'tests')]
from test_memory_agent import MemoryAgentTests

for case,name in (('allowed','test_actual_agent_turn_commits_native_fact_and_reports_its_receipt'),
                  ('unknown-author','test_actual_agent_turn_rejects_unknown_author_before_model_or_memory_calls')):
    fixture = MemoryAgentTests()
    fixture.setUp()
    try:
        getattr(fixture,name)()
        print(json.dumps({'case':case,'outcome':fixture.outcome,'requests':fixture.fixture.fixture.received}),flush=True)
    finally:
        fixture.doCleanups()
