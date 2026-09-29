// ABOUTME: Checks that the LifeOS dashboard selects configured Hermes models by provider.
// ABOUTME: Runs the plugin bundle against a small React SDK contract without a browser.

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const bundle = fs.readFileSync(path.join(__dirname, "../lifeos_hook_bridge/dashboard/dist/index.js"), "utf8");

function find(node, match) {
  if (!node || typeof node !== "object") return null;
  if (match(node)) return node;
  for (const child of node.children || []) {
    const result = find(child, match);
    if (result) return result;
  }
  return null;
}

test("model picker saves the selected provider, model, and effort", async () => {
  const fields = ["haiku", "sonnet", "opus", "fable"].flatMap((tier) => [
    { key: tier + "_provider", type: "string", value: "" },
    { key: tier + "_model", type: "string", value: "" },
    { key: tier + "_effort", type: "enum", value: "low", choices: ["low", "high"] },
  ]);
  fields.push({ key: "stop_cap_policy", type: "enum", value: "claude", choices: ["claude", "fail_closed"] });
  const models = { providers: [
    { slug: "custom", name: "Local endpoint", models: ["flashnext"] },
    { slug: "remote", name: "Remote endpoint", models: ["other"] },
  ] };
  const calls = [];
  const state = [];
  let index = 0;
  let effectRan = false;
  let component;
  const sdk = {
    React: { createElement: (type, props, ...children) => ({ type, props: props || {}, children: children.flat() }) },
    hooks: {
      useState(initial) {
        const slot = index++;
        if (!(slot in state)) state[slot] = initial;
        return [state[slot], (value) => { state[slot] = typeof value === "function" ? value(state[slot]) : value; }];
      },
      useEffect(callback) {
        if (!effectRan) { effectRan = true; callback(); }
      },
    },
    fetchJSON(url, init) {
      calls.push({ url, init });
      if (init?.method === "PUT") return Promise.resolve({ saved: ["haiku_model"] });
      if (url.endsWith("/version-drift/preview")) return Promise.resolve({
        version: "7.40.4", source_commit: "a".repeat(40), file_count: 1,
        files: ["hooks/VersionDrift.hook.ts"], fingerprint: "reviewed",
      });
      if (url.endsWith("/version-drift") && init?.method === "POST") return Promise.resolve({
        state: "ready", version: "7.40.4", source_commit: "a".repeat(40),
        file_count: 1, changed_count: 0, installed_version: "7.40.4", version_mismatch: false,
      });
      if (url.endsWith("/version-drift")) return Promise.resolve({ state: "missing", baseline_exists: false });
      if (url.endsWith("/installation/prepare")) return Promise.resolve({
        upstream_commit: "a".repeat(40), patches: [{ name: "lifeos-test.patch" }],
      });
      if (url.endsWith("/installation")) return Promise.resolve({
        lifeos: "installed", version: "7.40.4", hermes: "stock",
        missing_hooks: ["pre_turn_stop"], candidate_ready: false,
      });
      if (url.includes("/api/model/options")) return Promise.resolve(models);
      return Promise.resolve({ fields });
    },
  };
  const window = {
    __HERMES_PLUGIN_SDK__: sdk,
    __HERMES_PLUGINS__: { register: (_name, view) => { component = view; } },
  };
  vm.runInNewContext(bundle, { window, console });
  const render = () => { index = 0; return component(); };
  render();
  await new Promise(setImmediate);
  const view = render();
  for (const tier of ["haiku", "sonnet", "opus", "fable"]) {
    assert.ok(find(view, (node) => node.type === "select" && node.props.id === tier + "_model"));
    assert.ok(find(view, (node) => node.type === "select" && node.props.id === tier + "_effort"));
  }
  const modelSelect = find(view, (node) => node.type === "select" && node.props.id === "haiku_model");
  assert.ok(modelSelect);
  const option = find(modelSelect, (node) => node.type === "option" && node.children.includes("Local endpoint / flashnext"));
  assert.ok(option);
  modelSelect.props.onChange({ target: { value: option.props.value } });
  const effortSelect = find(render(), (node) => node.type === "select" && node.props.id === "haiku_effort");
  effortSelect.props.onChange({ target: { value: "high" } });
  const form = find(render(), (node) => node.type === "form");
  form.props.onSubmit({ preventDefault() {} });
  await new Promise(setImmediate);
  const saved = calls.find((call) => call.init?.method === "PUT");
  assert.ok(saved);
  const values = JSON.parse(saved.init.body);
  assert.equal(values.haiku_provider, "custom");
  assert.equal(values.haiku_model, "flashnext");
  assert.equal(values.haiku_effort, "high");
  const stopPolicy = find(render(), (node) => node.type === "select" && node.props.id === "stop_cap_policy");
  assert.ok(stopPolicy);
  stopPolicy.props.onChange({ target: { value: "fail_closed" } });
  const policyForm = find(render(), (node) => node.type === "form");
  policyForm.props.onSubmit({ preventDefault() {} });
  await new Promise(setImmediate);
  const lastSave = calls.filter((call) => call.init?.method === "PUT").at(-1);
  assert.equal(JSON.parse(lastSave.init.body).stop_cap_policy, "fail_closed");
  assert.ok(calls.some((call) => call.url.includes("/api/model/options?explicit_only=1")));

  const source = find(render(), (node) => node.type === "input" && node.props.id === "lifeos_source_dir");
  source.props.onChange({ target: { value: "/srv/LifeOS/LifeOS/install" } });
  const preview = find(render(), (node) => node.type === "button" && node.children.includes("Preview baseline files"));
  preview.props.onClick();
  await new Promise(setImmediate);
  const reviewed = find(render(), (node) => node.type === "pre" &&
    node.children.includes("hooks/VersionDrift.hook.ts"));
  assert.ok(reviewed);
  const create = find(render(), (node) => node.type === "button" && node.children.includes("Create reviewed baseline"));
  create.props.onClick();
  await new Promise(setImmediate);
  const apply = calls.find((call) => call.url.endsWith("/version-drift") && call.init?.method === "POST");
  assert.deepEqual(JSON.parse(apply.init.body), {
    source: "/srv/LifeOS/LifeOS/install", fingerprint: "reviewed", renew: false,
  });
  assert.ok(find(render(), (node) => node.type === "p" &&
    node.children.some((child) => typeof child === "string" && child.includes("0 changed since baseline"))));

});

