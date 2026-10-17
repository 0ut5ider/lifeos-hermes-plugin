// ABOUTME: Checks release page controls against the Hermes SDK rendering and request contract.
// ABOUTME: Verifies preparation actions and review remain separate from program installation.
const assert = require('node:assert/strict');
const test = require('node:test');
const {find, findAll, loadDashboard, settle, text} = require('./support/dashboard_sdk.cjs');

const qualified = {label: 'v0.21.7', commit: '71d34bad1045610252eda02ee79549436896e784'};
const compatible = {format: 1, compatible: true, state: 'compatible', reasons: [], qualified: 'v0.21.7',
  supported: [qualified], dependencies: {add: ['tree-sitter==0.26.0'], conflicts: []},
  detected: {source: '/home/owner/.hermes/hermes-agent', commit: qualified.commit, version: 'v0.21.7',
    profile: '/home/owner/.hermes', interpreter: '/home/owner/.hermes/hermes-agent/venv/bin/python', python: '3.11.9'}};

async function page(installed, operations = [], compatibility = compatible, review = null) {
  const calls = [];
  const sdk = {
    fetchJSON: async (url, options) => {
      calls.push({url, options});
      if (url.endsWith('/installation')) return {installed};
      if (url.endsWith('/compatibility')) {
        if (compatibility instanceof Error) throw compatibility;
        return compatibility;
      }
      if (url.endsWith('/prepare')) return {identifier: 'a'.repeat(32), state: 'preparing'};
      if (url.endsWith('/review')) return {identifier: url.split('/').at(-2), version: '0.7.3', commit: 'c'.repeat(40),
        package_sha256: 'd'.repeat(64), restart_required: true, ...(review ?? {})};
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

test('compatible Hermes shows the detected identity and the packages installation adds', async () => {
  const ui = await page(false);
  const section = find(ui.render(), (node) => node.props.id === 'release_compatibility');
  assert.ok(section);
  const content = text(section);
  assert.match(content, /LifeOS can be installed on this Hermes installation\./);
  assert.match(content, /Detected Hermes: v0\.21\.7 \(commit 71d34bad1045\)/);
  assert.match(content, /Source: \/home\/owner\/\.hermes\/hermes-agent/);
  assert.match(content, /Installation adds these Python packages: tree-sitter==0\.26\.0/);
  assert.equal(ui.calls.filter((item) => item.url.endsWith('/compatibility')).length, 1);
  ui.cleanup();
});

test('incompatible Hermes lists every reason, affected files, and the qualified versions', async () => {
  const paths = Array.from({length: 50}, (_, index) => 'agent/file' + index + '.py');
  const ui = await page(false, [], {...compatible, compatible: false, state: 'unsupported_version', qualified: null,
    detected: {...compatible.detected, commit: 'f4795c922c2ef9eef244ea0fb886ad863dc452be', version: 'v0.21.4-588-gf4795c922'},
    reasons: [
      {code: 'unsupported_version', message: 'LifeOS has no qualified patch set for this Hermes version.'},
      {code: 'modified_files', message: 'Hermes source files differ from the qualified upstream version.', paths, count: 72},
    ]});
  const section = find(ui.render(), (node) => node.props.id === 'release_compatibility');
  const content = text(section);
  assert.match(content, /LifeOS can't be installed on this Hermes installation\./);
  assert.match(content, /LifeOS has no qualified patch set for this Hermes version\./);
  assert.match(content, /Hermes source files differ from the qualified upstream version\./);
  assert.match(content, /agent\/file0\.py/);
  assert.doesNotMatch(content, /agent\/file10\.py/);
  assert.match(content, /and 62 more/);
  assert.match(content, /Qualified Hermes versions: v0\.21\.7 \(commit 71d34bad1045\)/);
  assert.match(content, /Detected Hermes: v0\.21\.4-588-gf4795c922 \(commit f4795c922c2e\)/);
  assert.equal(findAll(section, (node) => node.type === 'li').length, 2);
  ui.cleanup();
});

test('check again repeats the read-only compatibility request', async () => {
  const ui = await page(false);
  await find(ui.render(), (node) => node.type === 'button' && node.children.includes('Check again')).props.onClick();
  const requests = ui.calls.filter((item) => item.url === '/api/plugins/lifeos-release-manager/compatibility');
  assert.equal(requests.length, 2);
  assert.equal(requests.every((item) => item.options === undefined), true);
  ui.cleanup();
});

test('an unavailable compatibility check is reported without blocking release status', async () => {
  const ui = await page(false, [], new Error('The Hermes compatibility check is unavailable'));
  const content = text(find(ui.render(), (node) => node.props.id === 'release_compatibility'));
  assert.match(content, /The Hermes compatibility check is unavailable/);
  assert.ok(find(ui.render(), (node) => node.type === 'button' && node.children.includes('Install LifeOS')));
  ui.cleanup();
});

test('a malformed compatibility response is reported instead of breaking the page', async () => {
  const ui = await page(false, [], {operations: []});
  const content = text(find(ui.render(), (node) => node.props.id === 'release_compatibility'));
  assert.match(content, /The Hermes compatibility check returned an unexpected result\./);
  ui.cleanup();
});

test('an installed host is reported as installed rather than incompatible', async () => {
  const ui = await page(true, [], {...compatible, compatible: false, installed: true, state: 'installed'});
  const content = text(find(ui.render(), (node) => node.props.id === 'release_compatibility'));
  assert.match(content, /LifeOS is installed on this Hermes installation\./);
  assert.doesNotMatch(content, /can't be installed/);
  ui.cleanup();
});

test('an incompatible host disables Install LifeOS and explains why', async () => {
  const ui = await page(false, [], {...compatible, compatible: false, state: 'unsupported_version',
    reasons: [{code: 'unsupported_version', message: 'LifeOS has no qualified patch set for this Hermes version.'}]});
  const button = find(ui.render(), (node) => node.type === 'button' && node.children.includes('Install LifeOS'));
  assert.equal(button.props.disabled, true);
  assert.ok(find(ui.render(), (node) => node.props.id === 'release_preparation_help' &&
    text(node).includes("LifeOS can't be installed on this Hermes installation")));
  ui.cleanup();
});

test('an in-place review lists the Hermes changes, packages, services, and tested scope before installation', async () => {
  const identifier = 'f'.repeat(32);
  const ui = await page(false, [{identifier, version: '0.8.0', state: 'ready'}], compatible, {in_place: {
    hermes: {label: 'v0.21.7', commit: qualified.commit, source: '/home/owner/.hermes/hermes-agent', modified: 69, added: 27,
      files: {modified: ['hermes_cli/plugins.py', 'run_agent.py'], added: ['hermes_cli/new_hook.py']}, update_hold: true},
    configuration: ['plugins.enabled', 'plugins.entries'], update: null, known_conflicts: [],
    packages: ['tree-sitter==0.26.0', 'tree-sitter-bash==0.25.1'],
    services: {restarted: ['gateway'], created: ['dashboard', 'pulse'], replaced: [{pid: 4321, command: 'hermes', role: 'dashboard'}]},
    tested_scope: 'Qualified on a single-profile Linux Git installation of Hermes v0.21.7.'}});
  await find(ui.render(), (node) => node.type === 'button' && node.children.includes('Review release')).props.onClick();
  const content = text(find(ui.render(), (node) => node.props.className === 'lifeos-review'));
  assert.match(content, /Hermes v0\.21\.7 \(commit 71d34bad1045\): 69 files changed and 27 files added in \/home\/owner\/\.hermes\/hermes-agent/);
  assert.match(content, /Hermes updates stay held while LifeOS is installed/);
  assert.match(content, /Python packages added: tree-sitter==0\.26\.0, tree-sitter-bash==0\.25\.1/);
  assert.match(content, /Services that restart: gateway/);
  assert.match(content, /User services created: dashboard, pulse/);
  assert.match(content, /Stops the hand-started dashboard \(process 4321\); its new user service replaces it/);
  assert.match(content, /Qualified on a single-profile Linux Git installation of Hermes v0\.21\.7\./);
  const review = find(ui.render(), (node) => node.props.className === 'lifeos-review');
  const lists = findAll(review, (node) => node.type === 'details');
  assert.deepEqual(lists.map((node) => text(find(node, (child) => child.type === 'summary'))),
    ['Changed Hermes files (2)', 'Added Hermes files (1)', 'Configuration keys LifeOS changes (2)']);
  assert.ok(lists.every((node) => !node.props.open), 'Long lists start collapsed');
  assert.match(text(lists[0]), /hermes_cli\/plugins\.py.*run_agent\.py/);
  assert.match(text(lists[2]), /plugins\.enabled.*plugins\.entries/);
  assert.match(content, /Known conflicts: none reported for Hermes v0\.21\.7\./);
  ui.cleanup();
});

test('an in-place update review shows the change from the installed release and the known conflicts', async () => {
  const identifier = 'e'.repeat(32);
  const ui = await page(true, [{identifier, version: '0.8.1', state: 'ready'}], {...compatible, installed: true}, {in_place: {
    hermes: {label: 'v0.21.7', commit: qualified.commit, source: '/home/owner/.hermes/hermes-agent', modified: 1, added: 1,
      files: {modified: ['hermes_cli/plugins.py'], added: ['hermes_cli/new_hook.py']}, update_hold: true},
    configuration: [], known_conflicts: ['The example-relay plugin replaces the delivery hook.'],
    update: {added: ['hermes_cli/new_hook.py'], changed: ['hermes_cli/plugins.py'], restored: ['run_agent.py', 'tools/x.py']},
    packages: [], services: {restarted: ['gateway'], created: [], replaced: []},
    tested_scope: 'Qualified on a single-profile Linux Git installation of Hermes v0.21.7.'}});
  await find(ui.render(), (node) => node.type === 'button' && node.children.includes('Review release')).props.onClick();
  const review = find(ui.render(), (node) => node.props.className === 'lifeos-review');
  const content = text(review);
  assert.match(content, /Compared with the installed release: 1 Hermes files change, 1 are added, and 2 return to their original content\./);
  const summaries = findAll(review, (node) => node.type === 'summary').map(text);
  assert.ok(summaries.includes('Files that return to their original content (2)'));
  assert.match(content, /Configuration keys LifeOS changes: none/);
  assert.match(content, /Known conflicts:.*The example-relay plugin replaces the delivery hook\./);
  ui.cleanup();
});

test('a managed runtime shows the move to the stock Hermes installation', async () => {
  const ui = await page(true, [], {...compatible, transition: true});
  const content = text(find(ui.render(), (node) => node.props.id === 'release_compatibility'));
  assert.match(content, /moves it to your Hermes installation at \/home\/owner\/\.hermes\/hermes-agent/);
  const button = find(ui.render(), (node) => node.type === 'button' && node.children.includes('Update LifeOS'));
  assert.equal(button.props.disabled, false);
  ui.cleanup();
});
