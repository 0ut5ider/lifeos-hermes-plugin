// ABOUTME: Tests the dashboard controls that prepare, list, and remove fresh LifeOS stores.
// ABOUTME: Runs the shipped bundle with a recording SDK and checks requests and visible states.
const assert = require('node:assert/strict');
const test = require('node:test');
const { component, find, findAll, loadDashboard, plain, settle, text } = require('./support/dashboard_sdk.cjs');

async function controls(listing, selection, refusal) {
  const calls = [];
  let current = listing;
  let selected = selection || { configured: false, home: '/home/owner', running_home: '/home/owner', job: { state: 'none' } };
  const sdk = {
    fetchJSON(url, init) {
      calls.push({ url, init });
      if (refusal && init?.method) return Promise.reject(new Error(refusal));
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
      if (url.endsWith('/installation/selection') && init?.method === 'POST') {
        selected = { ...selected, job: { state: 'queued' } };
        return Promise.resolve({ state: 'queued', job: '/state/selection-1' });
      }
      if (url.endsWith('/installation/selection/return')) {
        selected = { ...selected, job: { state: 'queued' } };
        return Promise.resolve({ state: 'queued', job: '/state/selection-2' });
      }
      if (url.endsWith('/installation/selection')) return Promise.resolve(selected);
      return Promise.resolve({ state: 'not_configured', remaining_gates: {}, connections: [] });
    },
  };
  const app = loadDashboard('bridge', { ...sdk, window: { crypto: require('node:crypto').webcrypto } });
  const render = app.mount(component(app.preview(), 'FreshStores'));
  await settle();
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
  await settle(); await settle();
  const request = page.calls.find(call => call.url.endsWith('/memory/fresh/start'));
  assert.deepEqual(JSON.parse(request.init.body), { principal_name: 'Adrian', assistant_name: 'Cerebo' });
  assert.match(text(page.render()), /Adrian and Cerebo: preparing/);
});

test('remove is offered for every store and confirms by identifier', async () => {
  const page = await controls(listing);
  const buttons = findAll(page.render(), node => node.type === 'button' && text(node).startsWith('Remove'));
  assert.equal(buttons.length, 3);
  buttons[1].props.onClick();
  await settle(); await settle();
  const removal = page.calls.find(call => call.init?.method === 'DELETE');
  assert.ok(removal.url.endsWith('/memory/fresh/stores/' + 'b'.repeat(32)));
  assert.doesNotMatch(text(page.render()), /interrupted/);
});

test('while an installation operation runs the start control is disabled', async () => {
  const page = await controls({ busy: true, stores: [] });
  const button = find(page.render(), n => n.type === 'button' && n.props.type === 'submit' && text(n).includes('Prepare'));
  assert.equal(button.props.disabled, true);
});

test('a reviewed store can be selected and a selected store offers return', async () => {
  const page = await controls(listing);
  const use = find(page.render(), node => node.type === 'button' && text(node) === 'Use ' + 'a'.repeat(8));
  assert.ok(use, 'A reviewed store must offer selection');
  await use.props.onClick();
  await settle();
  const request = page.calls.find(call => call.url.endsWith('/installation/selection') && call.init?.method === 'POST');
  assert.deepEqual(JSON.parse(request.init.body), { store: 'a'.repeat(32) });
  assert.ok(find(page.render(), node => node.props?.role === 'status' && text(node).includes('queued')));

  const home = '/home/owner/.local/state/lifeos-hook-bridge/fresh-stores/p/' + 'a'.repeat(32) + '/home';
  const chosen = await controls(listing, { configured: true, home, running_home: home, job: { state: 'applied' } });
  const view = chosen.render();
  assert.ok(find(view, node => node.type === 'p' && text(node).includes('This profile uses the fresh store ' + 'a'.repeat(8))));
  assert.equal(find(view, node => node.type === 'button' && text(node) === 'Use ' + 'a'.repeat(8)), null);
  const back = find(view, node => node.type === 'button' && text(node) === 'Return to the previous installation');
  assert.ok(back);
  await back.props.onClick();
  const returned = chosen.calls.find(call => call.url.endsWith('/installation/selection/return'));
  assert.equal(returned.init.method, 'POST');
  assert.equal(returned.init.body, undefined);
});

