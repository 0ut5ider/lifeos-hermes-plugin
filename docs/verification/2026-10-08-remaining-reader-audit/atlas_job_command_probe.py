# ABOUTME: Observes actual Atlas owner-command RPC results without replacing their values.
# ABOUTME: Retains only synthetic operation results and leaves selected source code unchanged.
import json
from pathlib import Path
import sys
import test_memory_atlas_jobs as fixtures

root = Path(__file__).resolve().parent
fixture = fixtures.MemoryAtlasJobCommandTests()
fixture.setUp()
try:
    command = fixture.fixture.fixture
    profile = command.fixture.home
    rpc = profile / 'plugins/lifeos-hook-bridge/memory_rpc.py'
    original = rpc.with_name('actual_memory_rpc.py')
    rpc.rename(original)
    observations = profile / 'atlas-rpc-observations.jsonl'
    rpc.write_text('import json,sys,subprocess;from pathlib import Path\n'
        'wire=sys.stdin.buffer.read();request=json.loads(wire)\n'
        'result=subprocess.run([sys.executable,' + repr(str(original)) + ',*sys.argv[1:]],input=wire,capture_output=True)\n'
        'with Path(' + repr(str(observations)) + ').open("a") as stream:stream.write(json.dumps({"operation":request["operation"],"result":json.loads(result.stdout)})+"\\n")\n'
        'sys.stdout.buffer.write(result.stdout);sys.stderr.buffer.write(result.stderr);sys.exit(result.returncode)\n')
    rpc.chmod(0o600)
    result = command.call('atlas-insights')
    records = [json.loads(line) for line in observations.read_text().splitlines()] if observations.exists() else []
    record = {'exit_code': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr, 'actual_rpc_results': records}
    (root / 'atlas-job-command-observation.json').write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps(record))
finally: fixture.doCleanups()
