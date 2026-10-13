# ABOUTME: Prepares the default published stable release through the installed Hermes command.
# ABOUTME: Records exact public certificate identity without changing active programs or personal data.
import hashlib, json, os, subprocess
from pathlib import Path
os.umask(0o077)
home=Path.home();profile=home/'.hermes'
out=home/'releases/qualification-20261013-041-96f4f8fb'
report={'selection':'latest_stable','daily_server_changed':False}
try:
    environment=dict(os.environ,HOME=str(home),HERMES_HOME=str(profile),PYTHONPATH='',PYTHONDONTWRITEBYTECODE='1',TZ='UTC')
    environment['PATH']=str(home/'.local/bin')+':'+environment.get('PATH',os.defpath)
    result=subprocess.run([str(home/'.local/bin/hermes'),'lifeos-release','prepare'],cwd=profile,
        env=environment,capture_output=True,text=True,timeout=1800)
    (out/'public-preparation.stdout').write_text(result.stdout)
    (out/'public-preparation.stderr').write_text(result.stderr)
    assert result.returncode==0,'The public preparation command refuses; inspect private diagnostic output'
    prepared=json.loads(result.stdout)
    assert prepared['version']=='0.4.1' and prepared['commit']=='96f4f8fbef21f53ee704eb16f34698bc35b5dc77'
    assert prepared['package_sha256']=='462297fa0c20166ca77d0bf37fcef556b50832ff7bf46327d9777368ea80670e'
    assert prepared['state']=='ready' and prepared['active_unchanged'] is True
    certificate=profile/'.lifeos-releases'/prepared['identifier']/'download/RELEASE-CERTIFICATE.json'
    assert hashlib.sha256(certificate.read_bytes()).hexdigest()==(out/'public-certificate.sha256').read_text().strip()
    value=json.loads(certificate.read_bytes())
    assert value['production_qualified'] is True and not value.get('test_fixture_only')
    report.update(status='PASS',published_certificate_identity='PASS',preparation={k:prepared[k] for k in ('identifier','version','commit','package_sha256','state','active_unchanged')})
except BaseException as error:
    report.update(status='FAIL',failure_type=type(error).__name__,failure=str(error));raise
finally:
    (out/'public-preparation.json').write_text(json.dumps(report,indent=2)+'\n')
    (out/'public-preparation.done').write_text('0\n' if report.get('status')=='PASS' else '1\n')
