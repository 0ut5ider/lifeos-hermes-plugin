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
});
