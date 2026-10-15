# ABOUTME: Replays the default GitHub URL and complete LifeOS installation through the real stock Hermes UI.
# ABOUTME: Uses a synthetic owner session and records only safe actual request and operation metadata.
import json,os,re,sys,time
from pathlib import Path
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright,TimeoutError as BrowserTimeout

os.umask(0o077)
observe_only=sys.argv[1:]==['--observe-applied']
out=Path('/home/outsider/.cache/lifeos-release-0.5.0-20261014')/('public-ui-replay-5' if observe_only else 'public-ui-replay-3')
assert not out.exists();out.mkdir(mode=0o700)
origin='http://127.0.0.1:18948'
identifier_url='https://github.com/0ut5ider/lifeos-hermes-plugin.git#optional/lifeos_release_manager'
commit='04efe633296eb2b1a1d95561ca6d3e9516cd47dc'
archive='a6dd0e11b8fb1b5ae30345be20c955db02728839f7bc907f60a70944ad392813'
report={'status':'RUNNING','guest':113,'address':'192.168.8.244','synthetic_owner_only':True,
 'production_guest_changed':False,'actions':[],'browser_fallback_reason':'Two collaborative browser click timeouts; no install request or manager directory existed.'}
def save():
 (out/'receipt.json').write_text(json.dumps(report,indent=2)+'\n')
def response_for(page,path,button):
 with page.expect_response(lambda r:urlparse(r.url).path==path,timeout=300000) as pending:
  button.click(timeout=30000)
 response=pending.value;data=response.json()
 return response,data
def renew_owner(page):
 page.goto('http://127.0.0.1:18945/synthetic-owner-login')
 response=page.request.get(origin+'/api/auth/me')
 assert response.status==200,'The owner login does not return an authenticated session'
 identity=response.json()
 assert identity['provider']=='basic' and identity['user_id']=='qualification-owner'
 report['authenticated_owner_verified']=True
def wait_applied(page,identifier,allowed,target):
 deadline=time.monotonic()+1200
 while True:
  try:
   response=page.request.get(origin+'/api/plugins/lifeos-release-manager/operations',timeout=45000)
  except Exception:
   assert time.monotonic()<deadline,'The native operation status does not return'
   time.sleep(5);continue
  report['last_operation_http_status']=response.status;save()
  if response.status==401:
   assert time.monotonic()<deadline,'The owner session renewal wait expires'
   renew_owner(page)
   report['owner_session_renewals']=report.get('owner_session_renewals',0)+1;save()
   continue
  if response.status in {502,503,504}:
   assert time.monotonic()<deadline,'The dashboard restart wait expires'
   time.sleep(5);continue
  assert response.status==200,'The operation status request refuses'
  entries=response.json()['operations']
  selected=next(item for item in entries if item['identifier']==identifier)
  report['operation_state']=selected['state'];save()
  if selected['state']==target:return selected
  assert selected['state'] in allowed,'The actual native operation refuses: '+selected['state']
  assert time.monotonic()<deadline,'The native operation wait expires'
  time.sleep(5)

