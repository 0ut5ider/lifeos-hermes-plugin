# ABOUTME: Saves actual foreground and background review wire bodies from synthetic profiles.
# ABOUTME: Records native skill and pending files after the bounded assertions pass.
import json
from pathlib import Path
import sys


repository = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(repository),str(repository/'tests')]
from test_memory_review import MemoryReviewTests


results = []
for method in sorted(name for name in dir(MemoryReviewTests) if name.startswith('test_')):
    case = MemoryReviewTests(method)
    case.setUp()
    try:
        getattr(case,method)()
        files = {}
        for directory in ('skills','pending/skills','memories'):
            root = case.fixture.home/directory
            for path in sorted(root.rglob('*')):
                if path.is_file():
                    files[str(path.relative_to(case.fixture.home))] = path.read_text()
        results.append({'case':method,'outcome':case.outcome,'requests':case.fixture.fixture.received,
                        'files':files})
    finally:
        case.doCleanups()
print(json.dumps(results,indent=2))
