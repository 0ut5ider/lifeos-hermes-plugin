# ABOUTME: Certifies immutable release artifacts against completed local and installed checks.
# ABOUTME: Preserves deferred daily VM and Discord gates rather than marking them complete.
from pathlib import Path
import hashlib
import json
import re
import sys

here=Path(__file__).resolve().parent
root=here.parents[2]
load=lambda name:json.loads((here/name).read_text())
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
build=load('candidate-build.json')
assert build['status']=='PASS'
package=Path(build['package'])
combined=load('combined-final.json')
identity={}
differences=[]
for relative,expected in combined['source_hashes'].items():
    actual=digest(package/relative)
    identity[relative]={'tested_sha256':expected,'packaged_sha256':actual}
    if actual!=expected:differences.append(relative)
assert differences==[],differences
assert 'test_fresh_store' not in combined['command']
fresh=load('fresh-final.json')
assert fresh['source_hashes']['lifeos_hook_bridge/fresh_store.py']==digest(package/'lifeos_hook_bridge/fresh_store.py')
native=Path('/home/outsider/.cache/lifeos-atlas-20261010/native-limits-refresh/LifeOS/install')
native_hashes={}
for path in (package/'lifeos/LifeOS/install').rglob('*'):
    relative=path.relative_to(package/'lifeos/LifeOS/install')
    if not path.is_file() or '.git' in relative.parts:continue
    expected=digest(path)
    assert digest(native/relative)==expected,str(relative)
    native_hashes[str(relative)]=expected
main=Path('/home/outsider/.cache/lifeos-atlas-20261010/daily-text-0.2.0-531f8616/hermes')
hermes_hashes={}
for name,expected in load('installed-runtime.json')['hermes_source_files'].items():
    relative=Path(name)
    assert digest(package/'hermes'/relative)==expected,str(relative)
    assert digest(main/relative)==expected,str(relative)
    hermes_hashes[str(relative)]=expected
(here/'regression-source-identity.json').write_text(json.dumps({'plugin':identity,
 'separately_tested_fresh_store':differences,'native_fixture_files':native_hashes,
 'hermes_fixture_files':hermes_hashes},indent=2)+'\n')
if '--identity-only' in sys.argv:
    print(json.dumps({'plugin_files':len(identity),'native_fixture_files':len(native_hashes),
                      'hermes_fixture_files':len(hermes_hashes),'separate_fresh_store':differences}))
    sys.exit(0)
counts={}
for label in ('combined-final','fresh-final','channel-controls'):
    record=load(label+'.json')
    assert record['exit_code']==0, label
    count=re.search(r'Ran (\d+) tests',record['stderr'])
    assert count and 'skipped=' not in record['stderr'] and 'FAILED' not in record['stderr'],label
    counts[label]=int(count[1])
native_record=load('native-controls.json')
assert native_record['exit_code']==0
counts['native-controls']=0
for command in native_record['commands']:
    assert command['exit_code']==0 and not command['stderr']
    count=re.search(r'(\d+) passed',command['stdout'])
    assert count and 'skipped' not in command['stdout'] and 'warnings summary' not in command['stdout']
    counts['native-controls']+=int(count[1])
installed=load('installed-sequence.json')
assert installed['status']=='PASS' and len(installed['commands'])==12
assert all(item['exit_code']==0 for item in installed['commands'])
runtime=load('installed-runtime.json')
assert runtime['status']=='PASS' and runtime['head']==build['head']
assert runtime['plugin_files']==combined['source_hashes']
for name in ('fresh','cancellation','applications','owner-turn','atlas','schedule',
             'active-stop','profile-recovery','rollback','optional'):
    record=load('installed-'+name+'.json')
    assert record['status']=='PASS',name
    if 'head' in record:assert record['head']==build['head'],name
browser=load('browser-pages.json')
assert browser['status']=='PASS' and browser['code_head']==build['head']
assert len(browser['pulsePages'])==13
assert load('live-before.json')==load('live-after.json')
archive=Path(build['archive'])
assert digest(archive)==build['archive_sha256']
dashboard=Path('/home/outsider/.cache/lifeos-atlas-20261010/daily-text-release-11577ed4/hermes-dashboard.tgz')
assert digest(dashboard)=='078d6da534408339fefcb3893431835ccfc7ce9483cc85a46ebf6b917e8cb2ee'
report={'status':'ACCEPTANCE_PASS_MERGE_PENDING','date':'2026-10-10','version':build['version'],
 'base_main':'531f86169550ae118b1624a9cffe809211d7a3bf','code_head':build['head'],
 'archives':{'programs':{'path':str(archive),'bytes':archive.stat().st_size,'sha256':digest(archive)},
             'hermes_dashboard':{'path':str(dashboard),'bytes':dashboard.stat().st_size,'sha256':digest(dashboard)}},
 'hermes_base':build['hermes_base'],'lifeos_base':build['lifeos_base'],
 'patches':{'hermes':build['hermes_patch_count'],'lifeos':build['lifeos_patch_count']},
 'local_test_counts':counts,'installed_commands':installed['commands'],
 'test_fixture_header_head':combined['package_manifest']['head'],
 'tested_plugin_files_equal_final_package':len(identity),
 'hermes_runtime_program_files':len(hermes_hashes),
 'installed_native_program_files':len(runtime['native_program_files']),
 'pulse_frontend_included_in_program_archive':True,
 'live_profile_unchanged':True,'model_routes_unchanged':True,
 'scope':'Isolated .252 acceptance profile, synthetic data, actual native services and private model.',
 'remaining_gates':['Merge fresh-default and job-admission fixes and certify equivalent merged program bytes.',
                    'Create the separate daily VM and prepare fresh Adrian and Cerebo data.',
                    'Complete coherent off-server whole-guest backup and restore, including external Atlas.',
                    'Create and verify the private Discord channel on the daily VM.',
                    'Complete actual Discord delivery, bot cutover, and lasting-memory activation.'],
 'deferred':['Voice and media processing','Import and reverse migration',
             'Complete installation and updates from Hermes','Governed Pulse core-file editor'],
 'known_limits':browser['knownLimits'],
 'recovery_scope':'Local profile reconstruction and retained-version rollback. Off-server whole-guest restore remains required.'}
(here/'DAILY-RELEASE.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'status':report['status'],'local_test_counts':counts},indent=2))
