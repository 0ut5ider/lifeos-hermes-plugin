// ABOUTME: Tests owner-facing memory status and sharing controls in the dashboard SDK.
// ABOUTME: Verifies activation limits, default grants, and displayed native record references.
const assert = require('node:assert/strict');
const test = require('node:test');
const { component, find, loadDashboard, plain, settle } = require('./support/dashboard_sdk.cjs');

async function panel(initial, reviewResponse, adoptionResponse) {
  const calls = [];
  const sdk = {
    fetchJSON(url,init){calls.push({url,init});
      if(url.includes('/memory/adoption') && adoptionResponse)return Promise.resolve(adoptionResponse(url,JSON.parse(init.body)));
      if(url.endsWith('/memory/review')) {
        if(reviewResponse)return Promise.resolve(reviewResponse(JSON.parse(init.body)));
        return Promise.resolve({status:'ok',results:[{content:'Synthetic visible fact',reference:{id:'stable',revision:3},writer:'dashboard:owner',source:{kind:'explicit'}}]});
      }
      if(url.endsWith('/memory/connections'))return Promise.resolve({status:'enrolled',client:'reader',permissions:{read:['project'],write:[]}});
      return typeof initial==='function'?Promise.resolve().then(()=>initial(url,init)):Promise.resolve(initial);},
  };
  const app=loadDashboard('bridge',{...sdk,window:{crypto:require('node:crypto').webcrypto}});
  const render=app.mount(component(app.preview(),'MemoryPreferences'));
  await settle();
  return {render,calls};
}

test('memory status explains reviewed activation without engineering gates',async()=>{
  const p=await panel({state:'prepared',activation_ready:false,remaining_gates:{native_proposal_policy:'Native proposal approval'},connections:[]});
  const view=p.render();
  assert.equal(find(view,n=>n.type==='li'&&n.children.includes('Native proposal approval')),null);
  assert.ok(find(view,n=>n.type==='p'&&n.children.some(c=>typeof c==='string'&&
    c.includes('Open LifeOS releases to review and apply the provider switch'))));
  assert.equal(JSON.stringify(view).includes('Ownership setup is still in development'),false);
  assert.equal(find(view,n=>n.type==='button'&&n.children.includes('Enable LifeOS memory')),null);
  assert.ok(find(view,n=>n.type==='button'&&n.children.includes('Check memory status')));
});

test('agent correction guidance requires active memory ownership',async()=>{
  for(const ownership of [false,true]) {
    const p=await panel({state:'prepared',ownership_enabled:ownership,remaining_gates:{}});
    const guidance=find(p.render(),n=>n.type==='p'&&n.children.some(c=>
      typeof c==='string'&&c.includes('Ask your agent to correct or forget')));
    assert.equal(Boolean(guidance),ownership);
    if(!ownership)assert.ok(find(p.render(),n=>n.type==='p'&&n.children.some(c=>
      typeof c==='string'&&c.includes('Agent corrections and forgetting are unavailable'))));
    assert.equal(JSON.stringify(p.render()).includes('Ownership activation is not available in this version'),false);
  }
});

test('pending changes show their target and exact revision for manual decisions',async()=>{
  const proposal={reference:{id:'pending-one',revision:2},edit:'Confirm before synthetic publication.',
    target_file:'/synthetic/OPERATIONAL_RULES.md',rationale:'Synthetic owner rule.',writer:'chat-a:100',
    confidence:0.8,status:'pending'};
  let resolved=false;
  const p=await panel({state:'prepared',native_health:'ok',proposal_review_available:true,remaining_gates:{}},request=>{
    if(request.tool==='lifeos_memory_proposals')return {status:'ok',results:resolved?[]:[proposal]};
    resolved=true;return {status:'committed',proposal_status:'accepted',proposal_reference:{id:'pending-one',revision:3}};
  });
  const show=find(p.render(),n=>n.type==='button'&&n.children.includes('Review pending changes'));
  assert.ok(show,'The owner must be able to inspect native pending proposals');
  await show.props.onClick();
  let view=p.render();
  assert.ok(find(view,n=>n.type==='p'&&n.children.includes(proposal.edit)));
  assert.ok(find(view,n=>n.type==='p'&&n.children.some(c=>typeof c==='string'&&c.includes(proposal.target_file))));
  await find(view,n=>n.type==='button'&&n.children.includes('Accept change')).props.onClick();
  const request=p.calls.filter(c=>c.url.endsWith('/memory/review')).map(c=>JSON.parse(c.init.body))
    .find(c=>c.tool==='lifeos_memory_decide_proposal');
  assert.deepEqual(request.arguments.reference,proposal.reference);
  assert.equal(request.arguments.decision,'accept');
  assert.match(request.arguments.request_id,/^dashboard-/);
  assert.equal(find(p.render(),n=>n.type==='p'&&n.children.includes(proposal.edit)),null);
  assert.ok(find(p.render(),n=>n.type==='p'&&n.children.some(c=>typeof c==='string'&&c.includes('accepted'))));
});

