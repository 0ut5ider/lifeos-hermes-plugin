# ABOUTME: Exercises prior Atlas preparation evidence without preparing or recovering fixtures.
# ABOUTME: Refuses receipts that do not prove the exact successful daily preparation command.
import copy,json,tempfile
from pathlib import Path
from prepared_atlas_evidence import verify_preparation

operation='b9e873b251604202a58442b502a3c2b2'
python='/home/lifeos-hermes/.hermes/.lifeos-releases/'+operation+'/python-environment/bin/python'
command=['pct','exec','102','--','runuser','-u','lifeos-hermes','--',python,'-B',
 '/home/lifeos-hermes/releases/qualification-0.5.0/history_guest_recovery.py','prepare',
 '/home/lifeos-hermes/.hermes/.lifeos-releases/'+operation+'/package']
report={'status':'PASS','action':'prepare','version':'0.5.0','cases':[
 {'case':'baseline','files':51,'archives':1,'journal_present':False},
 {'case':'interrupted','files':55,'archives':2,'journal_present':True},
 {'case':'later-edit','files':55,'archives':2,'journal_present':True}],
 'personal_data_used':False,'live_store_modified':False}
operations=[{'label':'prepare-synthetic-atlas','command':command,'exit_code':0}]
with tempfile.TemporaryDirectory() as temporary:
 folder=Path(temporary)
 def run(value,ops):
  (folder/'prepare-synthetic-atlas.stdout').write_text(json.dumps(value))
  (folder/'operations.json').write_text(json.dumps(ops))
  return verify_preparation(folder,python,operation)
 assert run(report,operations)['report']==report
 mutations=[]
 for key,value in [('status','FAIL'),('action','verify'),('version','0.4.3'),('personal_data_used',True),('live_store_modified',True)]:
  row=copy.deepcopy(report);row[key]=value;mutations.append((row,operations))
 for key,value in [('files',50),('archives',0),('journal_present',True)]:
  row=copy.deepcopy(report);row['cases'][0][key]=value;mutations.append((row,operations))
 row=copy.deepcopy(report);row['cases']=row['cases'][:2];mutations.append((row,operations))
 for ops in ([],operations*2,[dict(operations[0],exit_code=1)],
  [dict(operations[0],command=command[:-2]+['verify',command[-1]])],
  [dict(operations[0],command=[part.replace(operation,'0'*32) for part in command])]):
  mutations.append((report,ops))
 for number,(value,ops) in enumerate(mutations):
  try:run(value,ops)
  except (AssertionError,ValueError,TypeError):pass
  else:raise AssertionError('Invalid preparation accepted: '+str(number))
 print(json.dumps({'status':'PASS','positive':1,'refusals':len(mutations)}))
