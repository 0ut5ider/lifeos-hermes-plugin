# ABOUTME: Exercises current admission, native skill, and later-owner-remount gates from the actual certifier.
# ABOUTME: Mutates safe local receipt copies without creating a certificate or guest completion evidence.
import ast,copy,json
from pathlib import Path

project=Path(__file__).resolve().parents[3]
root=project/'docs/agents/2026-10-14-pr27-current-certificate-closure/certificate-inputs/docs/verification/2026-10-14-release-0.5.0'
nodes=ast.parse((root/'certify_release.py').read_text()).body
def assigned(node,name):return isinstance(node,ast.Assign) and any(isinstance(target,ast.Name) and target.id==name for target in node.targets)
start=next(index for index,node in enumerate(nodes) if assigned(node,'admitted'))
stop=next(index for index,node in enumerate(nodes) if assigned(node,'certificate'))
validation=compile(ast.Module(body=nodes[start:stop],type_ignores=[]),'<actual-current-evidence-gates>','exec')
passed=next(node for node in nodes if isinstance(node,ast.FunctionDef) and node.name=='passed')
receipt_names=['development-post-admission-verification.json','development-native-skill-review.json','development-post-remount-restore-availability.json']
receipts={name:json.loads((root/name).read_bytes()) for name in receipt_names}
development=json.loads((root/'development-verification.json').read_bytes())
cases=[('actual-completed-inputs',None,lambda r:None,True),
 ('current-personal-records-read',receipt_names[0],lambda r:r.update(personal_records_read=True),False),
 ('current-memory-config-lost',receipt_names[0],lambda r:r.update(memory_configuration_bytes_preserved=False),False),
 ('current-gateway-not-restarted',receipt_names[0],lambda r:r.update(gateway_restarted_after_remount=False),False),
 ('skills-wrong-operation',receipt_names[1],lambda r:r.update(operation='0'*32),False),
 ('skills-wrong-archive',receipt_names[1],lambda r:r.update(archive_sha256='0'*64),False),
 ('skills-native-bytes-changed',receipt_names[1],lambda r:r.update(native_skill_bytes_changed=True),False),
 ('skills-still-omitted',receipt_names[1],lambda r:r.update(after_omitted_program_skills=1),False),
 ('skills-launcher-absent',receipt_names[1],lambda r:r.update(launcher_present=False),False),
 ('skills-remount-not-committed',receipt_names[1],lambda r:r.update(actual_remount_state='failed'),False),
 ('skills-restart-unverified',receipt_names[1],lambda r:r.update(gateway_restart_verified=False),False),
 ('old-recover-available',receipt_names[2],lambda r:r.update(recover_available=True),False),
 ('old-operation-rolled-back',receipt_names[2],lambda r:r.update(state='rolled_back'),False),
 ('old-proof-not-historical',receipt_names[2],lambda r:r.update(old_release_bound_receipt_is_historical_checkpoint=False),False),
 ('old-operation-mismatch',receipt_names[2],lambda r:r.update(operation='0'*32),False),
 ('later-owner-journal-not-refused',receipt_names[2],lambda r:r.update(later_owner_remount_refused_by_old_restore=False),False)]
results=[]
for name,changed,mutate,expected in cases:
 inputs=copy.deepcopy(receipts)
 if changed:mutate(inputs[changed])
 namespace={'load':lambda name:inputs[name],'development':development,
    'commit':'04efe633296eb2b1a1d95561ca6d3e9516cd47dc',
    'archive_sha':'a6dd0e11b8fb1b5ae30345be20c955db02728839f7bc907f60a70944ad392813'}
 exec(compile(ast.Module(body=[passed],type_ignores=[]),'<actual-passed-receipt-helper>','exec'),namespace)
 accepted=True
 try:exec(validation,namespace)
 except (AssertionError,KeyError,TypeError,ValueError):accepted=False
 assert accepted==expected,name
 results.append({'case':name,'status':'PASS','accepted':accepted})
report={'status':'PASS','cases':len(results),'results':results,
 'actual_completed_safe_inputs_used':True,'guest_completion_receipt_constructed':False,
 'certificate_written':False,'remote_commands_run':False}
Path(__file__).with_name('current-evidence-guard-results.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
