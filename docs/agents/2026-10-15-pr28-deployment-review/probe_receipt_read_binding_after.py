# ABOUTME: Checks parsed deployment values and their asset hashes come from the same receipt bytes.
# ABOUTME: Injects a changed second read in memory and never modifies any actual safe receipt.
import hashlib,importlib.util,json
from pathlib import Path
r=Path(__file__).resolve().parent;s=r/'current/certify_deployment.py';spec=importlib.util.spec_from_file_location('review_read_binding',s);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
selected='daily-verification.json';original=(s.parent/selected).read_bytes();value=json.loads(original);value['personal_data_imported_or_reset']=True;changed=(json.dumps(value,indent=2)+'\n').encode();reads={}
class Receipt:
 def __init__(self,name):self.name=name
 def read_bytes(self):
  reads[self.name]=reads.get(self.name,0)+1
  return changed if self.name==selected and reads[self.name]>1 else (s.parent/self.name).read_bytes()
class Folder:
 def __truediv__(self,name):return Receipt(name)
values,hashes=m.load(Folder());accepted=m.certify(values,hashes)['status']=='PASS'
result={'case':'receipt-changes-between-parse-and-hash','certificate_accepts':accepted,'parsed_import_flag':values[selected]['personal_data_imported_or_reset'],'hashed_receipt_import_flag':json.loads(changed)['personal_data_imported_or_reset'],'binds_changed_unvalidated_bytes':hashes[selected]==hashlib.sha256(changed).hexdigest(),'reads':reads,'remote_calls':False,'actual_receipts_modified':False,'release_certificate_written':False}
assert accepted and not result['binds_changed_unvalidated_bytes']
assert all(count==1 for count in reads.values())
assert hashes[selected]==hashlib.sha256(original).hexdigest()
(r/'receipt-read-binding-after.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
