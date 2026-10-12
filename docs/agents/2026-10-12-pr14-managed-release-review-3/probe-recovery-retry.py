# ABOUTME: Measures recovery eligibility after refusal of a missing retained native prior copy.
# ABOUTME: Uses a real governed Bun mount, public admission, and actual worker failure publication.
import json
from pathlib import Path
import shutil
from test_mount_transaction import MountTransactionTests, HOST
from optional.lifeos_release_manager.cli import read_private, write_state, status
from optional.lifeos_release_manager.release_operation import request_digest, seal_plan
from optional.lifeos_release_manager.release_programs import ProgramTransaction, publish
from optional.lifeos_release_manager import release_worker as worker
from lifeos_hook_bridge.lifeos_installation import publish as select_installation
fixture = MountTransactionTests()
fixture.setUp()
try:
    profile, root = fixture.profile, fixture.root
    job = profile / '.lifeos-releases' / ('a' * 32)
    job.mkdir(parents=True, mode=0o700)
    shutil.copytree(Path.cwd() / 'lifeos_hook_bridge', profile / 'plugins/lifeos-hook-bridge',
        ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    select_installation(profile, root.parent, root.parent / 'HermesWorkspace')
    request = {'identifier': job.name, 'profile': str(profile), 'installed': str(root),
        'account_home': str(Path.home()), 'version': '0.4.0-dev.1', 'commit': 'b' * 40,
        'package_sha256': 'c' * 64, 'runtime': {'source': str(HOST),
        'bun': fixture.fixture.fixture.memory.bun, 'hermes': str(fixture.hermes)}}
    publish(job / 'request.json', json.dumps(request).encode())
    write_state(job, 'ready')
    programs = ProgramTransaction(job / 'program-snapshot')
    source = job / 'candidate-config.yaml'
    publish(source, (profile / 'config.yaml').read_bytes())
    programs.prepare(directories={}, files={profile / 'config.yaml': source})
    programs.apply()
    plan = {'fresh': False, 'native_mount_required': True, 'services': None,
            'program_entries_sha256': programs.entries_digest()}
    seal_plan(job, request, plan)
    publish(profile / 'integration-release.json', json.dumps(request).encode())
    binding = {'job': str(job), 'request_digest': request_digest(request), 'action': 'apply'}
    publish(job / 'mount-intent.json', b'{"prior_journal_sha256":null,"action":"apply"}')
    grant = fixture.fixture.issue(binding=binding)
    fixture.addCleanup(fixture.fixture.admin().revoke, fixture.fixture.configuration, grant)
    environment = fixture.fixture.admin().mount_environment(root, profile, grant, binding=binding)
    from lifeos_hook_bridge.memory_service import MemoryService
    config, scope = fixture.fixture.admin().validate(fixture.fixture.configuration, grant)
    MemoryService(fixture.fixture.configuration)._prompt(config, scope, 'prompt_preview',
        {'home': str(profile), 'keepOutputFormat': False})
    transaction = fixture.transaction()
    transaction.execute(environment, fixture.fixture.fixture.memory.bun, str(fixture.hermes),
        binding=binding, retain_for_rollback=True)
    manifest = read_private(transaction.journal)
    entry = next(entry for entry in manifest['entries'] if entry['before'] is not None)
    previous = Path(manifest['snapshot']) / 'previous' / str(entry['copy'])
    original = previous.read_bytes()
    previous.unlink()
    write_state(job, 'recovery_required')
    recover_binding = {**binding, 'action': 'recover'}
    recover_grant = fixture.fixture.issue(binding=recover_binding)
    fixture.addCleanup(fixture.fixture.admin().revoke, fixture.fixture.configuration, recover_grant)
    worker.admit_operation(job, read_private(job / 'request.json'), 'recover', authorization=recover_grant)
    print('public recovery admitted with damaged retained copy:', read_private(job / 'status.json')['state'])
    before = (profile / 'config.yaml').read_bytes()
    try:
        worker.execute(job, 'recover')
    except Exception as error:
        print('actual worker refusal:', type(error).__name__, str(error))
    print('state after recover refusal:', read_private(job / 'status.json')['state'])
    print('profile preserved:', (profile / 'config.yaml').read_bytes() == before)
    publish(previous, original)
    print('retained copy restored, native preflight passes:', end=' ')
    worker.check_mount_recovery(job, request, transaction)
    print(True)
    print('safe status after repair:', status(profile, job.name))
    retry_grant = fixture.fixture.issue(binding=recover_binding)
    fixture.addCleanup(fixture.fixture.admin().revoke, fixture.fixture.configuration, retry_grant)
    try:
        worker.admit_operation(job, read_private(job / 'request.json'), 'recover', authorization=retry_grant)
        print('public recovery retry: admitted')
    except Exception as error:
        print('public recovery retry:', type(error).__name__, str(error))
finally:
    fixture.doCleanups()
