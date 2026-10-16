// ABOUTME: Checks release page controls against the Hermes SDK rendering and request contract.
// ABOUTME: Verifies preparation actions and review remain separate from program installation.
const assert = require('node:assert/strict');
const test = require('node:test');
const {find, loadDashboard, settle} = require('./support/dashboard_sdk.cjs');

async function page(installed, operations = []) {
  const calls = [];
  const sdk = {
    fetchJSON: async (url, options) => {
      calls.push({url, options});
      if (url.endsWith('/installation')) return {installed};
      if (url.endsWith('/prepare')) return {identifier: 'a'.repeat(32), state: 'preparing'};
      if (url.endsWith('/review')) return {identifier: url.split('/').at(-2), version: '0.7.3', commit: 'c'.repeat(40),
        package_sha256: 'd'.repeat(64), restart_required: true};
      if (url.endsWith('/apply')) return {state: 'queued-apply'};
      return {operations};
    },
  };
  const app = loadDashboard('releases', {...sdk, globals: {setInterval: () => 1, clearInterval: () => {}}});
  const render = app.mount();
  await settle();
  return {calls, render, cleanup: app.unmount};
}

test('fresh page offers Install LifeOS and queues preparation without applying programs', async () => {
  const ui = await page(false);
  const tree = ui.render();
  const button = find(tree, (node) => node.type === 'button' && node.children.includes('Install LifeOS'));
  assert.ok(button);
  assert.equal(button.props.disabled, false);
  await button.props.onClick();
  const call = ui.calls.find((item) => item.url.endsWith('/prepare'));
  assert.equal(call.options.method, 'POST');
  assert.deepEqual(JSON.parse(call.options.body), {intent: 'install', name: 'User', assistant: 'Hermes'});
  assert.equal(ui.calls.some((item) => item.url.endsWith('/apply')), false);
  ui.cleanup();
});

test('installed page offers both update actions for the complete integration', async () => {
  for (const [label, intent] of [['Update LifeOS', 'update'], ['Update plugin', 'plugin']]) {
    const ui = await page(true);
    const tree = ui.render();
    const button = find(tree, (node) => node.type === 'button' && node.children.includes(label));
    assert.ok(button);
    assert.equal(button.props.disabled, false);
    await button.props.onClick();
    const call = ui.calls.find((item) => item.url.endsWith('/prepare'));
    assert.equal(JSON.parse(call.options.body).intent, intent);
    assert.equal(ui.calls.some((item) => item.url.endsWith('/apply')), false);
    ui.cleanup();
  }
});

test('recovery blocks preparation and each operation has a visible identifier', async () => {
  const identifier = 'b'.repeat(32);
  const ui = await page(true, [{identifier, version: '0.4.1', state: 'recovery_required'}]);
  const tree = ui.render();
  for (const label of ['Update LifeOS', 'Update plugin']) {
    const button = find(tree, (node) => node.type === 'button' && node.children.includes(label));
    assert.equal(button.props.disabled, true);
  }
  assert.ok(find(tree, (node) => node.children.includes('Operation: ' + identifier)));
  ui.cleanup();
});

test('a ready release is reviewed before its separate installation request', async () => {
  const identifier = 'e'.repeat(32);
  const ui = await page(true, [{identifier, version: '0.7.3', state: 'ready'}]);
  await find(ui.render(), (node) => node.type === 'button' && node.children.includes('Review release')).props.onClick();
  const operation = '/api/plugins/lifeos-release-manager/operations/' + identifier;
  const review = ui.calls.find((item) => item.url === operation + '/review');
  assert.equal(JSON.stringify(review.options), JSON.stringify({method: 'POST'}));
  assert.equal(ui.calls.some((item) => item.url.endsWith('/apply')), false);
  assert.ok(find(ui.render(), (node) => node.type === 'p' && node.children.includes('Package SHA-256: ' + 'd'.repeat(64))));
  await find(ui.render(), (node) => node.type === 'button' && node.children.includes('Install this release')).props.onClick();
  const apply = ui.calls.find((item) => item.url === operation + '/apply');
  assert.equal(JSON.stringify(apply.options), JSON.stringify({method: 'POST'}));
  assert.equal(find(ui.render(), (node) => node.type === 'button' && node.children.includes('Install this release')), null);
  assert.ok(find(ui.render(), (node) => node.props.role === 'status' &&
    node.children.includes('Release operation started. Hermes can restart. Refresh this page to check the result.')));
  ui.cleanup();
});