test('conflicted proposal remains visible and edit decisions send the owner draft',async()=>{
  const proposal={reference:{id:'conflict-one',revision:1},edit:'Original synthetic rule.',
    target_file:'/synthetic/rules.md',rationale:'Synthetic proposal.',writer:'chat-a:100',status:'pending'};
  const p=await panel({state:'prepared',native_health:'ok',proposal_review_available:true,remaining_gates:{}},request=>
    request.tool==='lifeos_memory_proposals'?{status:'ok',results:[proposal]}:{status:'conflict',reason:'The target changed.'});
  await find(p.render(),n=>n.type==='button'&&n.children.includes('Review pending changes')).props.onClick();
  const field=find(p.render(),n=>n.type==='textarea'&&n.props.id==='memory_edit_conflict-one');
  assert.ok(field);
  field.props.onChange({target:{value:'Edited synthetic rule.'}});
  await find(p.render(),n=>n.type==='button'&&n.children.includes('Apply edited change')).props.onClick();
  const request=p.calls.map(c=>c.init?.body&&JSON.parse(c.init.body)).find(c=>c?.tool==='lifeos_memory_decide_proposal');
  assert.equal(request.arguments.content,'Edited synthetic rule.');
  assert.equal(request.arguments.decision,'edit');
  assert.ok(find(p.render(),n=>n.type==='p'&&n.children.includes('The target changed.')));
  assert.ok(find(p.render(),n=>n.type==='p'&&n.children.includes(proposal.edit)));
});

test('valid minimal revoked grants do not break the preferences page',async()=>{
  const p=await panel({state:'prepared',native_health:'ok',connections:[{client:'minimal',enabled:false}],remaining_gates:{}});
  assert.ok(find(p.render(),n=>n.type==='p'&&n.children.includes('minimal: revoked')));
  assert.ok(find(p.render(),n=>n.type==='p'&&n.children.includes('Reads: project. Writes: none.')));
});

test('owner search displays references and new connections default to read-only project access',async()=>{
  const p=await panel({state:'prepared',native_health:'ok',active_facts:1,sharing_enabled:false,connections:[],remaining_gates:{}});
  find(p.render(),n=>n.type==='input'&&n.props.id==='memory_query').props.onChange({target:{value:'synthetic'}});
  find(p.render(),n=>n.type==='form'&&n.props.id==='memory_search').props.onSubmit({preventDefault(){}});
  await settle();
  const view=p.render();
  assert.ok(find(view,n=>n.type==='p'&&n.children.includes('Synthetic visible fact')));
  assert.ok(find(view,n=>n.type==='p'&&n.children.some(c=>typeof c==='string'&&c.includes('stable, revision 3'))));
  for(const [id,value] of [['memory_client','reader'],['memory_public_key','ssh-ed25519 synthetic'],['memory_projects','lab']]) {
    find(p.render(),n=>n.type==='input'&&n.props.id===id).props.onChange({target:{value}});
  }
  find(p.render(),n=>n.type==='form'&&n.props.id==='memory_enrollment').props.onSubmit({preventDefault(){}});
  await settle();
  const request=p.calls.find(c=>c.url.endsWith('/memory/connections')&&c.init?.method==='POST');
  assert.deepEqual(JSON.parse(request.init.body),{client:'reader',public_key:'ssh-ed25519 synthetic',projects:['lab'],model_route:'unknown',read:['project'],write_project:false});
});

