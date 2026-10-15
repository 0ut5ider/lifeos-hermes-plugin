// ABOUTME: Exercises authorization refusal ordering in the actual manager memory component.
// ABOUTME: Uses deferred SDK responses to expose stale private state without a browser acceptance claim.
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const test=require('node:test');
function find(node,match){if(!node||typeof node!=='object')return null;if(match(node))return node;for(const child of node.children??[]){const result=find(child,match);if(result)return result;}return null;}
function pending(){let resolve,reject;const promise=new Promise((yes,no)=>{resolve=yes;reject=no;});return {promise,resolve,reject};}
test('an earlier successful poll cannot restore private state after an authorization refusal',async()=>{
 let root,index=0,states=[],mounted=false;
 const first=pending(), second=pending();let requests=0;
 const sdk={React:{createElement(type,props,...children){return {type,props:props??{},children:children.flat()};}},
  hooks:{useState(initial){const slot=index++;if(!(slot in states))states[slot]=initial;return [states[slot],value=>{states[slot]=value;}];},useEffect(){}},
  fetchJSON(){requests++;return requests===1?first.promise:second.promise;}};
 const bundle=fs.readFileSync(path.resolve(__dirname,'../../../optional/lifeos_release_manager/dashboard/dist/index.js'),'utf8');
 vm.runInNewContext(bundle,{window:{__HERMES_PLUGIN_SDK__:sdk,__HERMES_PLUGINS__:{register(_name,component){root=component;}}},setInterval(){return 1;},clearInterval(){}});
 root();states[4]=true;index=0;
 const component=find(root(),node=>typeof node.type==='function'&&node.type.name==='MemoryWorkflows');
 assert.ok(component);states=[];
 sdk.hooks.useEffect=callback=>{if(!mounted){mounted=true;callback();}};
 const render=()=>{index=0;return component.type();};
 render();
 const refresh=find(render(),node=>node.type==='button'&&node.children.includes('Refresh memory workflows')).props.onClick();
 second.reject(new Error('Authentication required'));await refresh;
 assert.ok(!JSON.stringify(render()).includes('Synthetic private owner prompt'));
 first.resolve({operations:[{identifier:'a'.repeat(32),kind:'return',state:'ready',review:{signature:'b'.repeat(64),prompt:'Synthetic private owner prompt'}}]});
 await new Promise(setImmediate);
 const leaked=JSON.stringify(render()).includes('Synthetic private owner prompt');
 fs.writeFileSync(path.join(__dirname,'private-state-ordering.json'),JSON.stringify({requests,refusal_clears_state:true,earlier_response_restores_private_prompt:leaked},null,2)+'\n');
 assert.equal(leaked,false);
});
