// ABOUTME: Tests owner-facing memory status and sharing controls in the dashboard SDK.
// ABOUTME: Verifies activation limits, default grants, and displayed native record references.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');
const bundle = fs.readFileSync(path.join(__dirname,'../lifeos_hook_bridge/dashboard/dist/index.js'),'utf8');

function find(node, match) {
  if (!node || typeof node !== 'object') return null;
  if (match(node)) return node;
  for (const child of node.children || []) { const result = find(child,match); if (result) return result; }
  return null;
}

async function panel(initial) {
  const state = [], calls = []; let index = 0, mounted = false, root;
  const sdk = {
    React:{createElement:(type,props,...children)=>({type,props:props||{},children:children.flat()})},
    hooks:{useState(value){const slot=index++; if (!(slot in state)) state[slot]=value;
      return [state[slot],value=>{state[slot]=typeof value==='function'?value(state[slot]):value;}];},useEffect(){}},
    fetchJSON(url,init){calls.push({url,init});
      if(url.endsWith('/memory/review'))return Promise.resolve({status:'ok',results:[{content:'Synthetic visible fact',reference:{id:'stable',revision:3},writer:'dashboard:owner',source:{kind:'explicit'}}]});
      if(url.endsWith('/memory/connections'))return Promise.resolve({status:'enrolled',client:'reader',permissions:{read:['project'],write:[]}});
      return Promise.resolve(initial);},
  };
  vm.runInNewContext(bundle,{window:{__HERMES_PLUGIN_SDK__:sdk,__HERMES_PLUGINS__:{register(_name,view){root=view;}}},console});
  const container=root();
  const component=find(container,node=>typeof node.type==='function'&&node.type.name==='MemoryPreferences');
  assert.ok(component,'The LifeOS page must include the memory preferences panel');
  state.length=0;
  sdk.hooks.useEffect=callback=>{if(!mounted){mounted=true;callback();}};
  const render=()=>{index=0;return component.type();};
  render();await new Promise(setImmediate);
  return {render,calls};
}

test('memory status names incomplete gates and does not offer activation',async()=>{
  const p=await panel({state:'not_configured',activation_ready:false,remaining_gates:{native_proposal_policy:'Native proposal approval'},connections:[]});
  const view=p.render();
  assert.ok(find(view,n=>n.type==='li'&&n.children.includes('Native proposal approval')));
  assert.equal(find(view,n=>n.type==='button'&&n.children.includes('Enable LifeOS memory')),null);
  assert.ok(find(view,n=>n.type==='button'&&n.children.includes('Check memory status')));
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
  await new Promise(setImmediate);
  const view=p.render();
  assert.ok(find(view,n=>n.type==='p'&&n.children.includes('Synthetic visible fact')));
  assert.ok(find(view,n=>n.type==='p'&&n.children.some(c=>typeof c==='string'&&c.includes('stable, revision 3'))));
  for(const [id,value] of [['memory_client','reader'],['memory_public_key','ssh-ed25519 synthetic'],['memory_projects','lab']]) {
    find(p.render(),n=>n.type==='input'&&n.props.id===id).props.onChange({target:{value}});
  }
  find(p.render(),n=>n.type==='form'&&n.props.id==='memory_enrollment').props.onSubmit({preventDefault(){}});
  await new Promise(setImmediate);
  const request=p.calls.find(c=>c.url.endsWith('/memory/connections')&&c.init?.method==='POST');
  assert.deepEqual(JSON.parse(request.init.body),{client:'reader',public_key:'ssh-ed25519 synthetic',projects:['lab'],model_route:'unknown',read:['project'],write_project:false});
});
