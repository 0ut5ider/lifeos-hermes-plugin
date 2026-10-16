// ABOUTME: Exercises explicit removal review and application controls in the actual manager component.
// ABOUTME: Uses an SDK test implementation and does not claim real browser or owner-service acceptance.
const assert=require('node:assert/strict');
const test=require('node:test');
const {component,find,loadDashboard,settle}=require('./support/dashboard_sdk.cjs');
async function panel(operations){
 const calls=[];
 const sdk={async fetchJSON(url,options){calls.push({url,options});
  if(url.endsWith('/installation'))return {installed:true};
  if(url.endsWith('/operations'))return {operations:[]};
  return {operations};}};
 const app=loadDashboard('releases',{...sdk,globals:{setInterval(){return 1;},clearInterval(){}}});
 const page=app.mount();await settle();
 const render=app.mount(component(page(),'MemoryWorkflows'));await settle();
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
test('a ready activation discloses the local account profile and exact model route',async()=>{
 const access={account:'terminal:1000',destination:'terminal:/synthetic/profile',provider:'custom',model:'synthetic-model',model_route:'e'.repeat(64)};
 const operation={identifier:'a'.repeat(32),kind:'activation',state:'ready',review:{signature:'b'.repeat(64),local_owner_access:access}};
 const view=await panel([operation]);const rendered=view.render();const text=JSON.stringify(rendered);
 for(const value of Object.values(access))assert.ok(text.includes(value),value);
 assert.equal(view.calls.some(call=>call.options?.method==='POST'),false);
});
