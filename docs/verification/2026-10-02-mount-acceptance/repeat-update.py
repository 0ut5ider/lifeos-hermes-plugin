# ABOUTME: Rehearses a second pinned update under the isolated operating-system account.
# ABOUTME: Starts the actual detached worker with a new action-bound owner grant.
import importlib.util
import json
from pathlib import Path
from uuid import uuid4

home = Path.home()
path = home / '.hermes/plugins/lifeos-hook-bridge/dashboard/plugin_api.py'
spec = importlib.util.spec_from_file_location('acceptance_update_api', path)
api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api)
api.HOST_SOURCE = home / 'workspace/hermes'
previous = Path(api.get_lifeos_update_status()['job'])
request = json.loads((previous / 'request.json').read_text())
request.pop('memory_authorization', None)
job = api.LIFEOS_UPDATE_ROOT / ('update-' + uuid4().hex)
job.mkdir(mode=0o700)
preferences = api._memory_preferences()
grant = preferences.authorize_mount(account='dashboard:basic:adrian', ttl=3600,
    binding=api.install_module.memory_administration().job_binding(job, request, 'apply'))
request['memory_authorization'] = str(grant)
try:
    for name, data in [('request.json', request), ('status.json', {'state': 'queued'})]:
        api.install_module.memory_administration().publish(job / name, (json.dumps(data) + '\n').encode())
    api._launch_lifeos_update(job)
except BaseException:
    preferences.revoke_mount(grant)
    raise
print(json.dumps({'state': 'queued', 'job': str(job), 'entry': 'local operator rehearsal'}))
