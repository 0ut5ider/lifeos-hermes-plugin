// ABOUTME: Checks that each standalone plugin provides its own scoped setup stylesheet.
// ABOUTME: Verifies complete setup navigation and styles without relying on host utility generation.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const {find, loadDashboard} = require('./support/dashboard_sdk.cjs');
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
  for (const [bundle, expected] of [['bridge', ['Lasting memory', 'Agent access', 'Installation']],
    ['releases', ['Prepare a release', 'Release operations', 'Memory and model settings']]]) {
    const tree = loadDashboard(bundle).preview();
    assert.ok(tree.props.className.includes('lifeos-setup'));
    const nav = find(tree, node => node.type === 'nav' && node.props['aria-label']);
    assert.ok(nav, 'Setup must have labelled section navigation');
    for (const label of expected) assert.ok(JSON.stringify(nav).includes(label), 'Missing navigation: ' + label);
  }
});