test('connection form is replaced by an installation note without the sharing component',async()=>{
  const p=await panel({state:'prepared',native_health:'ok',sharing_enabled:false,connection_enrollment_available:false,
    connections:[{client:'reader',enabled:true}],remaining_gates:{}});
  const view=p.render();
  assert.equal(find(view,n=>n.type==='form'&&n.props.id==='memory_enrollment'),null);
  assert.ok(find(view,n=>n.type==='p'&&n.props.id==='memory_enrollment_unavailable'));
  assert.ok(find(view,n=>n.type==='button'&&n.children.includes('Revoke reader')));
});

test('a disabled connection with a remaining SSH entry offers removal only with the component',async()=>{
  const connection={client:'reader',enabled:false,credential_entry_pending:true};
  let view=(await panel({state:'prepared',native_health:'ok',connection_enrollment_available:true,connections:[connection],remaining_gates:{}})).render();
  assert.ok(find(view,n=>n.type==='button'&&n.children.includes('Remove SSH entry of reader')));
  view=(await panel({state:'prepared',native_health:'ok',connection_enrollment_available:false,connections:[connection],remaining_gates:{}})).render();
  assert.equal(find(view,n=>n.type==='button'&&n.children.includes('Remove SSH entry of reader')),null);
  assert.ok(find(view,n=>n.type==='p'&&n.children.some(c=>typeof c==='string'&&c.includes('still present'))));
});


test('source adoption previews historical records and sends exact project assignments',async()=>{
  const source={path:'LIFEOS/MEMORY/LEARNING/SYSTEM/sample.md',content:'Synthetic historical source marker',
    source_kind:'learning',category:'project',position:20};
  const preview={signature:'a'.repeat(64),records:[source],proposals:[],excluded:[],scanned_files:1};
  const p=await panel({state:'prepared',native_health:'ok',remaining_gates:{}},null,(url,request)=>
    url.endsWith('/preview')?preview:{status:'committed',facts_adopted:1,proposals_adopted:0,native_files_changed:false});
  await find(p.render(),n=>n.type==='button'&&n.children.includes('Preview existing LifeOS memory')).props.onClick();
  let view=p.render();
  assert.ok(find(view,n=>n.type==='p'&&n.children.includes(source.content)));
  assert.ok(find(view,n=>n.type==='p'&&n.children.some(c=>typeof c==='string'&&c.includes('Historical learning'))));
  find(view,n=>n.type==='input'&&n.props.id==='memory_source_project_0').props.onChange({target:{value:'lab'}});
  await find(p.render(),n=>n.type==='button'&&n.children.includes('Add reviewed sources to memory')).props.onClick();
  const call=p.calls.find(c=>c.url.endsWith('/memory/adoption'));
  const request=JSON.parse(call.init.body);
  assert.equal(request.signature,preview.signature);
  assert.deepEqual(request.projects,{[source.path]:'lab'});
  assert.match(request.request_id,/^dashboard-/);
  assert.ok(find(p.render(),n=>n.type==='p'&&n.children.some(c=>typeof c==='string'&&c.includes('1 fact'))));
  assert.equal(find(p.render(),n=>n.type==='p'&&n.children.includes(source.content)),null);
});

test('source adoption retains a conflicted preview and reuses its request identifier',async()=>{
  const preview={signature:'b'.repeat(64),records:[{path:'LIFEOS/MEMORY/KNOWLEDGE/Research/note.md',
    content:'Synthetic stale source marker',source_kind:'adopted',category:'project',position:10}],proposals:[],excluded:[],scanned_files:1};
  const p=await panel({state:'prepared',native_health:'ok',remaining_gates:{}},null,(url)=>
    url.endsWith('/preview')?preview:{status:'conflict',reason:'The native source preview changed.'});
  await find(p.render(),n=>n.type==='button'&&n.children.includes('Preview existing LifeOS memory')).props.onClick();
  for(let i=0;i<2;i++)await find(p.render(),n=>n.type==='button'&&n.children.includes('Add reviewed sources to memory')).props.onClick();
  const requests=p.calls.filter(c=>c.url.endsWith('/memory/adoption')).map(c=>JSON.parse(c.init.body));
  assert.equal(requests[0].request_id,requests[1].request_id);
  assert.ok(find(p.render(),n=>n.type==='p'&&n.children.includes('Synthetic stale source marker')));
  assert.ok(find(p.render(),n=>n.type==='p'&&n.children.includes('The native source preview changed.')));
});

