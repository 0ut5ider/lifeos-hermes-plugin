// ABOUTME: Tests owner-facing memory status and sharing controls in the dashboard SDK.
// ABOUTME: Verifies activation limits, default grants, and displayed native record references.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');
const bundle = fs.readFileSync(path.join(process.cwd(),'lifeos_hook_bridge/dashboard/dist/index.js'),'utf8');

function find(node, match) {
  if (!node || typeof node !== 'object') return null;
  if (match(node)) return node;
  for (const child of node.children || []) { const result = find(child,match); if (result) return result; }
  return null;
}

async function panel(initial, reviewResponse) {
  const state = [], calls = []; let index = 0, mounted = false, root;
  const sdk = {
    React:{createElement:(type,props,...children)=>({type,props:props||{},children:children.flat()})},
    hooks:{useState(value){const slot=index++; if (!(slot in state)) state[slot]=value;
      return [state[slot],value=>{state[slot]=typeof value==='function'?value(state[slot]):value;}];},useEffect(){}},
    fetchJSON(url,init){calls.push({url,init});
      if(url.endsWith('/memory/review')) {
        if(reviewResponse)return Promise.resolve(reviewResponse(JSON.parse(init.body)));
        return Promise.resolve({status:'ok',results:[{content:'Synthetic visible fact',reference:{id:'stable',revision:3},writer:'dashboard:owner',source:{kind:'explicit'}}]});
      }
      if(url.endsWith('/memory/connections'))return Promise.resolve({status:'enrolled',client:'reader',permissions:{read:['project'],write:[]}});
      return Promise.resolve(initial);},
  };
  vm.runInNewContext(bundle,{window:{crypto:require('node:crypto').webcrypto,__HERMES_PLUGIN_SDK__:sdk,__HERMES_PLUGINS__:{register(_name,view){root=view;}}},console});
  const container=root();
  const component=find(container,node=>typeof node.type==='function'&&node.type.name==='MemoryPreferences');
  assert.ok(component,'The LifeOS page must include the memory preferences panel');
  state.length=0;
  sdk.hooks.useEffect=callback=>{if(!mounted){mounted=true;callback();}};
  const render=()=>{index=0;return component.type();};
  render();await new Promise(setImmediate);
  return {render,calls};
}


(async()=>{
 const proposal={reference:{id:'review-one',revision:4},edit:'Synthetic pending text.',target_file:'/synthetic/rules.md',rationale:'Synthetic reason.',writer:'fixture',status:'pending'};
 for(const decision of ['accept','reject','edit','applied_elsewhere']) {
  let reads=0; let captured;
  const p=await panel({state:'prepared',proposal_review_available:true,remaining_gates:{}},request=>{
   if(request.tool==='lifeos_memory_proposals') { if(++reads===1)return {status:'ok',results:[proposal]}; throw new Error('Synthetic refresh failure'); }
   captured=request;return {status:'committed',proposal_status:{accept:'accepted',reject:'rejected',edit:'edited',applied_elsewhere:'applied-elsewhere'}[request.arguments.decision]};
  });
  await find(p.render(),n=>n.type==='button'&&n.children.includes('Review pending changes')).props.onClick();
  if(decision==='edit')find(p.render(),n=>n.type==='textarea').props.onChange({target:{value:'Owner edited synthetic text.'}});
  if(decision==='applied_elsewhere')find(p.render(),n=>n.type==='input'&&n.props.id==='memory_note_review-one').props.onChange({target:{value:'Synthetic other target.'}});
  const label={accept:'Accept change',reject:'Reject change',edit:'Apply edited change',applied_elsewhere:'Mark applied elsewhere'}[decision];
  await find(p.render(),n=>n.type==='button'&&n.children.includes(label)).props.onClick();
  const msg=find(p.render(),n=>n.type==='p'&&n.children.some(c=>typeof c==='string'&&c.includes('Could not refresh pending changes')));
  assert.ok(msg);assert.ok(msg.children[0].startsWith('Change '));assert.deepEqual(captured.arguments.reference,proposal.reference);
  assert.equal(captured.arguments.decision,decision);
  console.log(JSON.stringify({case:decision,request:captured,outcome:msg.children[0]}));
 }
})().catch(error=>{console.error(error);process.exitCode=1;});
