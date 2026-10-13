# ABOUTME: Verifies published release installation through stock Hermes plugin and release commands.
# ABOUTME: Keeps the profile synthetic and records exact public asset identity without changing either server.
import gzip, hashlib, json, os, subprocess, sys, tempfile, time
from pathlib import Path
out=Path(__file__).resolve().parent
cache=Path('/home/outsider/.cache/lifeos-hermes-managed-20261012')
build=json.loads((out/'stable-bunfixed-build.json').read_bytes())
publication=json.loads((out/'publication.json').read_bytes())
assert publication['tag']=='v'+build['version'] and publication['program_commit']==build['head']
base=Path(tempfile.mkdtemp(prefix='public-040-',dir=cache))
profile=base/'.hermes';profile.mkdir(mode=0o700)
(base/'.local/bin').mkdir(parents=True,mode=0o700)
(profile/'config.yaml').write_text('model:\n  default: synthetic-model\n');(profile/'config.yaml').chmod(0o600)
environment=dict(os.environ,HOME=str(base),HERMES_HOME=str(profile),TZ='UTC',
    PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=str(cache/'upstream'),
    PATH=str(base/'.local/bin')+':'+os.environ['PATH'])
python=cache/'native-test-environment/bin/python'
command=[str(python),'-B','-m','hermes_cli.main']
report={'version':build['version'],'program_commit':build['head'],'archive_sha256':build['archive_sha256'],
    'synthetic_profile':True,'live_servers_changed':False,'profile':str(profile),
    'version_selection':'latest_stable' if '--latest' in sys.argv[1:] else 'explicit'}
started=time.monotonic()
def run(arguments,label,*,installed=False,input=None,timeout=600):
    process=subprocess.run(([str(base/'.local/bin/hermes')] if installed else command)+arguments,
        env=environment if not installed else dict(environment,PYTHONPATH=''),input=input,
        capture_output=True,text=True,timeout=timeout)
    with gzip.open(out/('public-'+label+'.stdout.gz'),'wt') as stream:stream.write(process.stdout)
    (out/('public-'+label+'.stderr')).write_text(process.stderr)
    assert process.returncode==0,label+' refuses; read saved output'
    return process.stdout
try:
    run(['plugins','install','https://github.com/0ut5ider/lifeos-hermes-plugin.git#optional/lifeos_release_manager',
        '--ref',publication['tag_commit']],'stock-plugin-install',input='y\n')
    run(['plugins','enable','lifeos-release-manager'],'stock-plugin-enable')
    assert json.loads(run(['lifeos-release','status'],'stock-manager-status'))=={'operations':[]}
    report['stock_public_plugin_install']='PASS'
    version_arguments=[] if '--latest' in sys.argv[1:] else ['--version',build['version']]
    prepared=json.loads(run(['lifeos-release','prepare',*version_arguments,
        '--name','SyntheticAdrian','--assistant','SyntheticCerebo'],'release-prepare',timeout=1800))
    assert prepared['state']=='ready' and prepared['active_unchanged'] is True
    assert prepared['commit']==build['head'] and prepared['package_sha256']==build['archive_sha256']
    report['public_preparation']=prepared
    job=profile/'.lifeos-releases'/prepared['identifier']
    certificate=json.loads((job/'download/RELEASE-CERTIFICATE.json').read_bytes())
    assert certificate['production_qualified'] is True and not certificate.get('test_fixture_only')
    assert hashlib.sha256((job/'download/RELEASE-CERTIFICATE.json').read_bytes()).hexdigest()==hashlib.sha256((out/'RELEASE-CERTIFICATE.json').read_bytes()).hexdigest()
    report['published_certificate_identity']='PASS'
    run(['lifeos-release','start',prepared['identifier']],'release-start')
    deadline=time.monotonic()+300
    while time.monotonic()<deadline:
        state=json.loads((job/'status.json').read_bytes())['state']
        if state in {'applied','recovery_required','rejected','rolled_back'}:break
        time.sleep(.5)
    assert state=='applied','Published worker does not apply'
    version=json.loads(run(['lifeos-version'],'installed-version',installed=True))['active']
    assert version['version']==build['version'] and version['commit']==build['head']
    assert version['package_sha256']==build['archive_sha256'] and version['verification']=='verified'
    report['public_worker_install']='PASS';report['installed_identity']=version;report['status']='PASS'
except BaseException as error:
    report.update(status='FAIL',failure_type=type(error).__name__,failure=str(error));raise
finally:
    report['elapsed_seconds']=time.monotonic()-started
    (out/'public-install-verification.json').write_text(json.dumps(report,indent=2)+'\n')
    (out/'public-install-verification.done').write_text('0\n' if report.get('status')=='PASS' else '1\n')
