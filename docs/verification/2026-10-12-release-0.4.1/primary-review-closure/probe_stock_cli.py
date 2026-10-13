# ABOUTME: Verifies public commit installation and exact-version dispatch through actual stock Hermes.
# ABOUTME: Uses invalid release selections in a synthetic profile so preparation never downloads a release.
import json,os,shutil,subprocess,sys,tempfile,time
from pathlib import Path
cache=Path('/home/outsider/.cache/lifeos-hermes-managed-20261012');out=Path(__file__).parent
commit='223cbfc1681f0b4d3a7bad668d40822a9267137e'
results=[]
with tempfile.TemporaryDirectory(prefix='pr16-stock-') as temp:
 root=Path(temp);home=root/'home';home.mkdir(mode=0o700);profile=home/'.hermes';profile.mkdir(mode=0o700)
 (profile/'config.yaml').write_text('model:\n  default: synthetic-model\n');(profile/'config.yaml').chmod(0o600)
 original=(profile/'config.yaml').read_bytes()
 host=root/'stock-hermes';shutil.copytree(cache/'upstream',host,ignore=shutil.ignore_patterns('__pycache__','*.pyc','.bytecode-fingerprint','.hermes'))
 env={key:value for key,value in os.environ.items() if key in ('PATH','LANG','LC_ALL','SSL_CERT_FILE','SSL_CERT_DIR')}
 env.update(HOME=str(home),HERMES_HOME=str(profile),TZ='UTC',PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=str(host))
 command=[sys.executable,'-B','-m','hermes_cli.main']
 def run(args,label,input=None):
  started=time.monotonic();r=subprocess.run(command+args,cwd=host,env=env,input=input,capture_output=True,text=True,timeout=600)
  (out/(label+'.stdout')).write_text(r.stdout);(out/(label+'.stderr')).write_text(r.stderr)
  result={'case':label,'command':args,'exit_code':r.returncode,'elapsed_seconds':time.monotonic()-started}
  results.append(result);return r
 installed=run(['plugins','install','https://github.com/0ut5ider/lifeos-hermes-plugin.git#optional/lifeos_release_manager','--ref',commit],'public-commit-install',input='y\n')
 assert installed.returncode==0,installed.stderr
 enabled=run(['plugins','enable','lifeos-release-manager'],'plugin-enable');assert enabled.returncode==0
 status=run(['lifeos-release','status'],'plugin-status');assert status.returncode==0 and json.loads(status.stdout)=={'operations':[]}
 for args,label in [(['lifeos-release','prepare','--version','not-a-version'],'separated-invalid-exact'),(['lifeos-release','prepare','--version=not-a-version'],'equals-invalid-exact')]:
  r=run(args,label);report=json.loads(r.stdout)
  assert r.returncode==1 and report['status']=='rejected' and report['message']=='The complete release operation is unavailable under this profile. Check its safe status and private preparation logs.'
  assert 'Hermes Agent v' not in r.stdout
 version=run(['--version'],'hermes-global-version');assert version.returncode==0 and 'Hermes Agent v0.21.7' in version.stdout
 script='import json,sys;sys.argv=["hermes",*json.loads(sys.argv[1])];from hermes_cli.main import _build_cli_parser,_parse_cli_args;p,s=_build_cli_parser();a=_parse_cli_args(p,s,sys.argv[1:]);print(json.dumps({"global_version":a.version,"release_version":getattr(a,"release_version",None),"action":getattr(a,"action",None)}))'
 for args,label,wanted in [(['lifeos-release','prepare'],'default-selection-namespace',None),(['lifeos-release','prepare','--version','0.4.0'],'separated-exact-namespace','0.4.0'),(['lifeos-release','prepare','--version=0.4.0'],'equals-exact-namespace','0.4.0')]:
  r=subprocess.run([sys.executable,'-B','-c',script,json.dumps(args)],cwd=host,env=env,capture_output=True,text=True,timeout=60)
  (out/(label+'.stdout')).write_text(r.stdout);(out/(label+'.stderr')).write_text(r.stderr)
  assert r.returncode==0 and json.loads(r.stdout)=={'global_version':False,'release_version':wanted,'action':'prepare'}
  results.append({'case':label,'arguments':args,'exit_code':r.returncode,'namespace':json.loads(r.stdout)})
 assert not (home/'.claude').exists()
 assert all(json.loads((p/'status.json').read_bytes())['state']=='preparation_failed' for p in (profile/'.lifeos-releases').iterdir())
 results.append({'case':'active-installation-preserved','native_installation_absent':True,'operations_safely_refused':True})
(out/'stock-cli-results.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps(results,indent=2))
