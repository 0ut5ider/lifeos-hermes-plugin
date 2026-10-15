# ABOUTME: Validates the safe receipt from an exact successful daily Atlas preparation command.
# ABOUTME: Lets a backup retry preserve existing synthetic interruption fixtures without consuming them.
import hashlib,json

def verify_preparation(folder,python,operation):
 raw=(folder/'prepare-synthetic-atlas.stdout').read_bytes()
 report=json.loads(raw)
 expected={'status':'PASS','action':'prepare','version':'0.5.0','cases':[
  {'case':'baseline','files':51,'archives':1,'journal_present':False},
  {'case':'interrupted','files':55,'archives':2,'journal_present':True},
  {'case':'later-edit','files':55,'archives':2,'journal_present':True}],
  'personal_data_used':False,'live_store_modified':False}
 assert json.dumps(report,sort_keys=True)==json.dumps(expected,sort_keys=True)
 command=['pct','exec','102','--','runuser','-u','lifeos-hermes','--',python,'-B',
  '/home/lifeos-hermes/releases/qualification-0.5.0/history_guest_recovery.py','prepare',
  '/home/lifeos-hermes/.hermes/.lifeos-releases/'+operation+'/package']
 operations=json.loads((folder/'operations.json').read_bytes())
 matches=[row for row in operations if row['label']=='prepare-synthetic-atlas']
 assert len(matches)==1 and type(matches[0]['exit_code']) is int and matches[0]['exit_code']==0 and matches[0]['command']==command
 return {'report':report,'receipt_sha256':hashlib.sha256(raw).hexdigest(),
  'evidence_directory':str(folder),'operation':operation}
