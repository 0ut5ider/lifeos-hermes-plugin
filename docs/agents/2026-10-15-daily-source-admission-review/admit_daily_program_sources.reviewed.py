# ABOUTME: Reviews only exact public package skills and constitution through the authenticated daily owner API.
# ABOUTME: Verifies installation-bound content digests and full prompt admission without exporting personal sources.
import hashlib,json,os,re,tarfile,time
from pathlib import Path
import httpx

os.umask(0o077)
home=Path('/home/lifeos-hermes');profile=home/'.hermes';stage=home/'releases/qualification-0.5.0'
verified=json.loads((stage/'daily-verification.json').read_bytes())
assert verified['status']=='PASS' and verified['server']=='daily'
identifier=verified['operation'];assert re.fullmatch('[0-9a-f]{32}',identifier)
job=profile/'.lifeos-releases'/identifier;request=json.loads((job/'request.json').read_bytes())
assert request['version']=='0.5.0' and request['commit']=='04efe633296eb2b1a1d95561ca6d3e9516cd47dc'
assert request['package_sha256']=='a6dd0e11b8fb1b5ae30345be20c955db02728839f7bc907f60a70944ad392813'
assert json.loads((job/'status.json').read_bytes())['state']=='applied'
archive=job/'download/0.5.0-04efe633.tgz'
assert hashlib.sha256(archive.read_bytes()).hexdigest()==request['package_sha256']
configuration=json.loads((profile/'lifeos-memory.json').read_bytes())
contents={};prefix='lifeos/LifeOS/install/'
with tarfile.open(archive) as stream:
 for member in stream.getmembers():
  relative=member.name.removeprefix(prefix)
  if member.name.startswith(prefix) and (re.fullmatch(r'skills/[^/.][^/]*/SKILL\.md',relative)
    or relative=='LIFEOS/LIFEOS_SYSTEM_PROMPT.md'):
   assert member.isfile() and relative not in contents
   contents[relative]=stream.extractfile(member).read().decode()
assert len(contents)==57 and sum(p.startswith('skills/') for p in contents)==56
expected={p:hashlib.sha256(json.dumps({'root':configuration['root'],'principal':configuration['principal'],
 'path':p,'content':c},sort_keys=True,ensure_ascii=False).encode()).hexdigest() for p,c in contents.items()}
credentials=json.loads((home/'install-input/dashboard-access.json').read_bytes())
report_path=stage/'daily-native-skill-review.json';assert not report_path.exists()
headers={'X-Hermes-Profile':'default'}
with httpx.Client(base_url='http://127.0.0.1:18819',timeout=180,trust_env=False) as client:
 assert client.post('/auth/password-login',json={'provider':'basic',**credentials}).status_code==200
 me=client.get('/api/auth/me').json();assert me['provider']=='basic' and me['user_id']=='adrian' and me['expires_at']>time.time()
 response=client.post('/api/plugins/lifeos-hook-bridge/memory/sources/preview',headers=headers,json={'paths':sorted(contents)})
 assert response.status_code==200
 preview=response.json();assert len(preview['sources'])==57 and {s['path'] for s in preview['sources']}==set(contents)
 for source in preview['sources']:
  assert source['accepted'] is True and source['digest']==expected[source['path']]
  assert source['content']==contents[source['path']]
 response=client.post('/api/plugins/lifeos-hook-bridge/memory/sources',headers=headers,json={'paths':sorted(contents),'signature':preview['signature']})
 assert response.status_code==200
 reviewed=response.json();assert reviewed['status'] in {'committed','unchanged'} and reviewed['reviewed_sources']==57
 response=client.post('/api/plugins/lifeos-hook-bridge/memory/prompt/preview',headers=headers,json={'keep_output_format':True})
 assert response.status_code==200
 prompt=response.json();assert prompt['bundle']['launcherName'] and len(prompt['bundle']['skills'])==56
 assert not any(p.startswith('skills/') for p in prompt['omitted_sources'])
 report={'status':'PASS','server':'daily','operation':identifier,'program_commit':request['commit'],
  'archive_sha256':request['package_sha256'],'method':'authenticated-owner-review-of-exact-public-package-sources',
  'package_skill_digests_verified':56,'public_constitution_digest_verified':True,'reviewed_sources':57,
  'review_http_status':200,'review_status':reviewed['status'],'after_admitted_skill_count':56,
  'after_omitted_program_skills':0,'launcher_present':True,'personal_sources_reviewed':0,
  'personal_records_exported':False,'personal_data_imported_or_reset':False,'native_skill_bytes_changed':False}
 report_path.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
