# ABOUTME: Measures account selection admission after a local selection launcher fails.
# ABOUTME: Records dashboard responses against synthetic owner profiles without starting services.
import json
from pathlib import Path
import sys

import test_selection_profile_isolation as fixture_module
from lifeos_hook_bridge.lifeos_installation import publish
from lifeos_hook_bridge.memory_service import MemoryConfiguration

fixture = fixture_module.SelectionProfileIsolationTests()
fixture.setUp()
try:
    target = fixture.home / 'fresh/home'
    (target / '.claude/LIFEOS').mkdir(parents=True)
    publish(fixture.b, target, fixture.home / 'HermesWorkspace')
    MemoryConfiguration(fixture.b / 'lifeos-memory.json').update(
        lambda value: value.update(root=str(target / '.claude')))
    fixture.api.INSTALLED_ROOT = target / '.claude'
    launcher = fixture.home / 'bin/systemd-run'
    launcher.write_text('#!' + sys.executable + '\nimport sys\nsys.exit(23)\n')
    controller = fixture.home / 'bin/systemctl'
    controller.write_text('#!' + sys.executable + '\nimport sys\nprint("inactive")\nsys.exit(3)\n')
    results = []
    def response(label, action):
        try:
            value = action()
        except fixture.api.HTTPException as error:
            value = {'http_status': error.status_code, 'detail': error.detail}
        results.append({'action': label, 'result': value})
    response('initial_return_failed_launch', lambda: fixture.api._queue_selection(fixture.owner_b, None))
    job = fixture.api._latest_selection()
    results.append({'action': 'stored_job', 'request': json.loads((job / 'request.json').read_text()),
        'status_file': json.loads((job / 'status.json').read_text()),
        'transaction_journal_exists': (job / 'transaction/journal.json').exists(),
        'observed_status': fixture.api._selection_status()})
    response('next_return', lambda: fixture.api._queue_selection(fixture.owner_b, None))
    response('recover', fixture.recover)
    data = {'results': results, 'scope': 'Local failing launch/control transport; no live systemd services.'}
    (Path(__file__).parent / 'failed-launch-results.json').write_text(json.dumps(data, indent=2) + '\n')
    print(json.dumps(data, indent=2))
finally:
    fixture.doCleanups()
