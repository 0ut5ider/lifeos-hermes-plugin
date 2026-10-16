// ABOUTME: Checks that each standalone plugin provides its own scoped setup stylesheet.
// ABOUTME: Verifies complete setup navigation and styles without relying on host utility generation.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');
const dashboards = ['lifeos_hook_bridge/dashboard', 'optional/lifeos_release_manager/dashboard'];
for (const dashboard of dashboards) {
  test(dashboard + ' declares a bundled, scoped, accessible stylesheet', () => {
    const root = path.join(__dirname, '..', dashboard);
    const manifest = JSON.parse(fs.readFileSync(path.join(root, 'manifest.json'), 'utf8'));
    assert.equal(manifest.css, 'dist/style.css', 'The host must load plugin CSS from the manifest');
    const css = fs.readFileSync(path.join(root, manifest.css), 'utf8');
    for (const selector of ['.lifeos-setup', 'button', ':disabled', ':focus-visible', 'label', 'summary', '@media']) {
      assert.ok(css.includes(selector), 'Missing setup style: ' + selector);
    }
    assert.ok(!css.includes('@import'), 'The standalone plugin must not require external stylesheets');
  });
}
test('Bridge and release pages expose labelled navigation and scoped roots', () => {
  for (const [dashboard, expected] of [[dashboards[0], ['Lasting memory', 'Agent access', 'Installation']],
    [dashboards[1], ['Prepare a release', 'Release operations', 'Memory and model settings']]]) {
    let component;
    const sdk = {React: {createElement: (type, props, ...children) => ({type, props: props ?? {}, children: children.flat()})},
      hooks: {useState: initial => [initial, () => {}], useEffect() {}}};
    vm.runInNewContext(fs.readFileSync(path.join(__dirname, '..', dashboard, 'dist/index.js'), 'utf8'), {
      window: {__HERMES_PLUGIN_SDK__: sdk, __HERMES_PLUGINS__: {register(_name, view) {component = view;}}}});
    const tree = component();
    assert.ok(tree.props.className.includes('lifeos-setup'));
    const all = node => !node || typeof node !== 'object' ? [] : [node, ...node.children.flatMap(all)];
    const nav = all(tree).find(node => node.type === 'nav' && node.props['aria-label']);
    assert.ok(nav, 'Setup must have labelled section navigation');
    for (const label of expected) assert.ok(JSON.stringify(nav).includes(label), 'Missing navigation: ' + label);
  }
});
