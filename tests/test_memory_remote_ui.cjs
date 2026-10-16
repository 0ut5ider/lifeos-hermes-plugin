// ABOUTME: Tests the HTTP memory setup and owner consent controls in the dashboard SDK.
// ABOUTME: Verifies explicit permissions, one-time credential display, and safe connection links.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');
const bundle = fs.readFileSync(path.join(__dirname, '../lifeos_hook_bridge/dashboard/dist/index.js'), 'utf8');
function find(node, match) {
  if (!node || typeof node !== 'object') return null;
  if (match(node)) return node;
  for (const child of node.children ?? []) { const found = find(child, match); if (found) return found; }
  return null;
}
async function panel(initial) {
  const state = [], calls = []; let index = 0, mounted = false, root;
  const sdk = {
    React: {createElement: (type, props, ...children) => ({type, props: props ?? {}, children: children.flat()})},
    hooks: {useState(value) {const slot = index++; if (!(slot in state)) state[slot] = value;
      return [state[slot], value => {state[slot] = typeof value === 'function' ? value(state[slot]) : value;}];},
      useEffect() {}},
    fetchJSON(url, init) {calls.push({url, init});
      if (url.endsWith('/connections') && init) return Promise.resolve({token: 'synthetic-token', expires_in: 7776000});
      if (url.includes('/authorization/')) return Promise.resolve({redirect_url: 'http://localhost:9812/callback?code=synthetic'});
      return Promise.resolve(initial);},
  };
  vm.runInNewContext(bundle, {window: {__HERMES_PLUGIN_SDK__: sdk, __HERMES_PLUGINS__: {register(_name, view) {root = view;}}}, console});
  const memory = find(root(), node => node.type?.name === 'MemoryPreferences');
  const component = find(memory.type(), node => node.type?.name === 'MemoryHTTPPreferences');
  assert.ok(component, 'The plugin must include HTTP memory setup');
  state.length = 0; index = 0; mounted = false;
  sdk.hooks.useEffect = callback => {if (!mounted) {mounted = true; callback();}};
  const render = () => {index = 0; return component.type();};
  render(); await new Promise(setImmediate);
  return {render, calls};
}
test('HTTP setup recommends Tailscale Serve and retains explicit grants', async () => {
  const p = await panel({enabled: true, public_url: 'https://synthetic.ts.net', mcp_url: 'https://synthetic.ts.net/mcp',
    sharing_enabled: true, pending: [], connections: []});
  assert.ok(JSON.stringify(p.render()).includes('Tailscale Serve'));
  for (const [id, value] of [['http_client', 'codex'], ['http_projects', 'lab'], ['http_model_route', 'cloud']]) {
    find(p.render(), node => node.props.id === id).props.onChange({target: {value}});
  }
  await find(p.render(), node => node.props.id === 'http_enrollment').props.onSubmit({preventDefault() {}});
  const call = p.calls.find(call => call.url.endsWith('/connections'));
  assert.deepEqual(JSON.parse(call.init.body), {client: 'codex', read: ['project'], projects: ['lab'], model_route: 'cloud', write_project: false});
  assert.ok(find(p.render(), node => node.type === 'textarea' && node.props.value === 'synthetic-token'));
  await find(p.render(), node => node.type === 'button' && node.children.includes('Hide token')).props.onClick();
  assert.equal(JSON.stringify(p.render()).includes('synthetic-token'), false);
});
test('OAuth requests require owner approval and display the callback', async () => {
  const p = await panel({enabled: true, public_url: 'https://synthetic.ts.net', mcp_url: 'https://synthetic.ts.net/mcp',
    sharing_enabled: true, connections: [], pending: [{id: 'request-one', client_name: 'Synthetic client', redirect_uri: 'http://localhost:9812/callback'}]});
  assert.ok(JSON.stringify(p.render()).includes('http://localhost:9812/callback'));
  assert.equal(find(p.render(), node => node.type === 'button' && node.children.includes('Approve Synthetic client')).props.disabled, true);
  find(p.render(), node => node.props.id === 'http_client').props.onChange({target: {value: 'desktop'}});
  find(p.render(), node => node.props.id === 'http_projects').props.onChange({target: {value: 'lab'}});
  await find(p.render(), node => node.type === 'button' && node.children.includes('Approve Synthetic client')).props.onClick();
  const call = p.calls.find(call => call.url.includes('/authorization/'));
  assert.equal(JSON.parse(call.init.body).decision, 'approve');
  const callback = find(p.render(), node => node.type === 'a' && node.children.includes('Return to agent'));
  assert.equal(callback.props.referrerPolicy, 'no-referrer');
  assert.equal(callback.props.href, 'http://localhost:9812/callback?code=synthetic');
});
test('the owner can clear unused OAuth registrations without revoking connections', async () => {
  const p = await panel({enabled: true, public_url: 'https://synthetic.ts.net', sharing_enabled: true, pending: [], connections: []});
  await find(p.render(), node => node.type === 'button' && node.children.includes('Clear unused OAuth registrations')).props.onClick();
  const call = p.calls.find(call => call.url.endsWith('/registrations/clear'));
  assert.deepEqual(JSON.parse(call.init.body), {});
});