save()
def run_browser():
 with sync_playwright() as playwright:
  browser=playwright.chromium.launch(headless=True,
   executable_path='/home/outsider/.cache/ms-playwright/chromium_headless_shell-1194/chrome-linux/headless_shell')
  report['browser_version']=browser.version
  context=browser.new_context(viewport={'width':1440,'height':1000})
  page=context.new_page();renew_owner(page)
  if observe_only:
   prior=json.loads(out.with_name('public-ui-replay-3').joinpath('receipt.json').read_bytes())
   assert prior['operation']=='568cd8927be849e7a92f0d048999d070' and len(prior['actions'])==4
   assert prior['actions'][-1]=={'action':'owner-ui-apply','http_status':200,'identifier':prior['operation']}
   report.update(actions=prior['actions'],operation=prior['operation'],read_only_completion=True,
    original_observer_completed=False,duplicate_apply_performed=False)
   wait_applied(page,prior['operation'],{'ready','queued-apply','applying'},'applied')
   report.update(status='UI_APPLIED',actual_ui_actions_verified=True,public_catalog_used=True,
    package_commit=commit,archive_sha256=archive,installed_program_identity_verified=False)
   save();browser.close();return
  if sys.argv[1:]==['--resume-manager']:
   prior=json.loads(out.with_name('public-ui-replay-2').joinpath('receipt.json').read_bytes())
   assert prior['status']=='FAIL' and len(prior['actions'])==1
   action=prior['actions'][0]
   assert action=={'action':'native-web-github-install','http_status':200,'identifier':identifier_url,
    'ref':None,'force':False,'plugin_name':'lifeos-release-manager','enabled':True}
   report['actions'].append(action);report['manager_bootstrap_in_prior_browser_session']=True;save()
  else:
   assert not sys.argv[1:]
   field=page.locator('#install-url');field.wait_for(state='visible',timeout=60000)
   field.fill(identifier_url)
   response,data=response_for(page,'/api/dashboard/agent-plugins/install',
    field.locator('xpath=../..').locator('button').filter(has_text=re.compile('^Install$',re.I)))
   request=response.request.post_data_json
   assert response.status==200 and data['ok'] is True and data['plugin_name']=='lifeos-release-manager'
   assert request['identifier']==identifier_url and request.get('ref') is None
   assert request.get('force',False) is False and data['enabled'] is True
   report['actions'].append({'action':'native-web-github-install','http_status':response.status,
    'identifier':request['identifier'],'ref':request.get('ref'),'force':request.get('force',False),
    'plugin_name':data['plugin_name'],'enabled':data['enabled']});save()
  page.goto(origin+'/lifeos-releases?profile=default')
  install=page.get_by_role('button',name='Install LifeOS',exact=True)
  for attempt in range(3):
   try:
    install.wait_for(state='visible',timeout=10000);break
   except BrowserTimeout:
    if attempt==2:raise
    page.reload()
    report['page_refreshes_after_bootstrap']=attempt+1;save()
  page.get_by_label('Your name',exact=True).fill('Synthetic public owner')
  page.get_by_label('Assistant name',exact=True).fill('Synthetic public assistant')
  assert page.get_by_placeholder('Latest stable',exact=True).input_value()==''
  response,data=response_for(page,'/api/plugins/lifeos-release-manager/prepare',install)
  request=response.request.post_data_json
  assert response.status==202 and request['intent']=='install' and 'version' not in request
  identifier=data['identifier'];assert len(identifier)==32
  report['operation']=identifier
  report['actions'].append({'action':'install-lifeos-latest-stable','http_status':response.status,
   'intent':request['intent'],'version_field_blank':True,'identifier':identifier});save()
  wait_applied(page,identifier,{'preparing'},'ready')
  response,data=response_for(page,'/api/plugins/lifeos-release-manager/operations/'+identifier+'/review',
   page.get_by_role('button',name='Review release',exact=True))
  assert response.status==200 and data['version']=='0.5.0' and data['commit']==commit
  assert data['package_sha256']==archive and data['fresh'] is True and data['state']=='ready'
  report['actions'].append({'action':'owner-ui-review','http_status':response.status,
   'version':data['version'],'commit':data['commit'],'package_sha256':data['package_sha256'],'fresh':data['fresh']});save()
  response,data=response_for(page,'/api/plugins/lifeos-release-manager/operations/'+identifier+'/apply',
   page.get_by_role('button',name='Install this release',exact=True))
  assert response.status==200 and data['identifier']==identifier and data['action']=='apply'
  report['actions'].append({'action':'owner-ui-apply','http_status':response.status,'identifier':identifier});save()
  wait_applied(page,identifier,{'ready','queued-apply','applying'},'applied')
  report.update(status='UI_APPLIED',actual_ui_actions_verified=True,public_catalog_used=True,
   package_commit=commit,archive_sha256=archive,installed_program_identity_verified=False)
  save();browser.close()
try:
 run_browser()
 (out/'process.done').write_text('0\n')
except BaseException as error:
 report.update(status='FAIL',error_type=type(error).__name__);save()
 (out/'process.done').write_text('1\n');raise
