// ABOUTME: Exercises explicit removal review and application controls in the actual manager component.
// ABOUTME: Uses an SDK test implementation and does not claim real browser or owner-service acceptance.
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const test=require('node:test');
function find(node,match){if(!node||typeof node!=='object')return null;if(match(node))return node;for(const child of node.children??[]){const result=find(child,match);if(result)return result;}return null;}
async function panel(operations){
 let root,index=0,states=[],mounted=false;const calls=[];
 const sdk={React:{createElement(type,props,...children){return {type,props:props??{},children:children.flat()};}},
 hooks:{useState(initial){const slot=index++;if(!(slot in states))states[slot]=initial;return [states[slot],value=>{states[slot]=value;}];},useRef(initial){const slot=index++;if(!(slot in states))states[slot]={current:initial};return states[slot];},useEffect(){}},
 async fetchJSON(url,options){calls.push({url,options});return {operations};}};
 const bundle=fs.readFileSync(path.resolve(__dirname,'../optional/lifeos_release_manager/dashboard/dist/index.js'),'utf8');
 vm.runInNewContext(bundle,{window:{__HERMES_PLUGIN_SDK__:sdk,__HERMES_PLUGINS__:{register(_name,component){root=component;}}},setInterval(){return 1;},clearInterval(){}});
 root();states[4]=true;index=0;const component=find(root(),node=>typeof node.type==='function'&&node.type.name==='MemoryWorkflows');assert.ok(component);states=[];
 sdk.hooks.useEffect=callback=>{if(!mounted){mounted=true;callback();}};
 const render=()=>{index=0;return component.type();};render();await new Promise(setImmediate);
 return {render,calls};
}
test('complete removal requires explicit Discord acknowledgment and queues the exact verified return',async()=>{
 const operation={identifier:'a'.repeat(32),kind:'return',state:'verified',review:{signature:'b'.repeat(64)},receipt:{application_verified:true}};
 const view=await panel([operation]);
 let button=find(view.render(),node=>node.type==='button'&&node.children.includes('Prepare complete LifeOS removal'));
 assert.ok(button);assert.equal(button.props.disabled,true);
 const checkbox=find(view.render(),node=>node.type==='input'&&node.props.type==='checkbox');assert.ok(checkbox);
 checkbox.props.onChange({target:{checked:true}});
 button=find(view.render(),node=>node.type==='button'&&node.children.includes('Prepare complete LifeOS removal'));
 assert.equal(button.props.disabled,false);await button.props.onClick();
 const post=view.calls.find(call=>call.options?.method==='POST');assert.ok(post);
 assert.deepEqual(JSON.parse(post.options.body),{kind:'removal',identifier:operation.identifier,signature:operation.review.signature,disable_discord:true});
});
test('a ready removal has distinct software application and recovery instructions',async()=>{
 const operation={identifier:'a'.repeat(32),kind:'removal',state:'ready',review:{signature:'b'.repeat(64),stock_commit:'c'.repeat(40),recovery_command:'/synthetic/private/recover'}};
 const view=await panel([operation]);const rendered=view.render();
 const button=find(rendered,node=>node.type==='button'&&node.children.includes('Remove reviewed LifeOS software'));assert.ok(button);
 assert.ok(JSON.stringify(rendered).includes('/synthetic/private/recover'));
 await button.props.onClick();const post=view.calls.find(call=>call.options?.method==='POST');
 assert.ok(post.url.endsWith('/'+operation.identifier+'/apply'));
 assert.deepEqual(JSON.parse(post.options.body),{signature:operation.review.signature});
});
