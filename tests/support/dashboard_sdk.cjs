// ABOUTME: Loads a shipped dashboard bundle against a minimal Hermes SDK for Node component tests.
// ABOUTME: Each load has its own hook state; it is a rendering contract fixture, not React or a browser.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const bundles = {
  bridge: path.join(__dirname, '../../lifeos_hook_bridge/dashboard/dist/index.js'),
  releases: path.join(__dirname, '../../optional/lifeos_release_manager/dashboard/dist/index.js'),
};

function find(node, match) {
  if (!node || typeof node !== 'object') return null;
  if (match(node)) return node;
  for (const child of node.children) {
    const result = find(child, match);
    if (result) return result;
  }
  return null;
}

function findAll(node, match) {
  if (!node || typeof node !== 'object') return [];
  return [...(match(node) ? [node] : []), ...node.children.flatMap((child) => findAll(child, match))];
}

function text(node) {
  if (typeof node === 'string') return node;
  if (!node || typeof node !== 'object') return '';
  return node.children.map(text).join('');
}

function component(tree, name) {
  const element = find(tree, (node) => typeof node.type === 'function' && node.type.name === name);
  assert.ok(element, 'The rendered page must include ' + name);
  return element.type;
}

// Copies a value built inside the bundle realm so strict deep equality compares only its data.
function plain(value) {
  return JSON.parse(JSON.stringify(value));
}

function settle() {
  return new Promise(setImmediate);
}

// Runs one bundle with its own hook slots. preview() renders without effects; mount() runs only the
// first effect it meets, like a single mounted component, and keeps rendering from fresh state.
function loadDashboard(bundle, { fetchJSON, window = {}, globals = {} } = {}) {
  const state = [];
  const cleanups = [];
  let index = 0;
  let effects = 'ignore';
  let root;
  const sdk = {
    React: { createElement: (type, props, ...children) => ({ type, props: props ?? {}, children: children.flat() }) },
    hooks: {
      useState(initial) {
        const slot = index++;
        if (!(slot in state)) state[slot] = initial;
        return [state[slot], (value) => { state[slot] = typeof value === 'function' ? value(state[slot]) : value; }];
      },
      useRef(initial) {
        const slot = index++;
        if (!(slot in state)) state[slot] = { current: initial };
        return state[slot];
      },
      useEffect(callback) {
        if (effects !== 'first') return;
        effects = 'done';
        const cleanup = callback();
        if (typeof cleanup === 'function') cleanups.push(cleanup);
      },
    },
    fetchJSON,
  };
  vm.runInNewContext(fs.readFileSync(bundles[bundle], 'utf8'), {
    window: { ...window, __HERMES_PLUGIN_SDK__: sdk, __HERMES_PLUGINS__: { register(_name, view) { root = view; } } },
    console,
    ...globals,
  });
  assert.equal(typeof root, 'function', 'The bundle must register its page');
  function draw(view) {
    index = 0;
    return view();
  }
  function reset(mode) {
    state.length = 0;
    effects = mode;
  }
  return {
    root,
    preview(view = root) {
      reset('ignore');
      return draw(view);
    },
    mount(view = root) {
      reset('first');
      const render = () => draw(view);
      render();
      return render;
    },
    unmount() {
      for (const cleanup of cleanups.splice(0)) cleanup();
    },
  };
}

module.exports = { component, find, findAll, loadDashboard, plain, settle, text };
