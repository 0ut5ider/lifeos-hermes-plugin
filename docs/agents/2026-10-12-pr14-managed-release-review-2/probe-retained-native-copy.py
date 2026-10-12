# ABOUTME: Checks retained native copy validation before managed restore preflight returns.
# ABOUTME: Uses a real bound Bun mount in synthetic owner storage and removes one retained copy.
import json
from pathlib import Path
from test_mount_transaction import MountTransactionTests
from optional.lifeos_release_manager.cli import write_state
from optional.lifeos_release_manager.release_operation import request_digest, seal_plan
from optional.lifeos_release_manager.release_programs import ProgramTransaction, publish
from optional.lifeos_release_manager.release_worker import check_restore, _restore_mount, restore_available
fixture = MountTransactionTests()
fixture.setUp()
try:
    job = fixture.profile / '.lifeos-releases' / ('a' * 32)
    job.mkdir(parents=True, mode=0o700)
    request = {'identifier': job.name, 'profile': str(fixture.profile), 'installed': str(fixture.root),
               'version': '0.4.0-dev.1', 'commit': 'b' * 40, 'package_sha256': 'c' * 64}
    publish(job / 'request.json', json.dumps(request).encode())
    write_state(job, 'ready')
    programs = ProgramTransaction(job / 'program-snapshot')
    source = job / 'candidate-config.yaml'
    source.write_bytes((fixture.profile / 'config.yaml').read_bytes())
    source.chmod(0o600)
    programs.prepare(directories={}, files={fixture.profile / 'config.yaml': source})
    programs.apply()
    plan = {'fresh': False, 'native_mount_required': True, 'services': None,
            'program_entries_sha256': programs.entries_digest()}
    seal_plan(job, request, plan)
    publish(fixture.profile / 'integration-release.json', json.dumps(request).encode())
    binding = {'job': str(job), 'request_digest': request_digest(request), 'action': 'apply'}
    publish(job / 'mount-intent.json', b'{"prior_journal_sha256":null,"action":"apply"}')
    grant = fixture.fixture.issue(binding=binding)
    fixture.addCleanup(fixture.fixture.admin().revoke, fixture.fixture.configuration, grant)
    environment = fixture.fixture.admin().mount_environment(fixture.root, fixture.profile, grant, binding=binding)
    from lifeos_hook_bridge.memory_service import MemoryService
    config, scope = fixture.fixture.admin().validate(fixture.fixture.configuration, grant)
    MemoryService(fixture.fixture.configuration)._prompt(config, scope, 'prompt_preview', {'home': str(fixture.profile), 'keepOutputFormat': False})
    transaction = fixture.transaction()
    first = transaction.execute(environment, fixture.fixture.fixture.memory.bun, str(fixture.hermes), binding=binding, retain_for_rollback=True)
    print('real bound mount:', first['state'])
    manifest = json.loads(transaction.journal.read_bytes())
    selected = next(entry for entry in manifest['entries'] if entry['before'] is not None)
    previous = Path(first['snapshot']) / 'previous' / str(selected['copy'])
    print('remove retained copy for:', selected['target'])
    previous.unlink()
    print('restore available after copy loss:', restore_available(job, request, plan))
    check_restore(job, request, plan, transaction)
    print('managed restore preflight after copy loss: PASS')
    before = (fixture.profile / 'config.yaml').read_bytes()
    transaction.restore_completed()
except Exception as error:
    print('actual native restore:', type(error).__name__ + ': ' + str(error))
    print('native journal state after refusal:', json.loads(transaction.journal.read_bytes())['state'])
    print('configuration preserved:', (fixture.profile / 'config.yaml').read_bytes() == before)
finally:
    fixture.doCleanups()
