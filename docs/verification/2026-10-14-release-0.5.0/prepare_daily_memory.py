# ABOUTME: Creates one synthetic preservation baseline through the authenticated daily owner memory API.
# ABOUTME: Confirms previously forgotten synthetic facts remain absent and exports only safe receipt references.
import json,os
from pathlib import Path
import httpx

os.umask(0o077)
home=Path('/home/lifeos-hermes')
stage=home/'releases/qualification-0.5.0'
target=stage/'daily-memory-baseline.json'
assert not target.exists(),'The daily synthetic baseline already exists'
credentials=json.loads((home/'install-input/dashboard-access.json').read_bytes())
marker='STABLE-050-DAILY-04EFE633'
with httpx.Client(base_url='http://127.0.0.1:18819',timeout=60) as client:
 login=client.post('/auth/password-login',json={'provider':'basic',**credentials});assert login.status_code==200
 me=client.get('/api/auth/me');assert me.status_code==200 and me.json()['provider']=='basic' and me.json()['user_id']=='adrian'
 def tool(name,arguments):
  response=client.post('/api/plugins/lifeos-hook-bridge/memory/review',headers={'X-Hermes-Profile':'default'},json={'tool':name,'arguments':arguments})
  assert response.status_code==200
  return response.json()
 for query in ('D253-042-PROMOTION-1014','D253-CEREBO-1011'):
  assert tool('lifeos_memory_search',{'query':query})=={'status':'ok','results':[]}
 result=tool('lifeos_memory_remember',{'content':'Synthetic daily acceptance verification code is '+marker+'.','category':'project','project':'release-0.5.0-qualification','title':'Synthetic release acceptance','request_id':'stable-050-daily-04efe633'})
 assert result['status']=='committed'
 found=tool('lifeos_memory_search',{'query':marker});assert found['status']=='ok' and len(found['results'])==1
 match=found['results'][0]
 assert match['reference']==result['reference']
 assert match['content']=='Synthetic daily acceptance verification code is '+marker+'.'
 report={'status':'PASS','server':'daily','synthetic_query':marker,'reference':result['reference'],'actual_owner_save_and_search_verified':True,'authenticated_owner_verified':True,'prior_forgotten_facts_absent':True,'personal_records_exported':False,'personal_data_imported_or_reset':False}
 target.write_text(json.dumps(report,indent=2)+'\n');target.chmod(0o600)
 print(json.dumps(report,indent=2))
