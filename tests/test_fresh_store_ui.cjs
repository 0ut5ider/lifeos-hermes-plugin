// ABOUTME: Tests the dashboard controls that prepare, list, and remove fresh LifeOS stores.
// ABOUTME: Runs the shipped bundle with a recording SDK and checks requests and visible states.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');
const bundle = fs.readFileSync(path.join(__dirname, '../lifeos_hook_bridge/dashboard/dist/index.js'), 'utf8');

function find(node, match) {
  if (!node || typeof node !== 'object') return null;
  if (match(node)) return node;
  for (const child of node.children || []) { const result = find(child, match); if (result) return result; }
  return null;
}
function text(node) {
  if (typeof node === 'string') return node;
  if (!node || typeof node !== 'object') return '';
  return (node.children || []).map(text).join('');
}

async function controls(listing) {
  const state = [], calls = []; let index = 0, mounted = false, root;
  let current = listing;
  const sdk = {
    React: { createElement: (type, props, ...children) => ({ type, props: props || {}, children: children.flat() }) },
    hooks: {
      useState(value) { const slot = index++; if (!(slot in state)) state[slot] = value;
        return [state[slot], value => { state[slot] = typeof value === 'function' ? value(state[slot]) : value; }]; },
      useEffect() {},
    },
    fetchJSON(url, init) {
      calls.push({ url, init });
      if (url.endsWith('/memory/fresh/start')) {
        current = { busy: true, stores: [{ identifier: 'c'.repeat(32), state: 'preparing',
          names: { principal: 'Adrian', assistant: 'Cerebo' } }, ...current.stores] };
        return Promise.resolve({ identifier: 'c'.repeat(32), state: 'preparing' });
      }
      if (init?.method === 'DELETE') {
        const identifier = url.split('/').pop();
        current = { ...current, stores: current.stores.filter(row => row.identifier !== identifier) };
        return Promise.resolve({ identifier, removed: true });
      }
      if (url.endsWith('/memory/fresh/status')) return Promise.resolve(current);
      return Promise.resolve({ state: 'not_configured', remaining_gates: {}, connections: [] });
    },
  };
  vm.runInNewContext(bundle, { window: { crypto: require('node:crypto').webcrypto, __HERMES_PLUGIN_SDK__: sdk,
    __HERMES_PLUGINS__: { register(_name, view) { root = view; } } }, console });
  const component = find(root(), node => typeof node.type === 'function' && node.type.name === 'FreshStores');
  assert.ok(component, 'The LifeOS page must include the fresh store controls');
  state.length = 0;
  sdk.hooks.useEffect = callback => { if (!mounted) { mounted = true; callback(); } };
  const render = () => { index = 0; return component.type(); };
  render(); await new Promise(setImmediate);
  return { render, calls };
}

const listing = { busy: false, stores: [
  { identifier: 'a'.repeat(32), state: 'review', names: { principal: 'Adrian', assistant: 'Cerebo' }, active_facts: 0,
    activation_ready: false, source: { upstream_commit: '5e2f2e8' }, retained_installation: '/home/user/.claude' },
  { identifier: 'b'.repeat(32), state: 'interrupted', names: { principal: 'Adrian', assistant: 'Cerebo' } },
  { identifier: 'd'.repeat(32), state: 'failed', names: { principal: 'Adrian', assistant: 'Cerebo' },
    reason: 'Fresh store preparation requires a verified native candidate' },
] };

test('each store shows its state, names, and the reason for a failure', async () => {
  const view = (await controls(listing)).render();
  const all = text(view);
  assert.match(all, /Adrian and Cerebo: ready for review, 0 active facts/);
  assert.match(all, /interrupted/);
  assert.match(all, /failed: Fresh store preparation requires a verified native candidate/);
  assert.match(all, /The current installation stays selected/);
});

test('starting a store sends only the two names and shows the running preparation', async () => {
  const page = await controls({ busy: false, stores: [] });
  find(page.render(), n => n.type === 'input' && n.props.id === 'fresh_principal').props.onChange({ target: { value: 'Adrian' } });
  find(page.render(), n => n.type === 'input' && n.props.id === 'fresh_assistant').props.onChange({ target: { value: 'Cerebo' } });
  find(page.render(), n => n.type === 'form' && n.props.id === 'fresh_store_start').props.onSubmit({ preventDefault() {} });
  await new Promise(setImmediate); await new Promise(setImmediate);
  const request = page.calls.find(call => call.url.endsWith('/memory/fresh/start'));
  assert.deepEqual(JSON.parse(request.init.body), { principal_name: 'Adrian', assistant_name: 'Cerebo' });
  assert.match(text(page.render()), /Adrian and Cerebo: preparing/);
});

test('remove is offered for every store and confirms by identifier', async () => {
  const page = await controls(listing);
  const buttons = [];
  (function walk(node) { if (!node || typeof node !== 'object') return;
    if (node.type === 'button' && text(node).startsWith('Remove')) buttons.push(node);
    (node.children || []).forEach(walk); })(page.render());
  assert.equal(buttons.length, 3);
  buttons[1].props.onClick();
  await new Promise(setImmediate); await new Promise(setImmediate);
  const removal = page.calls.find(call => call.init?.method === 'DELETE');
  assert.ok(removal.url.endsWith('/memory/fresh/stores/' + 'b'.repeat(32)));
  assert.doesNotMatch(text(page.render()), /interrupted/);
});

test('while an installation operation runs the start control is disabled', async () => {
  const page = await controls({ busy: true, stores: [] });
  const button = find(page.render(), n => n.type === 'button' && n.props.type === 'submit' && text(n).includes('Prepare'));
  assert.equal(button.props.disabled, true);
});
