# ABOUTME: Exercises mount snapshot cleanup with private synthetic journals.
# ABOUTME: Confirms pending recovery and unrecognized payloads remain untouched.
import json
from pathlib import Path
import tempfile
from lifeos_hook_bridge.mount_transaction import MountTransaction, _json

def run(case):
    with tempfile.TemporaryDirectory() as temp:
        home = Path(temp); installed = home / 'installed'; profile = home / 'profile'
        installed.mkdir(); profile.mkdir(mode=0o700)
        t = MountTransaction(installed,profile)
        t.state.mkdir(mode=0o700)
        snapshot = t.state / ('a'*32); snapshot.mkdir(mode=0o700)
        (snapshot/'payload').write_text('Synthetic old credential copy')
        _json(snapshot/'identity.json',t._snapshot_identity())
        manifest = {'version':1,'profile':str(profile),'installed':str(installed),'baseline':None,
                    'state':'committed','snapshot':str(snapshot),'workspace':str(home/'workspace'),
                    'absent_directories':[], 'entries':[{'target':str(profile/'config.yaml'),'before':None,
                    'after':{'digest':'0'*64,'mode':0o600},'copy':0}]}
        expected = 'removed'
        if case.startswith('pending_'):
            manifest['state'] = case.split('_',1)[1]; expected='kept'
        if case == 'orphan': pass
        elif case == 'foreign_identity':
            identity=t._snapshot_identity(); identity['installed']=str(home/'foreign')
            _json(snapshot/'identity.json',identity); expected='kept'
        elif case == 'missing_identity':
            (snapshot/'identity.json').unlink(); expected='kept'
        elif case == 'identity_symlink':
            (snapshot/'identity.json').unlink(); target=home/'keep'; target.write_text('Synthetic Keep')
            (snapshot/'identity.json').symlink_to(target); expected='kept'
        elif case == 'nested_symlink':
            outside=home/'outside'; outside.mkdir(); (outside/'keep').write_text('Synthetic Keep')
            (snapshot/'link').symlink_to(outside)
        elif case == 'malformed_journal':
            _json(t.journal,{'state':'applying'}); expected='error_keep'
        elif case == 'missing_pending_snapshot':
            manifest['state']='applying'; import shutil; shutil.rmtree(snapshot)
            _json(t.journal,manifest); expected='error_missing'
        elif case == 'missing_terminal_snapshot':
            import shutil; shutil.rmtree(snapshot); _json(t.journal,manifest)
        elif case == 'historical_terminal':
            (snapshot/'identity.json').unlink(); _json(t.journal,manifest)
        else:
            _json(t.journal,manifest)
        try:
            status=t.status(); error=None
        except Exception as exc:
            status=None; error=str(exc)
        exists=snapshot.exists()
        print(json.dumps({'case':case,'status':status,'snapshot_exists':exists,'error':error},sort_keys=True))
        if expected=='removed': assert not error and not exists
        elif expected=='kept': assert not error and exists
        elif expected=='error_keep': assert error and exists
        else: assert error and not exists
        if case=='nested_symlink': assert (outside/'keep').read_text()=='Synthetic Keep'
        if case=='identity_symlink': assert target.read_text()=='Synthetic Keep'
for case in ('terminal','pending_prepared','pending_applying','pending_restoring','orphan','foreign_identity',
             'missing_identity','identity_symlink','nested_symlink','malformed_journal','missing_pending_snapshot',
             'missing_terminal_snapshot','historical_terminal'):
    run(case)
