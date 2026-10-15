# ABOUTME: Checks local final publication metadata against the approved deployment bytes.
# ABOUTME: Verifies preserved asset records and lossless compression without remote requests.
import gzip,hashlib,json,subprocess
from pathlib import Path
root=Path(__file__).resolve().parents[3];r=Path(__file__).resolve().parent
v=root/'docs/verification/2026-10-14-release-0.5.0';prior=root/'docs/agents/2026-10-15-pr28-deployment-review'
def load(path):return json.loads(path.read_bytes())
def sha(data):return hashlib.sha256(data).hexdigest()
publication=load(v/'deployment-acceptance-publication.json')
before=load(prior/'assets-before-deployment-acceptance.json')['assets'];after=load(v/'assets-after-deployment-acceptance.json')['assets']
assert isinstance(before,list) and isinstance(after,list)
key=lambda row:(row['tag'],row['id'])
old={key(row):row for row in before};new={key(row):row for row in after}
assert len(old)==len(before)==55 and len(new)==len(after)==56
assert all(new[k]==row for k,row in old.items())
added=[row for k,row in new.items() if k not in old];assert added==[publication['new_asset']]
asset=added[0];candidate=(v/'DEPLOYMENT-ACCEPTANCE.json').read_bytes()
assert asset['id']==642573776 and asset['name']=='DEPLOYMENT-ACCEPTANCE.json' and asset['tag']=='v0.5.0'
assert asset['size']==len(candidate)==3957
assert sha(candidate)=='0d6a52ae5a88f0e3874db09ccd13050fa9b0180c626112c136eb58f93f3d1478'
assert asset['digest']=='sha256:'+sha(candidate) and publication['reviewed_candidate_sha256']==sha(candidate)
assert asset['updated_at']=='2026-10-15T03:46:58Z'
assert publication['status']=='PASS' and publication['prior_immutable_assets_verified']==55
assert publication['existing_assets_replaced'] is False and publication['initial_certificate_unchanged'] is True and publication['public_installation_asset_unchanged'] is True
snapshot=load(prior/'reviewed-snapshot.json')
for name,digest in snapshot['current_source_and_input_sha256'].items():assert sha((v/name).read_bytes())==digest,name
compressed=prior/'initial-documentation.diff.gz';original=gzip.decompress(compressed.read_bytes())
expected=(prior/'initial-documentation.diff.sha256').read_text().split()[0]
assert sha(original)==expected
oldpath=str((prior/'initial-documentation.diff').relative_to(root))
previous=subprocess.check_output(['git','show','23c6830b75bb0b73e97b446fd703f754088a9150:'+oldpath],cwd=root)
assert previous==original
assert 'initial-documentation.diff.gz' in (prior/'pr28-deployment-review.md').read_text()
progress=load(v/'PROGRESS.json');assert progress['status']=='DEPLOYMENT_COMPLETE'
assert progress['original_0700_wall_clock_observed'] is False and progress['deployment_acceptance_sha256']==sha(candidate)
assert progress['prior_immutable_assets_preserved']==55 and progress['initial_certificate_unchanged'] is True
cleanup=load(v/'native-post-cleanup-verification.json');earlier=load(v/'release-test-cleanup.json')
assert cleanup['status']=='PASS' and cleanup['protected_archive']==earlier['protected_archive_preserved']
assert cleanup['native_pruning_protection_verified'] is True and cleanup['owned_guests_absent']==[110,111,112,113]
assert cleanup['owned_storage_registration_absent'] is True and cleanup['owned_storage_directory_absent'] is True
assert cleanup['preserved_guests']==earlier['other_guests_preserved']
resources=load(v/'operator-local-resource-cleanup.json')
assert resources['status']=='PASS' and resources['user_browser_profiles_changed'] is False
assert resources['all_owned_login_bridges_stopped_verified'] is True and resources['all_owned_dashboard_tunnels_closed_verified'] is True
assert len(resources['resources'])==5
check=subprocess.run(['git','diff','origin/main','--check'],cwd=root,capture_output=True,text=True)
(r/'whitespace-check.stdout').write_text(check.stdout);(r/'whitespace-check.stderr').write_text(check.stderr)
assert check.returncode==0
report={'status':'PASS','head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),'prior_asset_records_exactly_unchanged':55,'asset_records_after':56,'only_new_asset':asset,'candidate_sha256':sha(candidate),'reviewed_source_and_inputs_unchanged':True,'compressed_diff_sha256':sha(original),'compressed_diff_equals_precompression_git_bytes':True,'native_cleanup_receipt_consistent':True,'progress_consistent':True,'whitespace_check':'PASS','remote_calls':False,'publication_reexecuted':False}
(r/'publication-metadata-checks.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