test('an unconfigured installation offers the owner claim and shows the claimed state',async()=>{
  const p=await panel({state:'not_configured',activation_ready:false,remaining_gates:{},connections:[]});
  const claim=find(p.render(),n=>n.type==='button'&&n.children.includes('Claim this LifeOS installation'));
  assert.ok(claim,'An unconfigured installation must offer the owner claim');
  await claim.props.onClick();
  await settle();
  const request=p.calls.find(c=>c.url.endsWith('/memory/owner'));
  assert.equal(request.init.method,'POST');
  assert.equal(request.init.body,undefined);
  assert.ok(find(p.render(),n=>n.props.role==='status'&&
    n.children.includes('This dashboard account now owns the LifeOS installation. Ownership and sharing stay disabled.')));
  const configured=await panel({state:'prepared',native_health:'ok',remaining_gates:{},connections:[]});
  assert.equal(find(configured.render(),n=>n.type==='button'&&n.children.includes('Claim this LifeOS installation')),null);
});

const json={'Content-Type':'application/json'};
const statusMessage=view=>find(view,n=>n.type==='p'&&n.props.role==='status')?.children[0];
const memoryCalls=p=>p.calls.map(c=>({path:c.url.replace('/api/plugins/lifeos-hook-bridge/memory',''),init:c.init&&plain(c.init)}));

test('connection changes refresh memory status and report each outcome',async()=>{
  let status={state:'prepared',native_health:'ok',sharing_enabled:false,connections:[{client:'reader',enabled:true}],remaining_gates:{}};
  const p=await panel((url,init)=>{
    if(url.endsWith('/memory/sharing')){status={...status,sharing_enabled:JSON.parse(init.body).enabled};return {status:'ok',sharing_enabled:status.sharing_enabled};}
    if(init?.method==='DELETE')return {status:'revoked',client:'reader'};
    return status;
  });
  await find(p.render(),n=>n.type==='button'&&n.children.includes('Enable memory sharing')).props.onClick();
  assert.deepEqual(memoryCalls(p).slice(-2),[{path:'/sharing',init:{method:'POST',headers:json,body:'{"enabled":true}'}},{path:'',init:undefined}]);
  assert.equal(statusMessage(p.render()),'Memory sharing is enabled.');
  assert.ok(find(p.render(),n=>n.type==='button'&&n.children.includes('Disable memory sharing')));
  await find(p.render(),n=>n.type==='button'&&n.children.includes('Revoke reader')).props.onClick();
  assert.deepEqual(memoryCalls(p).slice(-2),[{path:'/connections/reader',init:{method:'DELETE',headers:json}},{path:'',init:undefined}]);
  assert.equal(statusMessage(p.render()),'Connection revoked. Its contributed facts remain.');
  for(const [id,value] of [['memory_client','writer'],['memory_public_key','ssh-ed25519 synthetic'],['memory_projects',' lab, ,ops '],['memory_model_route','cloud']]) {
    find(p.render(),n=>n.type==='input'&&n.props.id===id).props.onChange({target:{value}});
  }
  for(const id of ['memory_principal','memory_assistant','memory_project_write']) {
    find(p.render(),n=>n.type==='input'&&n.props.id===id).props.onChange({target:{checked:true}});
  }
  await find(p.render(),n=>n.type==='form'&&n.props.id==='memory_enrollment').props.onSubmit({preventDefault(){}});
  assert.deepEqual(memoryCalls(p).slice(-2),[{path:'/connections',init:{method:'POST',headers:json,body:JSON.stringify({client:'writer',
    public_key:'ssh-ed25519 synthetic',projects:['lab','ops'],model_route:'cloud',read:['project','principal','assistant'],write_project:true})}},{path:'',init:undefined}]);
  assert.equal(statusMessage(p.render()),'Connection added. Use its private key with SSH and the lifeos-memory command. The private key stays on the other agent\'s computer.');
  assert.equal(find(p.render(),n=>n.type==='button'&&n.children.includes('Check memory status')).props.disabled,false);
});

