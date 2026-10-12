# ABOUTME: Exercises retained managed rollback across a later actual native mount.
# ABOUTME: Uses synthetic owner data, native Bun, and actual Hermes configuration checks.
import json
from pathlib import Path
from test_mount_transaction import MountTransactionTests
from optional.lifeos_release_manager.release_operation import request_digest
from optional.lifeos_release_manager.release_programs import publish
from optional.lifeos_release_manager.release_worker import _restore_mount

fixture = MountTransactionTests()
fixture.setUp()
try:
    transaction = fixture.transaction()
    job = fixture.profile / '.lifeos-releases' / ('a' * 32)
    job.mkdir(parents=True, mode=0o700)
    request = {'profile': str(fixture.profile), 'installed': str(fixture.root), 'identifier': job.name}
    binding = {'job': str(job), 'request_digest': request_digest(request), 'action': 'apply'}
    publish(job / 'mount-intent.json', json.dumps({'prior_journal_sha256': None, 'action': 'apply'}).encode())
    bound_grant = fixture.fixture.issue(binding=binding)
    fixture.addCleanup(fixture.fixture.admin().revoke, fixture.fixture.configuration, bound_grant)
    bound_environment = fixture.fixture.admin().mount_environment(fixture.root, fixture.profile, bound_grant, binding=binding)
    from lifeos_hook_bridge.memory_service import MemoryService
    config, scope = fixture.fixture.admin().validate(fixture.fixture.configuration, bound_grant)
    MemoryService(fixture.fixture.configuration)._prompt(config, scope, 'prompt_preview', {'home': str(fixture.profile), 'keepOutputFormat': False})
    first = transaction.execute(bound_environment, fixture.fixture.fixture.memory.bun,
                                str(fixture.hermes), binding=binding, retain_for_rollback=True)
    snapshot = Path(first['snapshot'])
    print('first state:', first['state'])
    print('first retained snapshot exists:', snapshot.exists())
    original = transaction.journal.read_bytes()
    # Same synthetic owner remounts unchanged programs. No later user edit occurs.
    second = transaction.execute(fixture.environment, fixture.fixture.fixture.memory.bun,
                                 str(fixture.hermes))
    print('second state:', second['state'])
    print('first retained snapshot exists after second mount:', snapshot.exists())
    print('journal still binds first managed operation:', transaction.journal.read_bytes() == original)
    try:
        _restore_mount(job, request, transaction)
    except Exception as error:
        print('managed rollback:', type(error).__name__ + ': ' + str(error))
finally:
    fixture.doCleanups()
