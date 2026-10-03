# ABOUTME: Reproduces update and restore data-preservation gaps with real temporary directories.
# ABOUTME: Uses the repository update test fixture and synthetic data only.
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path[:0] = ['.', 'tests']
from lifeos_hook_bridge import update_transaction
from lifeos_hook_bridge.update_transaction import apply_update, restore_update, validate_restore
from test_update_transaction import UpdateTransactionTests

fixture = UpdateTransactionTests()
results = {}

# R1: a native or dashboard writer that keeps running while only the gateway is stopped.
with tempfile.TemporaryDirectory() as directory:
    installed, hermes, prior, selected, reference, baseline, snapshot = fixture.fixture(Path(directory))
    events, stop, start, mount, renew, verify = fixture.callbacks(hermes, baseline)
    real_sync = update_transaction.sync_dependencies

    def sync_with_concurrent_write(staged, *args):
        # The copy of installed into staged has finished. A running writer appends a fact.
        (installed / 'LIFEOS/MEMORY/later-fact.txt').write_text('synthetic fact written during update')
        return real_sync(staged, *args)

    update_transaction.sync_dependencies = sync_with_concurrent_write
    try:
        result = apply_update(installed, hermes, prior, selected, reference, baseline, snapshot,
                              stop=stop, start=start, mount=mount, renew=renew, verify=verify)
    finally:
        update_transaction.sync_dependencies = real_sync
    results['R1_concurrent_write'] = {
        'update_state': result['state'],
        'fact_in_installed': (installed / 'LIFEOS/MEMORY/later-fact.txt').exists(),
        'fact_only_in_snapshot_live_prior': (snapshot / 'live-prior/LIFEOS/MEMORY/later-fact.txt').exists(),
        'restore_guard_baseline_includes_loss': 'LIFEOS/MEMORY/later-fact.txt' in result['user_data'],
    }

# R2: browser restore after a later Hermes profile edit.
with tempfile.TemporaryDirectory() as directory:
    installed, hermes, prior, selected, reference, baseline, snapshot = fixture.fixture(Path(directory))
    events, stop, start, mount, renew, verify = fixture.callbacks(hermes, baseline)
    apply_update(installed, hermes, prior, selected, reference, baseline, snapshot,
                 stop=stop, start=start, mount=mount, renew=renew, verify=verify)
    (hermes / 'config.yaml').write_text('owner edit after update: model choice')
    (hermes / '.env').write_text('SYNTHETIC_PROVIDER_KEY=placeholder-added-after-update\n')
    (hermes / '.env').chmod(0o600)
    guard = 'passed'
    try:
        validate_restore(snapshot, installed=installed)
    except Exception as error:
        guard = f'refused: {error}'
    restore_update(snapshot, stop=stop, start=start, verify=lambda: None)
    archived = [str(path.relative_to(snapshot)) for path in snapshot.rglob('*')
                if path.is_file() and path.read_bytes() in (b'owner edit after update: model choice',
                                                            b'SYNTHETIC_PROVIDER_KEY=placeholder-added-after-update\n')]
    results['R2_restore_profile_edit'] = {
        'route_guard': guard,
        'config_after_restore': (hermes / 'config.yaml').read_text(),
        'env_exists_after_restore': (hermes / '.env').exists(),
        'later_edit_copies_retained_anywhere_in_snapshot': archived,
    }

print(json.dumps(results, indent=2))