test("missing LifeOS shows preparation without active model settings", async () => {
  const calls = [];
  const state = [];
  let index = 0;
  let effectRan = false;
  let component;
  let lifeos = "missing";
  let candidateReady = false;
  const sdk = {
    React: { createElement: (type, props, ...children) => ({ type, props: props || {}, children: children.flat() }) },
    hooks: {
      useState(initial) {
        const slot = index++;
        if (!(slot in state)) state[slot] = initial;
        return [state[slot], (value) => { state[slot] = typeof value === "function" ? value(state[slot]) : value; }];
      },
      useEffect(callback) { if (!effectRan) { effectRan = true; callback(); } },
    },
    fetchJSON(url, init) {
      calls.push({ url, init });
      if (url.endsWith("/installation/prepare")) {
        candidateReady = true;
        return Promise.resolve({ upstream_commit: "a".repeat(40), patches: [{ name: "one.patch" }] });
      }
      if (url.endsWith("/installation/apply")) {
        lifeos = "installed";
        return Promise.resolve({ installed_version: "7.40.4", restart_required: true });
      }
      if (url.endsWith("/installation")) return Promise.resolve({
        lifeos, version: lifeos === "installed" ? "7.40.4" : null,
        hermes: "stock", candidate_ready: candidateReady,
        candidate_commit: candidateReady ? "a".repeat(40) : null,
        candidate_patch_count: candidateReady ? 1 : null,
      });
      if (url.endsWith("/version-drift")) return Promise.resolve({ state: "missing" });
      if (url.includes("/api/model/options")) return Promise.resolve({ providers: [] });
      return Promise.resolve({ fields: [] });
    },
  };
  vm.runInNewContext(bundle, {
    window: {
      __HERMES_PLUGIN_SDK__: sdk,
      __HERMES_PLUGINS__: { register: (_name, view) => { component = view; } },
    },
    console,
  });
  const render = () => { index = 0; return component(); };
  render();
  await new Promise(setImmediate);
  const view = render();
  assert.equal(find(view, (node) => node.type === "form"), null);
  assert.equal(find(view, (node) => node.type === "h2" && node.children.includes("VersionDrift baseline")), null);
  const prepareLifeOS = find(view, (node) => node.type === "button" &&
    node.children.includes("Prepare latest LifeOS"));
  assert.ok(prepareLifeOS);
  prepareLifeOS.props.onClick();
  await new Promise(setImmediate);
  assert.ok(calls.some((call) => call.url.endsWith("/installation/prepare") && call.init?.method === "POST"));
  assert.ok(find(render(), (node) => node.type === "p" &&
    node.children.some((child) => typeof child === "string" && child.includes("Candidate prepared"))));
  const installLifeOS = find(render(), (node) => node.type === "button" &&
    node.children.includes("Install prepared LifeOS"));
  assert.ok(installLifeOS);
  assert.ok(find(render(), (node) => node.type === "p" &&
    node.children.some((child) => typeof child === "string" && child.includes("1 compatibility patch"))));
  installLifeOS.props.onClick();
  await new Promise(setImmediate);
  await new Promise(setImmediate);
  assert.ok(calls.some((call) => call.url.endsWith("/installation/apply") && call.init?.method === "POST"));
  assert.ok(find(render(), (node) => node.type === "p" &&
    node.children.some((child) => typeof child === "string" && child.includes("LifeOS 7.40.4 is installed"))));
});

test("installed LifeOS on stock Hermes shows the reduced safety limits", async () => {
  const state = [];
  let index = 0;
  let effectRan = false;
  let component;
  const sdk = {
    React: { createElement: (type, props, ...children) => ({ type, props: props || {}, children: children.flat() }) },
    hooks: {
      useState(initial) {
        const slot = index++;
        if (!(slot in state)) state[slot] = initial;
        return [state[slot], (value) => { state[slot] = typeof value === "function" ? value(state[slot]) : value; }];
      },
      useEffect(callback) { if (!effectRan) { effectRan = true; callback(); } },
    },
    fetchJSON(url) {
      if (url.endsWith("/installation")) return Promise.resolve({
        lifeos: "installed", version: "7.40.4", hermes: "stock", candidate_ready: false,
      });
      if (url.endsWith("/version-drift")) return Promise.resolve({ state: "missing" });
      if (url.includes("/api/model/options")) return Promise.resolve({ providers: [] });
      return Promise.resolve({ fields: [] });
    },
  };
  vm.runInNewContext(bundle, {
    window: {
      __HERMES_PLUGIN_SDK__: sdk,
      __HERMES_PLUGINS__: { register: (_name, view) => { component = view; } },
    },
    console,
  });
  const render = () => { index = 0; return component(); };
  render();
  await new Promise(setImmediate);
  const view = render();
  assert.ok(find(view, (node) => node.type === "p" &&
    node.children.some((child) => typeof child === "string" && child.includes("Reduced mode cannot enforce LifeOS Bash permission decisions"))));
  assert.equal(find(view, (node) => node.type === "button" &&
    node.children.includes("Prepare latest LifeOS")), null);
});
