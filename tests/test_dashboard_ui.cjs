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

test("model picker starts with the current Hermes model and saves every tier", async () => {
  const fields = ["haiku", "sonnet", "opus", "fable"].flatMap((tier) => [
    { key: tier + "_provider", type: "string", value: "" },
    { key: tier + "_model", type: "string", value: "" },
    { key: tier + "_inherit_child_default", type: "boolean", value: false },
    { key: tier + "_effort", type: "enum", value: { haiku: "low", sonnet: "medium", opus: "xhigh", fable: "xhigh" }[tier], choices: ["low", "medium", "high", "xhigh"] },
  ]);
  fields.push({ key: "stop_cap_policy", type: "enum", value: "claude", choices: ["claude", "fail_closed"] });
  const models = { model: "flashnext", provider: "custom", providers: [
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
    const selectedModel = find(view, (node) => node.type === "select" && node.props.id === tier + "_model");
    assert.equal(selectedModel.props.value, JSON.stringify(["custom", "flashnext"]));
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
  for (const tier of ["haiku", "sonnet", "opus", "fable"]) {
    assert.equal(values[tier + "_provider"], "custom");
    assert.equal(values[tier + "_model"], "flashnext");
  }
  assert.equal(values.haiku_effort, "high");
  assert.equal(values.sonnet_effort, "medium");
  assert.equal(values.opus_effort, "xhigh");
  assert.equal(values.fable_effort, "xhigh");
  assert.equal(values.haiku_inherit_child_default, false);
  const inherited = find(render(), (node) => node.type === "select" && node.props.id === "haiku_model");
  inherited.props.onChange({ target: { value: "" } });
  const inheritForm = find(render(), (node) => node.type === "form");
  inheritForm.props.onSubmit({ preventDefault() {} });
  await new Promise(setImmediate);
  const inheritSave = calls.filter((call) => call.init?.method === "PUT").at(-1);
  assert.equal(JSON.parse(inheritSave.init.body).haiku_model, "");
  assert.equal(JSON.parse(inheritSave.init.body).haiku_inherit_child_default, true);
  assert.ok(find(render(), (node) => node.type === "p" && node.children.some((child) =>
    typeof child === "string" && child.includes("this Hermes conversation's model"))));
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

test("an explicit existing child route stays selected after reloading", async () => {
  const fields = ["haiku", "sonnet", "opus", "fable"].flatMap((tier) => [
    { key: tier + "_provider", value: tier === "sonnet" ? "second" : "" },
    { key: tier + "_model", value: tier === "sonnet" ? "other-model" : "" },
    { key: tier + "_inherit_child_default", value: tier === "haiku" },
    { key: tier + "_effort", value: "low", choices: ["low", "medium", "xhigh"] },
  ]);
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
      if (url.endsWith("/settings")) return Promise.resolve({ fields });
      if (url.includes("/api/model/options")) return Promise.resolve({
        model: "flashnext", provider: "custom", providers: [
          { slug: "custom", name: "Local", models: ["flashnext"] },
          { slug: "second", name: "Other", models: ["other-model"] },
        ],
      });
      if (url.endsWith("/installation")) return Promise.resolve({ lifeos: "installed", hermes: "stock" });
      return Promise.resolve({ state: "missing" });
    },
  };
  vm.runInNewContext(bundle, { window: {
    __HERMES_PLUGIN_SDK__: sdk,
    __HERMES_PLUGINS__: { register: (_name, view) => { component = view; } },
  }, console });
  const render = () => { index = 0; return component(); };
  render();
  await new Promise(setImmediate);
  const view = render();
  const selected = (tier) => find(view, (node) => node.type === "select" && node.props.id === tier + "_model").props.value;
  assert.equal(selected("haiku"), "");
  assert.equal(selected("sonnet"), JSON.stringify(["second", "other-model"]));
  assert.equal(selected("opus"), JSON.stringify(["custom", "flashnext"]));
  assert.equal(selected("fable"), JSON.stringify(["custom", "flashnext"]));
});

test("missing LifeOS shows preparation without active model settings", async () => {
  const calls = [];
  const state = [];
  let index = 0;
  let effectRan = false;
  let component;
  let lifeos = "missing";
  let candidateReady = false;
  let setupComplete = false;
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
      if (url.endsWith("/installation/finalize")) {
        setupComplete = true;
        return Promise.resolve({ mounted: true, baseline_created: true, restart_required: true });
      }
      if (url.endsWith("/installation")) return Promise.resolve({
        lifeos, version: lifeos === "installed" ? "7.40.4" : null,
        setup_baseline_exists: setupComplete,
        mount: {state: "applying", recovery_required: true},
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
  assert.ok(find(render(), (node) => node.type === "button" &&
    node.children.includes("Restore interrupted mount")));
  const finish = find(render(), (node) => node.type === "button" &&
    node.children.includes("Finish LifeOS setup"));
  assert.ok(finish);
  finish.props.onClick();
  await new Promise(setImmediate);
  await new Promise(setImmediate);
  assert.ok(calls.some((call) => call.url.endsWith("/installation/finalize") && call.init?.method === "POST"));
  assert.equal(find(render(), (node) => node.type === "button" &&
    node.children.includes("Finish LifeOS setup")), null);
});

test("installed LifeOS on stock Hermes shows the reduced safety limits", async () => {
  const calls = [];
  const state = [];
  let index = 0;
  let effectRan = false;
  let component;
  let candidateReady = false;
  let lifeosCandidateReady = false;
  let lifeosUpdateApplied = false;
  let hostPatched = false;
  let hostRestored = false;
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
        lifeosCandidateReady = true;
        return Promise.resolve({ upstream_commit: "a".repeat(40), patches: Array(9).fill({ name: "patch" }) });
      }
      if (url.endsWith("/installation/update") && init?.method === "POST") {
        lifeosUpdateApplied = true;
        return Promise.resolve({ state: "queued" });
      }
      if (url.endsWith("/installation/update")) return Promise.resolve({ state: lifeosUpdateApplied ? "applied" : "none" });
      if (url.endsWith("/installation/prepare-hermes")) {
        candidateReady = true;
        return Promise.resolve({ base_commit: "b".repeat(40), patches: Array(19).fill({ name: "patch" }) });
      }
      if (url.endsWith("/installation/apply-hermes")) {
        hostPatched = true;
        hostRestored = false;
        return Promise.resolve({ state: "staged" });
      }
      if (url.endsWith("/installation/restore-hermes")) {
        hostPatched = false;
        hostRestored = true;
        return Promise.resolve({ state: "restoring" });
      }
      if (url.endsWith("/installation/host-patch")) return Promise.resolve({
        state: hostPatched ? "applied" : hostRestored ? "rolled_back" : "none",
      });
      if (url.endsWith("/installation")) return Promise.resolve({
        lifeos: "installed", version: "7.40.4", hermes: hostPatched ? "patched_hooks_present" : "stock",
        candidate_ready: lifeosCandidateReady, setup_baseline_exists: true,
        hermes_candidate_ready: candidateReady,
        hermes_candidate_commit: candidateReady ? "b".repeat(40) : null,
        hermes_candidate_patch_count: candidateReady ? 19 : null,
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
  const prepareUpdate = find(view, (node) => node.type === "button" &&
    node.children.includes("Prepare latest LifeOS update"));
  assert.ok(prepareUpdate);
  prepareUpdate.props.onClick();
  await new Promise(setImmediate);
  const applyUpdate = find(render(), (node) => node.type === "button" &&
    node.children.includes("Apply prepared LifeOS update"));
  assert.ok(applyUpdate);
  applyUpdate.props.onClick();
  await new Promise(setImmediate);
  await new Promise(setImmediate);
  assert.ok(calls.some((call) => call.url.endsWith("/installation/update") && call.init?.method === "POST"));
  const prepareHost = find(view, (node) => node.type === "button" &&
    node.children.includes("Prepare tested Hermes extension"));
  assert.ok(prepareHost);
  prepareHost.props.onClick();
  await new Promise(setImmediate);
  assert.ok(calls.some((call) => call.url.endsWith("/installation/prepare-hermes") && call.init?.method === "POST"));
  assert.ok(find(render(), (node) => node.type === "p" &&
    node.children.some((child) => typeof child === "string" && child.includes("19 Hermes patches"))));
  const applyHost = find(render(), (node) => node.type === "button" &&
    node.children.includes("Apply tested Hermes extension"));
  assert.ok(applyHost);
  applyHost.props.onClick();
  await new Promise(setImmediate);
  await new Promise(setImmediate);
  assert.ok(calls.some((call) => call.url.endsWith("/installation/apply-hermes") && call.init?.method === "POST"));
  assert.ok(find(render(), (node) => node.type === "p" &&
    node.children.some((child) => typeof child === "string" && child.includes("Hermes extension is active"))));
  const restoreHost = find(render(), (node) => node.type === "button" &&
    node.children.includes("Restore previous Hermes"));
  assert.ok(restoreHost);
  restoreHost.props.onClick();
  await new Promise(setImmediate);
  await new Promise(setImmediate);
  assert.ok(calls.some((call) => call.url.endsWith("/installation/restore-hermes") && call.init?.method === "POST"));
  assert.equal(find(render(), (node) => node.type === "button" &&
    node.children.includes("Restore previous Hermes")), null);
});
