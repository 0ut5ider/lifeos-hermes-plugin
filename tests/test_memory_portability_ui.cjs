// ABOUTME: Exercises import review decisions and authenticated failures through the dashboard SDK.
// ABOUTME: Checks source provenance, explicit publication, and private draft removal after refusal.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

function find(node, match) {
  if (!node || typeof node !== 'object') return null;
  if (match(node)) return node;
  for (const child of node.children ?? []) { const result = find(child, match); if (result) return result; }
  return null;
}

async function panel(respond, name = 'MemoryImportReview') {
  let states = [], index = 0, root, mounted = false;
  const calls = [];
  const sdk = { React: { createElement(type, props, ...children) { return { type, props: props ?? {}, children: children.flat() }; } },
    hooks: { useState(value) { const slot = index++; if (!(slot in states)) states[slot] = value;
      return [states[slot], value => { states[slot] = typeof value === 'function' ? value(states[slot]) : value; }]; },
    useEffect() {} },
    fetchJSON(url, options) { calls.push({ url, options });
      if (url.endsWith('/memory')) return Promise.resolve({ state: 'configured', remaining_gates: {} });
      return Promise.resolve().then(() => respond(url, JSON.parse(options.body))); } };
  const bundle = fs.readFileSync(path.join(__dirname, '../lifeos_hook_bridge/dashboard/dist/index.js'), 'utf8');
  vm.runInNewContext(bundle, { window: { __HERMES_PLUGIN_SDK__: sdk,
    __HERMES_PLUGINS__: { register(_name, component) { root = component; } } } });
  const preferences = find(root(), node => typeof node.type === 'function' && node.type.name === 'MemoryPreferences');
  sdk.hooks.useEffect = callback => { if (!mounted) { mounted = true; callback(); } };
  states = []; index = 0; preferences.type(); await new Promise(setImmediate);
  index = 0;
  const component = find(preferences.type(), node => typeof node.type === 'function' && node.type.name === name);
  assert.ok(component, 'The configured owner page includes ' + name);
  states = [];
  const render = () => { index = 0; return component.type(); };
  return { render, calls };
}

const review = { installed: '/synthetic/native', principal: 'owner', signature: 'review', readers: {},
  source_origin: { label: 'Synthetic source host' }, sources: [{ path: 'memories/MEMORY.md', status: 'present',
    chunks: [{ id: 'chunk', content: 'Synthetic <script>source</script> fact.', exact_native_matches: [],
      retired_claim: false, disposition: 'review' }] }] };

test('import shows source provenance and never publishes before plan approval', async () => {
  let decision;
  const p = await panel((url, body) => {
    if (url.endsWith('/preview')) return review;
    if (url.endsWith('/snapshot')) return { identifier: 'a'.repeat(32), snapshot_signature: 'b'.repeat(64) };
    if (url.endsWith('/plan')) { decision = body.decisions[0]; return { signature: 'plan', items: [{ ...decision,
      destination: 'LIFEOS/MEMORY/KNOWLEDGE/Research/synthetic.md', transformation: { published: decision.content } }] }; }
    if (url.endsWith('/apply')) return { state: 'published', required_items_verified: true,
      items: [{ ...decision, verified: true, receipt: { reference: { id: 'saved', revision: 1 } } }] };
    throw new Error('Unexpected request');
  });
  await find(p.render(), node => node.type === 'button' && node.children.includes('Review Hermes memory')).props.onClick();
  assert.ok(JSON.stringify(p.render()).includes('Synthetic source host'));
  assert.equal(p.calls.filter(call => call.url.endsWith('/apply')).length, 0);
  find(p.render(), node => node.type === 'select' && node.props.value === 'pending').props.onChange({ target: { value: 'import' } });
  find(p.render(), node => node.props.id === 'import_chunk_project').props.onChange({ target: { value: 'lab' } });
  await find(p.render(), node => node.type === 'button' && node.children.includes('Review publication plan')).props.onClick();
  assert.equal(decision.project, 'lab'); assert.equal(decision.required, true);
  assert.equal(p.calls.filter(call => call.url.endsWith('/apply')).length, 0);
  await find(p.render(), node => node.type === 'button' && node.children.includes('Apply reviewed import')).props.onClick();
  assert.ok(JSON.stringify(p.render()).includes('revision 1'));
  assert.equal(find(p.render(), node => node.type === 'script'), null);
});