test('review refusals report their reason and keep the previous proposal list',async()=>{
  const searches=[{status:'ok',results:[{content:'Synthetic listed fact',reference:{id:'listed',revision:1},writer:'owner'}]},
    {status:'denied',reason:'Synthetic search refusal'},{status:'unavailable'}];
  const p=await panel({state:'prepared',native_health:'ok',proposal_review_available:true,remaining_gates:{}},request=>
    request.tool==='lifeos_memory_search'?searches.shift():{status:'denied',reason:'Synthetic proposal refusal'});
  find(p.render(),n=>n.type==='input'&&n.props.id==='memory_query').props.onChange({target:{value:'synthetic'}});
  const search=()=>find(p.render(),n=>n.type==='form'&&n.props.id==='memory_search').props.onSubmit({preventDefault(){}});
  await search();
  assert.ok(find(p.render(),n=>n.type==='p'&&n.children.includes('Synthetic listed fact')));
  assert.equal(statusMessage(p.render()),undefined);
  await search();
  assert.equal(statusMessage(p.render()),'Synthetic search refusal');
  assert.equal(find(p.render(),n=>n.type==='p'&&n.children.includes('Synthetic listed fact')),null);
  await search();
  assert.equal(statusMessage(p.render()),'unavailable');
  await find(p.render(),n=>n.type==='button'&&n.children.includes('Review pending changes')).props.onClick();
  assert.equal(statusMessage(p.render()),'Synthetic proposal refusal');
  assert.equal(find(p.render(),n=>n.type==='p'&&n.children.includes('No pending changes.')),null);
});

test('a committed decision reports a failed pending-change refresh',async()=>{
  const proposal={reference:{id:'pending-one',revision:2},edit:'Synthetic pending rule.',target_file:'/synthetic/rules.md',
    rationale:'Synthetic owner rule.',writer:'chat-a:100',status:'pending'};
  const responses=[{status:'ok',results:[proposal]},{status:'committed',proposal_status:'rejected'},{status:'denied',reason:'Synthetic refresh refusal'}];
  const p=await panel({state:'prepared',native_health:'ok',proposal_review_available:true,remaining_gates:{}},()=>responses.shift());
  await find(p.render(),n=>n.type==='button'&&n.children.includes('Review pending changes')).props.onClick();
  await find(p.render(),n=>n.type==='button'&&n.children.includes('Reject change')).props.onClick();
  const requests=memoryCalls(p).filter(c=>c.path==='/review');
  assert.ok(requests.every(c=>c.init.method==='POST'&&JSON.stringify(c.init.headers)===JSON.stringify(json)));
  assert.deepEqual(requests.map(c=>JSON.parse(c.init.body).tool),['lifeos_memory_proposals','lifeos_memory_decide_proposal','lifeos_memory_proposals']);
  assert.deepEqual(JSON.parse(requests[2].init.body).arguments,{});
  assert.equal(statusMessage(p.render()),'Change rejected. Could not refresh pending changes: Synthetic refresh refusal');
  assert.ok(find(p.render(),n=>n.type==='p'&&n.children.includes(proposal.edit)));
});

test('a committed adoption reports a failed memory status refresh',async()=>{
  const source={path:'LIFEOS/MEMORY/KNOWLEDGE/Research/note.md',content:'Synthetic adopted source marker',source_kind:'adopted',category:'project'};
  let committed=false;
  const p=await panel(()=>{if(committed)throw new Error('Synthetic status refusal');return {state:'prepared',native_health:'ok',remaining_gates:{}};},null,
    url=>{if(url.endsWith('/preview'))return {signature:'a'.repeat(64),records:[source],proposals:[],excluded:[]};
      committed=true;return {status:'committed',facts_adopted:1,proposals_adopted:0};});
  await find(p.render(),n=>n.type==='button'&&n.children.includes('Preview existing LifeOS memory')).props.onClick();
  await find(p.render(),n=>n.type==='button'&&n.children.includes('Add reviewed sources to memory')).props.onClick();
  assert.equal(statusMessage(p.render()),'Added 1 fact(s) and 0 pending change(s). Native files remain unchanged. Could not refresh memory status: Synthetic status refusal');
  assert.equal(find(p.render(),n=>n.type==='p'&&n.children.includes(source.content)),null);
});
