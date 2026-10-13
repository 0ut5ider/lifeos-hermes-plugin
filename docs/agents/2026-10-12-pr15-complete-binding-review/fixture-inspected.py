# ABOUTME: Checks qualification receipt binding and incomplete-gate refusal using isolated certificate fixtures.
# ABOUTME: Labels invented future gates and native identity as test data without creating release evidence.
import hashlib, json, os, shutil, subprocess, sys, tarfile, tempfile
from pathlib import Path
source=Path(__file__).resolve().parent
build=json.loads((source/'stable-bunfixed-build.json').read_bytes())
identity=build['head'][:8]
generator=Path(sys.argv[1]) if len(sys.argv)>1 else source/'certify_release.py'
with tarfile.open(build['archive']) as archive:
    manifest_bytes=archive.extractfile('hermes/hermes-source-manifest.json').read()
manifest=json.loads(manifest_bytes)
selected=['stable-bunfixed-build.json','frontend-build.json',
'integration-sealed-'+identity+'.json','integration-sealed-'+identity+'.stderr',
'native-sealed-'+identity+'.json','native-sealed-'+identity+'.stdout','native-sealed-'+identity+'.stderr',
'fresh-install-'+identity+'-bunfixed.json','development-bunfixed-update.json',
'development-bunfixed-interruption-recovery.json','development-bunfixed-boot.json','development-preparation-bunfixed-interruption.json']
cases=[('baseline',None,None),('stale-integration','integration','package_commit'),
('wrong-fresh-digest','fresh','package_sha256'),('wrong-fresh-commit','fresh','commit'),
('wrong-fresh-version','fresh','version'),('wrong-native-commit','native','package_commit'),
('wrong-native-archive','native','archive_sha256'),('wrong-native-manifest','native','source_manifest_sha256'),
('wrong-native-tree','native','source_tree_sha256'),('wrong-native-runtime','native','bun_version'),
('wrong-native-binary','native','bun_binary_sha256'),('changed-native-source','native','archived_source_files_unchanged'),('wrong-rollback-operation','rollback','operation'),('wrong-interrupted-operation','interrupted','operation'),('wrong-interrupted-commit','interrupted-preparation','commit'),
('wrong-interrupted-archive','interrupted-preparation','package_sha256'),('wrong-interrupted-version','interrupted-preparation','version'),
('wrong-boot-operation','boot','operation'),('wrong-boot-commit','boot','commit'),('wrong-boot-archive','boot','package_sha256'),
('wrong-coverage-count','coverage','program_targets'),('incomplete-gates',None,None)]
results=[]
for name,receipt,key in cases:
    with tempfile.TemporaryDirectory(prefix='release-certificate-binding-') as directory:
        root=Path(directory)
        shutil.copy2(generator,root/'certify_release.py')
        for file in selected:shutil.copy2(source/file,root/file)
        # All following added metadata is explicitly synthetic test data, never qualification evidence.
        path=root/('native-sealed-'+identity+'.json')
        native=json.loads(path.read_bytes())
        native.update(package_commit=build['head'],archive_sha256=build['archive_sha256'],
            source_manifest_sha256=hashlib.sha256(manifest_bytes).hexdigest(),source_tree_sha256=manifest['tree_sha256'],
            archived_source_files_unchanged=True,bun_version='1.4.3',
            bun_binary_sha256='7ce7d6b654eddeec20afddf2396317fba6dc19ab52788a27e894e1806bf8f24b',synthetic_probe_only=True)
        path.write_text(json.dumps(native))
        update=json.loads((source/'development-bunfixed-update.json').read_bytes())
        path=root/'development-bunfixed-boot.json';boot=json.loads(path.read_bytes())
        boot.update(operation=update['operation'],active_identity=update['active_identity'],synthetic_probe_only=True)
        path.write_text(json.dumps(boot))
        if name!='incomplete-gates':
            rollback=json.loads((source/'development-bunfixed-interruption-recovery.json').read_bytes())
            rollback['synthetic_probe_only']=True
            rollback['operation']=json.loads((source/'development-bunfixed-update.json').read_bytes())['operation']
            (root/'development-bunfixed-rollback.json').write_text(json.dumps(rollback))
            (root/'whole-guest-recovery.json').write_text(json.dumps({'status':'PASS','network_disconnected':True,
                'application_services_masked':True,'cases':[{'case':c,'status':'PASS'} for c in ('baseline','interrupted','later-edit')],
                'synthetic_probe_only':True}))
            (root/'whole-guest-program-coverage.json').write_text(json.dumps({'status':'PASS',
                'program_commit':build['head'],'archive_sha256':build['archive_sha256'],'program_targets':143,'synthetic_probe_only':True}))
        if receipt:
            file={'integration':'integration-sealed-'+identity+'.json','native':'native-sealed-'+identity+'.json',
                'fresh':'fresh-install-'+identity+'-bunfixed.json','rollback':'development-bunfixed-rollback.json','interrupted':'development-bunfixed-interruption-recovery.json',
                'interrupted-preparation':'development-preparation-bunfixed-interruption.json','boot':'development-bunfixed-boot.json',
                'coverage':'whole-guest-program-coverage.json'}[receipt]
            path=root/file;value=json.loads(path.read_bytes())
            target=value['preparation'] if receipt in {'fresh','interrupted-preparation'} else (value['active_identity'] if receipt=='boot' and key!='operation' else value)
            target[key]=142 if key=='program_targets' else False if key=='archived_source_files_unchanged' else ('0'*40 if 'commit' in key else '0'*64)
            path.write_text(json.dumps(value))
        process=subprocess.run([sys.executable,'-B',str(root/'certify_release.py')],
            env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),capture_output=True,text=True)
        accepted=process.returncode==0 and (root/'RELEASE-CERTIFICATE.json').exists()
        results.append({'case':name,'accepted':accepted,'expected_acceptance':name=='baseline',
            'exit_code':process.returncode,'synthetic_probe_only':True})
print(json.dumps(results,indent=2))
assert all(row['accepted']==row['expected_acceptance'] for row in results), 'Certificate accepts mismatched qualification evidence'
