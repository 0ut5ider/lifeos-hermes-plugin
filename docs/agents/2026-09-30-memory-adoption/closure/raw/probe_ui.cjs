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

async function panel(initial, reviewResponse, adoptionResponse) {
  const state = [], calls = []; let index = 0, mounted = false, root, statusReads = 0;
  const sdk = {
    React:{createElement:(type,props,...children)=>({type,props:props||{},children:children.flat()})},
    hooks:{useState(value){const slot=index++; if (!(slot in state)) state[slot]=value;
      return [state[slot],value=>{state[slot]=typeof value==='function'?value(state[slot]):value;}];},useEffect(){}},
    fetchJSON(url,init){calls.push({url,init});
      if(url.includes('/memory/adoption') && adoptionResponse)return Promise.resolve(adoptionResponse(url,JSON.parse(init.body)));
      if(url.endsWith('/memory/review')) {
        if(reviewResponse)return Promise.resolve(reviewResponse(JSON.parse(init.body)));
        return Promise.resolve({status:'ok',results:[{content:'Synthetic visible fact',reference:{id:'stable',revision:3},writer:'dashboard:owner',source:{kind:'explicit'}}]});
      }
      if(url.endsWith('/memory/connections'))return Promise.resolve({status:'enrolled',client:'reader',permissions:{read:['project'],write:[]}});
      if (++statusReads > 1) return Promise.reject(new Error("Synthetic status refresh failure")); return Promise.resolve(initial);},
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
 const records=Array.from({length:26},(_,i)=>({path:'LIFEOS/MEMORY/LEARNING/SYSTEM/'+i+'.md',content:'Synthetic marker '+i,category:'project',source_kind:'learning'}));
 const preview={signature:'c'.repeat(64),records,proposals:[],excluded:[]};let attempts=0;
 const p=await panel({state:'prepared',remaining_gates:{}},null,(url)=>{
  if(url.endsWith('/preview'))return preview;
  if(++attempts===1)throw new Error('Synthetic lost response');
  return {status:'committed',facts_adopted:26,proposals_adopted:0};
 });
 await find(p.render(),n=>n.type==='button'&&n.children.includes('Preview existing LifeOS memory')).props.onClick();
 assert.ok(find(p.render(),n=>n.type==='p'&&n.children.includes('Synthetic marker 24')));
 assert.equal(find(p.render(),n=>n.type==='p'&&n.children.includes('Synthetic marker 25')),null);
 find(p.render(),n=>n.type==='input'&&n.props.id==='memory_source_project_0').props.onChange({target:{value:' lab '}});
 find(p.render(),n=>n.type==='button'&&n.children.includes('Next sources')).props.onClick();
 assert.ok(find(p.render(),n=>n.type==='p'&&n.children.includes('Synthetic marker 25')));
 assert.equal(find(p.render(),n=>n.type==='p'&&n.children.includes('Synthetic marker 24')),null);
 for(let i=0;i<2;i++)await find(p.render(),n=>n.type==='button'&&n.children.includes('Add reviewed sources to memory')).props.onClick();
 const calls=p.calls.filter(c=>c.url.endsWith('/memory/adoption')).map(c=>JSON.parse(c.init.body));
 assert.deepEqual(calls[0],calls[1]);assert.deepEqual(calls[1].projects,{[records[0].path]:'lab'});
 const message=find(p.render(),n=>n.props.role==='status').children[0];assert.ok(message.startsWith('Added 26 fact(s)'));assert.ok(message.includes('Could not refresh memory status'));
 console.log(JSON.stringify({pagination:25,records:26,retry_identical:true,request:calls[1],message}));
})().catch(e=>{console.error(e);process.exitCode=1;});
