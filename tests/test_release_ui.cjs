// ABOUTME: Checks release page controls against the Hermes SDK rendering and request contract.
// ABOUTME: Verifies preparation actions and review remain separate from program installation.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

function nodes(tree) {
  if (Array.isArray(tree)) return tree.flatMap(nodes);
  if (!tree || typeof tree !== 'object') return [];
  return [tree, ...(tree.children || []).flatMap(nodes)];
}

async function page(installed, operations = []) {
  const states = [];
  let index = 0;
  let component;
  const calls = [];
  const effects = [];
  const sdk = {
    React: {createElement: (type, props, ...children) => ({type, props, children})},
    hooks: {
      useState: (initial) => {
        const key = index++;
        if (!(key in states)) states[key] = initial;
        return [states[key], (value) => {states[key] = value;}];
      },
      useEffect: (effect) => {effects.push(effect);},
    },
    fetchJSON: async (url, options) => {
      calls.push({url, options});
      if (url.endsWith('/installation')) return {installed};
      if (url.endsWith('/prepare')) return {identifier: 'a'.repeat(32), state: 'preparing'};
      return {operations};
    },
  };
  const source = fs.readFileSync(path.join(__dirname, '../optional/lifeos_release_manager/dashboard/dist/index.js'), 'utf8');
  vm.runInNewContext(source, {window: {__HERMES_PLUGIN_SDK__: sdk,
    __HERMES_PLUGINS__: {register: (name, entry) => {component = entry;}}},
    setInterval: () => 1, clearInterval: () => {}});
  function render() {index = 0; return component();}
  render();
  const cleanup = effects[0]();
  await new Promise((resolve) => setImmediate(resolve));
  return {calls, render, cleanup};
}

test('fresh page offers Install LifeOS and queues preparation without applying programs', async () => {
  const ui = await page(false);
  const tree = ui.render();
  const button = nodes(tree).find((node) => node.type === 'button' && node.children.includes('Install LifeOS'));
  assert.ok(button);
  assert.equal(button.props.disabled, false);
  await button.props.onClick();
  const call = ui.calls.find((item) => item.url.endsWith('/prepare'));
  assert.equal(call.options.method, 'POST');
  assert.equal(JSON.parse(call.options.body).intent, 'install');
  assert.equal(ui.calls.some((item) => item.url.endsWith('/apply')), false);
  ui.cleanup();
});

test('installed page offers both update actions for the complete integration', async () => {
  for (const [label, intent] of [['Update LifeOS', 'update'], ['Update plugin', 'plugin']]) {
    const ui = await page(true);
    const tree = ui.render();
    const button = nodes(tree).find((node) => node.type === 'button' && node.children.includes(label));
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
    const button = nodes(tree).find((node) => node.type === 'button' && node.children.includes(label));
    assert.equal(button.props.disabled, true);
  }
  assert.ok(nodes(tree).some((node) => node.children.includes('Operation: ' + identifier)));
  ui.cleanup();
});