test('waiting approval explains required permissions and keeps manual tokens separate', async () => {
  const p = await panel({enabled: true, public_url: 'https://synthetic.ts.net', sharing_enabled: true,
    connections: [], pending: [{id: 'request-one', client_name: 'Synthetic client', redirect_uri: 'http://localhost:9812/callback'}]});
  const view = p.render();
  const approve = find(view, node => node.type === 'button' && node.children.includes('Approve Synthetic client'));
  assert.equal(approve.props['aria-describedby'], 'http_grant_help');
  assert.ok(find(view, node => node.props.id === 'http_grant_help').children.join('').includes('connection name'));
  assert.ok(find(view, node => node.type === 'details' && node.props.id === 'http_manual_token'));
  for (const id of ['http_endpoint', 'http_permissions', 'http_requests', 'http_connections']) {
    assert.ok(find(view, node => node.props.id === id), 'Missing HTTP group: ' + id);
  }
});

test('HTTP settings, denial, and revocation retain their explicit API contracts', async () => {
  const p = await panel({enabled: true, public_url: 'https://synthetic.ts.net', sharing_enabled: true,
    connections: [{client: 'synthetic-agent', enabled: true, read: ['project'], write: [], projects: ['lab']}],
    pending: [{id: 'request-one', client_name: 'Synthetic client', redirect_uri: 'http://localhost:9812/callback'}]});
  find(p.render(), node => node.props.id === 'http_public_url').props.onChange({target: {value: 'https://changed.ts.net'}});
  await find(p.render(), node => node.props.id === 'http_settings').props.onSubmit({preventDefault() {}});
  const enabled = p.calls.find(call => call.url.endsWith('/settings') && call.init?.method === 'POST');
  assert.deepEqual(JSON.parse(enabled.init.body), {enabled: true, public_url: 'https://changed.ts.net'});
  await find(p.render(), node => node.type === 'button' && node.children.includes('Deny Synthetic client')).props.onClick();
  const denied = p.calls.find(call => call.url.includes('/authorization/'));
  assert.deepEqual(JSON.parse(denied.init.body), {decision: 'deny'});
  await find(p.render(), node => node.type === 'button' && node.children.includes('Revoke HTTP synthetic-agent')).props.onClick();
  assert.ok(p.calls.some(call => call.url.endsWith('/connections/synthetic-agent') && call.init.method === 'DELETE'));
  await find(p.render(), node => node.type === 'button' && node.children.includes('Disable HTTP MCP and invalidate credentials')).props.onClick();
  const disabled = p.calls.filter(call => call.url.endsWith('/settings') && call.init?.method === 'POST').at(-1);
  assert.deepEqual(JSON.parse(disabled.init.body), {enabled: false, public_url: 'https://synthetic.ts.net'});
});

test('permission editing cannot implicitly submit the manual-token form', async () => {
  const p = await panel({enabled: true, public_url: 'https://synthetic.ts.net', sharing_enabled: true, connections: [], pending: []});
  const form = find(p.render(), node => node.props.id === 'http_enrollment');
  assert.equal(find(form, node => node.props.id === 'http_client'), null);
  assert.ok(find(form, node => node.type === 'button' && node.children.includes('Create agent token (90 days)')));
});
