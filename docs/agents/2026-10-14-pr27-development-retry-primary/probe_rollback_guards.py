# ABOUTME: Checks the actual rollback verifier's baseline equality and before-fingerprint refusal guards.
# ABOUTME: Uses safe metadata and real temporary program files without guest operations or completion receipts.
import ast
import copy
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace

from optional.lifeos_release_manager import release_programs as programs

project=Path(__file__).resolve().parents[3]
source=project/'docs/verification/2026-10-14-release-0.5.0'
body=ast.parse((source/'verify_development_rollback.py').read_text()).body
baseline_assert=next(node for node in body if isinstance(node,ast.Assert) and ast.unparse(node.test)=='current == baseline')
snapshot_assert=next(node for node in body if isinstance(node,ast.Assert) and ast.unparse(node.test)=="snapshot['state'] == 'restored'")
loop=next(node for node in body if isinstance(node,ast.For))
results=[]
def execute(nodes,namespace):
    try:
        exec(compile(ast.Module(body=nodes,type_ignores=[]),'<actual-rollback-guards>','exec'),namespace)
    except (AssertionError,programs.ProgramConflict):
        return False
    return True

baseline=json.loads((source/'development-prepromotion-baseline.json').read_bytes())
mutations=[('unchanged-safe-baseline',lambda row:None,True),
 ('changed-prior-release',lambda row:row['prior_identity'].update(commit='0'*40),False),
 ('changed-model-selection',lambda row:row.update(model_selection_sha256='0'*64),False),
 ('changed-credential-digest',lambda row:row['configuration_file_sha256'].update({'.env':'0'*64}),False),
 ('changed-memory-configuration-digest',lambda row:row['configuration_file_sha256'].update({'lifeos-memory.json':'0'*64}),False),
 ('changed-service-home',lambda row:next(iter(row['services'].values())).update(home='/synthetic/other'),False),
 ('inactive-service',lambda row:next(iter(row['services'].values())).update(active=False),False)]
for name,mutation,expected in mutations:
    current=copy.deepcopy(baseline);mutation(current)
    accepted=execute([baseline_assert],{'baseline':baseline,'current':current})
    assert accepted==expected
    results.append({'case':name,'status':'PASS','accepted':accepted})
for state in ('restored','applied','applying'):
    accepted=execute([snapshot_assert],{'snapshot':{'state':state}})
    assert accepted==(state=='restored')
    results.append({'case':'snapshot-state-'+state,'status':'PASS','accepted':accepted})

for name in ('restored-file','changed-bytes','changed-mode','removed-file','replaced-by-symlink','unexpected-new-file','absent-prior-file','aliased-parent'):
    with tempfile.TemporaryDirectory(prefix='rollback-file-refusal-') as temporary:
        root=Path(temporary);target=root/'program.py';target.write_text('accepted synthetic program\n');target.chmod(0o600)
        before=programs.fingerprint(target)
        if name=='changed-bytes':target.write_text('later synthetic program edit\n')
        elif name=='changed-mode':target.chmod(0o700)
        elif name=='removed-file':target.unlink()
        elif name=='replaced-by-symlink':
            other=root/'other';other.write_text('accepted synthetic program\n');target.unlink();target.symlink_to(other)
        elif name=='unexpected-new-file':before=None
        elif name=='absent-prior-file':before=None;target.unlink()
        elif name=='aliased-parent':
            alias=root/'alias';alias.symlink_to(root,target_is_directory=True);target=alias/'program.py'
        accepted=execute([loop],{'snapshot':{'entries':[{'target':str(target),'allow_links':False,'before':before}]},'programs':programs})
        expected=name in {'restored-file','absent-prior-file'}
        assert accepted==expected,name
        results.append({'case':name,'status':'PASS','accepted':accepted})
report={'status':'PASS','cases':len(results),'results':results,
        'actual_native_fingerprint_function_used':True,'actual_rollback_guard_statements_used':True,
        'remote_commands_run':False,'completion_receipt_written':False,
        'limit':'Local guard and filesystem tests only. The actual guest restoration receipt remains separate evidence.'}
Path(__file__).with_name('rollback-guard-results.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