test('an authorization refusal clears private review text and approval controls', async () => {
  let denied = false;
  const p = await panel(url => {
    if (denied) throw new Error('Authentication required');
    if (url.endsWith('/preview')) return review;
    return { identifier: 'a'.repeat(32), snapshot_signature: 'b'.repeat(64) };
  });
  const button = () => find(p.render(), node => node.type === 'button' && node.children.includes('Review Hermes memory'));
  await button().props.onClick();
  assert.ok(JSON.stringify(p.render()).includes('Synthetic <script>source</script> fact.'));
  denied = true; await button().props.onClick();
  assert.ok(!JSON.stringify(p.render()).includes('Synthetic <script>source</script> fact.'));
  assert.equal(find(p.render(), node => node.children.includes('Apply reviewed import')), null);
});

test('reverse export shows capacity and retains every item until the owner chooses', async () => {
  let planned;
  const p = await panel((url, body) => {
    if (url.endsWith('/preview')) return { signature: 'review', settings: { memory_char_limit: 80, user_char_limit: 40 },
      items: [{ id: 'lifeos:one', content: 'Synthetic reverse fact.', category: 'project', project: 'lab',
        reference: { id: 'one', revision: 2 }, origin: { kind: 'explicit' }, retired_claim: false, quarantined: false }] };
    if (url.endsWith('/snapshot')) return { identifier: 'a'.repeat(32), signature: 'b'.repeat(64) };
    if (url.endsWith('/plan')) { planned = body.decisions; return { signature: 'plan', items: planned, files: { 'MEMORY.md': '', 'USER.md': '' },
      limits: { 'MEMORY.md': 80, 'USER.md': 40 }, ready_for_return: false }; }
    throw new Error('Unexpected request');
  }, 'MemoryExportReview');
  await find(p.render(), node => node.type === 'button' && node.children.includes('Review reverse export')).props.onClick();
  assert.ok(JSON.stringify(p.render()).includes('80'));
  assert.ok(JSON.stringify(p.render()).includes('revision 2'));
  await find(p.render(), node => node.type === 'button' && node.children.includes('Review export plan')).props.onClick();
  assert.equal(planned[0].action, 'retain'); assert.equal(planned[0].required, true);
  assert.equal(p.calls.filter(call => call.url.endsWith('/apply')).length, 0);
});

test('published import queues ownership review without applying the cutover', async () => {
  let decision;
  const p = await panel((url, body) => {
    if (url.endsWith('/preview')) return review;
    if (url.endsWith('/snapshot')) return { identifier: 'a'.repeat(32), snapshot_signature: 'b'.repeat(64) };
    if (url.endsWith('/plan')) { decision = body.decisions[0]; return { signature: 'c'.repeat(64), items: [decision] }; }
    if (url.endsWith('/import/apply')) return { state: 'published', required_items_verified: true, items: [] };
    if (url.endsWith('/memory-workflows')) return { identifier: 'd'.repeat(32) };
    throw new Error('Unexpected request: ' + url);
  });
  await find(p.render(), n => n.children.includes('Review Hermes memory')).props.onClick();
  find(p.render(), n => n.type === 'select' && n.props.value === 'pending').props.onChange({ target: { value: 'import' } });
  find(p.render(), n => n.props.id === 'import_chunk_project').props.onChange({ target: { value: 'lab' } });
  await find(p.render(), n => n.children.includes('Review publication plan')).props.onClick();
  await find(p.render(), n => n.children.includes('Apply reviewed import')).props.onClick();
  const button = find(p.render(), n => n.children.includes('Prepare LifeOS ownership activation'));
  assert.ok(button);
  await button.props.onClick();
  const call = p.calls.find(c => c.url.endsWith('/memory-workflows'));
  assert.equal(JSON.parse(call.options.body).kind, 'activation');
  assert.equal(JSON.parse(call.options.body).plan_signature, 'c'.repeat(64));
  assert.equal(p.calls.filter(c => c.url.includes('/memory-workflows/')).length, 0);
});
