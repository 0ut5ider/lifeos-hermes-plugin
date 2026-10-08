# ABOUTME: Observes actual native job completion in a separate owner process.
# ABOUTME: Revokes a real policy grant after native writes and records the delivered result.
import json
from pathlib import Path
import sys

from lifeos_hook_bridge import memory_owner_jobs
from lifeos_hook_bridge.memory_service import MemoryConfiguration


configuration = MemoryConfiguration(Path(sys.argv[1]))
route = json.loads(sys.argv[2])
mapping = json.loads(sys.argv[3])
original = memory_owner_jobs._command
observed = []


def command(*args):
    result = original(*args)
    environment = args[1]
    observed.append({'context': json.loads(environment['LIFEOS_MEMORY_CONTEXT']),
        'home': environment['HOME'], 'mapping': json.loads(environment['LIFEOS_MODEL_TIER_MAP']),
        'scheduled_metadata': [key for key in environment if key.startswith('HERMES_CRON_')]})
    if len(observed) == 2 and sys.argv[4] == 'revoke':
        configuration.update(lambda value: value['accounts'].pop('terminal:' + observed[0]['context']['author']))
    return result


memory_owner_jobs._command = command
try:
    result = memory_owner_jobs.OwnerJobs(configuration.path).run('memory-consolidation', route=route, mapping=mapping)
except memory_owner_jobs.MemoryAdmissionError:
    result = {'status': 'authority-refused'}
print(json.dumps({'result': result, 'observed': observed}))
