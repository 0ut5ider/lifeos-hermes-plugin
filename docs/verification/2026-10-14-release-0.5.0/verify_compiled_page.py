# ABOUTME: Compares the archived, installed, and HTTP-served assistant page.
# ABOUTME: Exports exact source identities without reading synthetic or personal memory content.
import hashlib,json,os,urllib.request
from pathlib import Path
os.umask(0o077)
home=Path('/home/lifeos-hermes');stage=home/'releases/qualification-0.5.0';profile=home/'.hermes'
identifier=json.loads((stage/'fresh-preparation.json').read_bytes())['preparation']['identifier']
request=json.loads((profile/'.lifeos-releases'/identifier/'request.json').read_bytes())
relative='LIFEOS/PULSE/Observability/out/assistant.html'
installed=Path(request['installed'])/relative
archived=profile/'.lifeos-releases'/identifier/'package/lifeos/LifeOS/install'/relative
served=urllib.request.urlopen('http://127.0.0.1:31337/assistant',timeout=30).read()
digest=lambda data:hashlib.sha256(data).hexdigest()
report={'status':'PASS','program_commit':request['commit'],'archive_sha256':request['package_sha256'],
 'archived_page_sha256':digest(archived.read_bytes()),'installed_page_sha256':digest(installed.read_bytes()),
 'served_page_sha256':digest(served),'served_matches_installed':served==installed.read_bytes(),
 'installed_matches_archived':installed.read_bytes()==archived.read_bytes(),'synthetic_data_only':True}
assert report['served_matches_installed'] and report['installed_matches_archived']
(stage/'compiled-page-identity.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