test('an interrupted selection offers recovery', async () => {
  const page = await controls(listing, { configured: false, home: '/home/owner', running_home: '/home/owner',
    job: { state: 'interrupted', error: 'synthetic stop' } });
  const recover = find(page.render(), node => node.type === 'button' && text(node) === 'Recover interrupted selection');
  assert.ok(recover);
  assert.equal(find(page.render(), node => node.type === 'button' && text(node) === 'Use ' + 'a'.repeat(8)), null);
});

const notice = (view, message) => find(view, node => node.type === 'p' && node.props.role === 'status' && text(node) === message);
const action = (view, label) => find(view, node => node.type === 'button' && text(node) === label);

test('each store change reports its notice and reloads both statuses', async () => {
  const listed = { busy: false, stores: listing.stores.slice(0, 1) };
  const interrupted = { configured: false, home: '/home/owner', running_home: '/home/owner', job: { state: 'interrupted' } };
  const home = '/home/owner/.local/state/lifeos-hook-bridge/fresh-stores/p/' + 'a'.repeat(32) + '/home';
  for (const change of [
    { selection: undefined, label: 'Use ' + 'a'.repeat(8), path: '/installation/selection', body: { store: 'a'.repeat(32) },
      done: 'Selection started. Hermes restarts with the fresh store when it finishes.' },
    { selection: { configured: true, home, running_home: home, job: { state: 'applied' } }, label: 'Return to the previous installation',
      path: '/installation/selection/return', done: 'Return started. Hermes restarts when it finishes.' },
    { selection: interrupted, label: 'Recover interrupted selection', path: '/installation/selection/recover', done: 'Recovery started.' },
    { selection: undefined, label: 'Remove ' + 'a'.repeat(8), path: '/memory/fresh/stores/' + 'a'.repeat(32), method: 'DELETE',
      done: 'Store removed. The current installation is unchanged.' },
  ]) {
    const page = await controls(listed, change.selection);
    const before = page.calls.length;
    const pending = action(page.render(), change.label).props.onClick();
    assert.equal(action(page.render(), change.label)?.props.disabled ?? true, true, change.label + ' must wait for the request');
    await pending;
    const after = page.calls.slice(before).map(call => ({ path: call.url.replace('/api/plugins/lifeos-hook-bridge', ''), init: call.init && plain(call.init) }));
    const request = change.body === undefined ? { method: change.method ?? 'POST' } :
      { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(change.body) };
    assert.deepEqual(after, [{ path: change.path, init: request }, { path: '/memory/fresh/status', init: undefined },
      { path: '/installation/selection', init: undefined }]);
    assert.ok(notice(page.render(), change.done), change.label);
  }
  const page = await controls({ busy: false, stores: [] });
  find(page.render(), n => n.props.id === 'fresh_principal').props.onChange({ target: { value: 'Adrian' } });
  find(page.render(), n => n.props.id === 'fresh_assistant').props.onChange({ target: { value: 'Cerebo' } });
  const before = page.calls.length;
  await find(page.render(), n => n.props.id === 'fresh_store_start').props.onSubmit({ preventDefault() {} });
  const start = page.calls[before];
  assert.equal(start.init.method, 'POST');
  assert.equal(JSON.stringify(start.init.headers), JSON.stringify({ 'Content-Type': 'application/json' }));
  assert.deepEqual(page.calls.slice(before + 1).map(call => call.url.replace('/api/plugins/lifeos-hook-bridge', '')),
    ['/memory/fresh/status', '/installation/selection']);
  assert.ok(notice(page.render(), 'Preparation started. It continues if this page closes.'));
});

test('a refused store change shows the reason, skips reload, and enables controls', async () => {
  const page = await controls(listing, undefined, 'Synthetic store refusal');
  const before = page.calls.length;
  await action(page.render(), 'Remove ' + 'a'.repeat(8)).props.onClick();
  await action(page.render(), 'Use ' + 'a'.repeat(8)).props.onClick();
  find(page.render(), n => n.props.id === 'fresh_principal').props.onChange({ target: { value: 'Adrian' } });
  await find(page.render(), n => n.props.id === 'fresh_store_start').props.onSubmit({ preventDefault() {} });
  assert.deepEqual(page.calls.slice(before).map(call => call.init.method), ['DELETE', 'POST', 'POST']);
  assert.ok(notice(page.render(), 'Synthetic store refusal'));
  assert.equal(action(page.render(), 'Remove ' + 'a'.repeat(8)).props.disabled, false);
  assert.equal(action(page.render(), 'Use ' + 'a'.repeat(8)).props.disabled, false);
});
