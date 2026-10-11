# ABOUTME: Protects the three verified whole-guest archives from scheduled pruning.
# ABOUTME: Records current native backup attributes after each successful protection change.
import json,os,pathlib,subprocess
os.umask(0o077)
here=pathlib.Path('/root/lifeos-daily-install/recovery')
receipts=json.loads((here/'receipts.json').read_text())
assert [r['case'] for r in receipts]==['baseline','interrupted','later-edit']
protected=[]
for row in receipts:
    assert row['status']=='PASS' and row['archive'].startswith('PBS-01:backup/ct/102/')
    target='/nodes/pve-tr1950x/storage/PBS-01/content/'+row['archive']
    result=subprocess.run(['pvesh','set',target,'--protected','1'],capture_output=True,text=True,check=True)
    attributes=json.loads(subprocess.check_output(['pvesh','get',target,'--output-format','json'],text=True))
    assert attributes['protected']==1,attributes
    protected.append({'case':row['case'],'archive':row['archive'],'protected':True})
(here/'protected-archives.json').write_text(json.dumps({'status':'PASS','archives':protected},indent=2)+'\n')
print(json.dumps(protected,indent=2))
