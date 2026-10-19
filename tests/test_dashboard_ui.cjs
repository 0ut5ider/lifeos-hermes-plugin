// ABOUTME: Checks that the LifeOS dashboard selects configured Hermes models by provider.
// ABOUTME: Runs the plugin bundle against a small React SDK contract without a browser.

const assert = require("node:assert/strict");
const test = require("node:test");
const { find, findAll, loadDashboard, plain, settle, text } = require("./support/dashboard_sdk.cjs");

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
  const sdk = {
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
  const render = loadDashboard("bridge", sdk).mount();
  await settle();
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
  await settle();
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
  await settle();
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
  await settle();
  const lastSave = calls.filter((call) => call.init?.method === "PUT").at(-1);
  assert.equal(JSON.parse(lastSave.init.body).stop_cap_policy, "fail_closed");
  assert.ok(calls.some((call) => call.url.includes("/api/model/options?explicit_only=1")));

  const source = find(render(), (node) => node.type === "input" && node.props.id === "lifeos_source_dir");
  source.props.onChange({ target: { value: "/srv/LifeOS/LifeOS/install" } });
  const preview = find(render(), (node) => node.type === "button" && node.children.includes("Preview baseline files"));
  preview.props.onClick();
  await settle();
  const reviewed = find(render(), (node) => node.type === "pre" &&
    node.children.includes("hooks/VersionDrift.hook.ts"));
  assert.ok(reviewed);
  const create = find(render(), (node) => node.type === "button" && node.children.includes("Create reviewed baseline"));
  create.props.onClick();
  await settle();
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
  const sdk = {
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
  const render = loadDashboard("bridge", sdk).mount();
  await settle();
  const view = render();
  const selected = (tier) => find(view, (node) => node.type === "select" && node.props.id === tier + "_model").props.value;
  assert.equal(selected("haiku"), "");
  assert.equal(selected("sonnet"), JSON.stringify(["second", "other-model"]));
  assert.equal(selected("opus"), JSON.stringify(["custom", "flashnext"]));
  assert.equal(selected("fable"), JSON.stringify(["custom", "flashnext"]));
});

test("missing LifeOS shows preparation without active model settings", async () => {
  const calls = [];
  let lifeos = "missing";
  let candidateReady = false;
  let setupComplete = false;
  const sdk = {
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
  const render = loadDashboard("bridge", sdk).mount();
  await settle();
  const view = render();
  assert.equal(find(view, (node) => node.type === "form"), null);
  assert.equal(find(view, (node) => node.type === "h2" && node.children.includes("VersionDrift baseline")), null);
  const prepareLifeOS = find(view, (node) => node.type === "button" &&
    node.children.includes("Prepare latest LifeOS"));
  assert.ok(prepareLifeOS);
  prepareLifeOS.props.onClick();
  await settle();
  assert.ok(calls.some((call) => call.url.endsWith("/installation/prepare") && call.init?.method === "POST"));
  assert.ok(find(render(), (node) => node.type === "p" &&
    node.children.some((child) => typeof child === "string" && child.includes("Candidate prepared"))));
  const installLifeOS = find(render(), (node) => node.type === "button" &&
    node.children.includes("Install prepared LifeOS"));
  assert.ok(installLifeOS);
  assert.ok(find(render(), (node) => node.type === "p" &&
    node.children.some((child) => typeof child === "string" && child.includes("1 compatibility patch"))));
  installLifeOS.props.onClick();
  await settle();
  await settle();
  assert.ok(calls.some((call) => call.url.endsWith("/installation/apply") && call.init?.method === "POST"));
  assert.ok(find(render(), (node) => node.type === "p" &&
    node.children.some((child) => typeof child === "string" && child.includes("LifeOS 7.40.4 is installed"))));
  assert.ok(find(render(), (node) => node.type === "button" &&
    node.children.includes("Restore interrupted mount")));
  const finish = find(render(), (node) => node.type === "button" &&
    node.children.includes("Finish LifeOS setup"));
  assert.ok(finish);
  finish.props.onClick();
  await settle();
  await settle();
  assert.ok(calls.some((call) => call.url.endsWith("/installation/finalize") && call.init?.method === "POST"));
  assert.equal(find(render(), (node) => node.type === "button" &&
    node.children.includes("Finish LifeOS setup")), null);
});

test("installed LifeOS on stock Hermes shows the reduced safety limits", async () => {
  const calls = [];
  let candidateReady = false;
  let lifeosCandidateReady = false;
  let lifeosUpdateApplied = false;
  let hostPatched = false;
  let hostRestored = false;
  const sdk = {
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
  const render = loadDashboard("bridge", sdk).mount();
  await settle();
  const view = render();
  assert.ok(find(view, (node) => node.type === "p" &&
    node.children.some((child) => typeof child === "string" && child.includes("Reduced mode cannot enforce LifeOS Bash permission decisions"))));
  assert.equal(find(view, (node) => node.type === "button" &&
    node.children.includes("Prepare latest LifeOS")), null);
  const prepareUpdate = find(view, (node) => node.type === "button" &&
    node.children.includes("Prepare latest LifeOS update"));
  assert.ok(prepareUpdate);
  prepareUpdate.props.onClick();
  await settle();
  const applyUpdate = find(render(), (node) => node.type === "button" &&
    node.children.includes("Apply prepared LifeOS update"));
  assert.ok(applyUpdate);
  applyUpdate.props.onClick();
  await settle();
  await settle();
  assert.ok(calls.some((call) => call.url.endsWith("/installation/update") && call.init?.method === "POST"));
  const restoreLifeOS = find(render(), (node) => node.type === "button" &&
    node.children.includes("Restore previous LifeOS version"));
  assert.ok(restoreLifeOS);
  restoreLifeOS.props.onClick();
  await settle();
  assert.ok(calls.some((call) => call.url.endsWith("/installation/update/restore") && call.init?.method === "POST"));
  const prepareHost = find(view, (node) => node.type === "button" &&
    node.children.includes("Prepare tested Hermes extension"));
  assert.ok(prepareHost);
  prepareHost.props.onClick();
  await settle();
  assert.ok(calls.some((call) => call.url.endsWith("/installation/prepare-hermes") && call.init?.method === "POST"));
  assert.ok(find(render(), (node) => node.type === "p" &&
    node.children.some((child) => typeof child === "string" && child.includes("19 Hermes patches"))));
  const applyHost = find(render(), (node) => node.type === "button" &&
    node.children.includes("Apply tested Hermes extension"));
  assert.ok(applyHost);
  applyHost.props.onClick();
  await settle();
  await settle();
  assert.ok(calls.some((call) => call.url.endsWith("/installation/apply-hermes") && call.init?.method === "POST"));
  assert.ok(find(render(), (node) => node.type === "p" &&
    node.children.some((child) => typeof child === "string" && child.includes("Hermes extension is active"))));
  const restoreHost = find(render(), (node) => node.type === "button" &&
    node.children.includes("Restore previous Hermes"));
  assert.ok(restoreHost);
  restoreHost.props.onClick();
  await settle();
  await settle();
  assert.ok(calls.some((call) => call.url.endsWith("/installation/restore-hermes") && call.init?.method === "POST"));
  assert.equal(find(render(), (node) => node.type === "button" &&
    node.children.includes("Restore previous Hermes")), null);
});

test("a host change waiting for a dashboard restart hides stale Hermes controls", async () => {
  const sdk = {
    fetchJSON: (url) => {
      if (url.endsWith("/installation/host-patch")) return Promise.resolve({ state: "applied" });
      if (url.endsWith("/installation")) return Promise.resolve({
        lifeos: "installed", version: "7.40.4", hermes: "stock", dashboard_restart_required: true,
        candidate_ready: false, setup_baseline_exists: true, hermes_candidate_ready: true,
      });
      if (url.endsWith("/version-drift")) return Promise.resolve({ state: "missing" });
      if (url.includes("/api/model/options")) return Promise.resolve({ providers: [] });
      return Promise.resolve({ fields: [] });
    },
  };
  const render = loadDashboard("bridge", sdk).mount();
  await settle();
  const view = render();
  assert.ok(find(view, (node) => node.type === "p" &&
    node.children.some((child) => typeof child === "string" && child.includes("Restart the Hermes dashboard"))));
  assert.equal(find(view, (node) => node.type === "button" &&
    node.children.includes("Prepare tested Hermes extension")), null);
  assert.equal(find(view, (node) => node.type === "p" &&
    node.children.some((child) => typeof child === "string" && child.includes("Reduced mode cannot enforce"))), null);
});

function inPlaceBridge(update, hostPatch = { state: "none" }, installation = {}) {
  return loadDashboard("bridge", {
    fetchJSON: (url) => {
      if (url.endsWith("/installation/update")) return Promise.resolve(update);
      if (url.endsWith("/installation/host-patch")) return Promise.resolve(hostPatch);
      if (url.endsWith("/installation")) return Promise.resolve({
        lifeos: "installed", version: "7.40.4", hermes: "patched_hooks_present", in_place: true,
        candidate_ready: true, candidate_newer: true, candidate_commit: "a".repeat(40), candidate_patch_count: 9,
        setup_baseline_exists: true, ...installation,
      });
      if (url.endsWith("/version-drift")) return Promise.resolve({ state: "missing" });
      if (url.includes("/api/model/options")) return Promise.resolve({ providers: [] });
      return Promise.resolve({ fields: [] });
    },
  }).mount();
}

test("an in-place installation points LifeOS updates to the releases page", async () => {
  const render = inPlaceBridge({ state: "applied", transaction_state: "applied" });
  await settle();
  const view = render();
  for (const label of ["Prepare latest LifeOS update", "Check for newer supported LifeOS",
    "Apply prepared LifeOS update", "Restore previous LifeOS version"]) {
    assert.equal(find(view, (node) => node.type === "button" && node.children.includes(label)), null, label);
  }
  const pointer = find(view, (node) => node.props?.id === "lifeos_update_pointer");
  assert.match(text(pointer), /^This installation gets LifeOS updates from the LifeOS releases page\.$/);
  assert.equal(find(pointer, (node) => node.type === "a").props.href, "/lifeos-releases");
  assert.equal(find(view, (node) => node.type === "p" && text(node).startsWith("Prepared commit")), null);
});

test("an in-place installation still shows and recovers an interrupted bridge update", async () => {
  const render = inPlaceBridge({ state: "interrupted", transaction_state: "swapped", job: "/jobs/update-one" });
  await settle();
  const view = render();
  assert.ok(find(view, (node) => node.type === "p" && text(node) === "LifeOS update: interrupted"));
  assert.ok(find(view, (node) => node.type === "button" && node.children.includes("Restore interrupted update")));
  assert.ok(find(view, (node) => node.props?.id === "lifeos_update_pointer"));
});

test("an in-place installation hides the bridge Hermes patch and setup controls", async () => {
  const stock = { hermes: "stock", hermes_candidate_ready: true, hermes_candidate_commit: "b".repeat(40),
    hermes_candidate_patch_count: 19 };
  let render = inPlaceBridge({ state: "none" }, { state: "none" }, stock);
  await settle();
  let view = render();
  for (const label of ["Prepare tested Hermes extension", "Apply tested Hermes extension"]) {
    assert.equal(find(view, (node) => node.type === "button" && node.children.includes(label)), null, label);
  }
  assert.equal(find(view, (node) => node.type === "p" && text(node).startsWith("Candidate base")), null);
  render = inPlaceBridge({ state: "none" }, { state: "none" }, { setup_baseline_exists: false });
  await settle();
  view = render();
  assert.equal(find(view, (node) => node.type === "button" && node.children.includes("Finish LifeOS setup")), null);
  assert.equal(find(view, (node) => node.type === "p" && text(node).startsWith("Finish setup")), null);
  assert.match(text(find(view, (node) => node.props?.id === "lifeos_update_pointer")),
    /^This installation gets LifeOS updates from the LifeOS releases page\.$/);
});

test("an in-place installation keeps an old bridge Hermes patch job visible and actionable", async () => {
  let render = inPlaceBridge({ state: "none" }, { state: "applied", snapshot: "/jobs/patch-1" });
  await settle();
  assert.ok(find(render(), (node) => node.type === "button" && node.children.includes("Restore previous Hermes")));
  render = inPlaceBridge({ state: "none" }, { state: "interrupted", transaction_state: "applying", snapshot: "/jobs/patch-1" });
  await settle();
  assert.ok(find(render(), (node) => node.type === "button" && node.children.includes("Recover interrupted Hermes change")));
  render = inPlaceBridge({ state: "none" }, { state: "restore_failed", error: "Gateway stop failed" });
  await settle();
  assert.ok(find(render(), (node) => node.type === "p" && text(node) === "Hermes patch job: restore_failed. Gateway stop failed"));
});

test("an interrupted Hermes patch change offers recovery", async () => {
  const calls = [];
  const sdk = {
    fetchJSON: (url, init) => {
      calls.push({ url, init });
      if (url.endsWith("/installation/recover-hermes")) return Promise.resolve({ state: "recovering" });
      if (url.endsWith("/installation/host-patch")) return Promise.resolve({ state: "interrupted", transaction_state: "restoring" });
      if (url.endsWith("/installation")) return Promise.resolve({
        lifeos: "installed", version: "7.40.4", hermes: "patched_hooks_present", setup_baseline_exists: true,
      });
      if (url.endsWith("/version-drift")) return Promise.resolve({ state: "missing" });
      if (url.includes("/api/model/options")) return Promise.resolve({ providers: [] });
      return Promise.resolve({ fields: [] });
    },
  };
  const render = loadDashboard("bridge", { ...sdk, window: { setTimeout: () => 0 } }).mount();
  await settle();
  const recover = find(render(), (node) => node.type === "button" &&
    node.children.includes("Recover interrupted Hermes change"));
  assert.ok(recover);
  recover.props.onClick();
  await settle();
  assert.ok(calls.some((call) => call.url.endsWith("/installation/recover-hermes") && call.init?.method === "POST"));
});

const commit = "a".repeat(40);
const installationActions = [
  { label: "Prepare latest LifeOS", path: "/installation/prepare", installation: { lifeos: "missing", candidate_ready: false },
    result: { upstream_commit: commit, patches: [] }, refreshed: [], failed: "Could not prepare LifeOS: ",
    done: "Candidate prepared from LifeOS commit " + commit + ". The running installation has not changed." },
  { label: "Install prepared LifeOS", path: "/installation/apply",
    installation: { lifeos: "missing", candidate_ready: true, candidate_commit: commit, candidate_patch_count: 1 },
    result: { installed_version: "7.40.4" }, refreshed: ["/installation"], failed: "Could not install LifeOS: ",
    done: "LifeOS 7.40.4 installed. Finish setup to mount it into Hermes and record the VersionDrift baseline." },
  { label: "Finish LifeOS setup", path: "/installation/finalize",
    installation: { lifeos: "installed", hermes: "patched_hooks_present", setup_baseline_exists: false, candidate_ready: true },
    result: { mounted: true }, refreshed: ["/installation", "/version-drift"], failed: "Could not finish LifeOS setup: ",
    done: "LifeOS is mounted and the baseline is recorded. Restart the Hermes gateway to load the new configuration." },
  { label: "Restore interrupted mount", path: "/installation/mount/recover",
    installation: { lifeos: "installed", hermes: "patched_hooks_present", setup_baseline_exists: false, mount: { recovery_required: true } },
    result: { restored: true }, refreshed: ["/installation"], failed: "Could not restore the mount: ",
    done: "The previous Hermes files are restored. You can finish setup again." },
  { label: "Prepare tested Hermes extension", path: "/installation/prepare-hermes",
    installation: { lifeos: "installed", hermes: "stock", setup_baseline_exists: true, candidate_ready: true, hermes_candidate_ready: false },
    result: { base_commit: commit, patches: [] }, refreshed: [], failed: "Could not prepare Hermes: ",
    done: "Hermes candidate prepared. The running Hermes installation has not changed." },
  { label: "Apply tested Hermes extension", path: "/installation/apply-hermes",
    installation: { lifeos: "installed", hermes: "stock", setup_baseline_exists: true, candidate_ready: true, hermes_candidate_ready: true },
    result: { state: "staged" }, refreshed: ["/installation/host-patch"], failed: "Could not start Hermes patch: ",
    done: "Hermes patch worker started. The gateway will restart while it applies the tested extension." },
  { label: "Restore previous Hermes", path: "/installation/restore-hermes", hostPatch: { state: "applied" },
    installation: { lifeos: "installed", hermes: "patched_hooks_present", setup_baseline_exists: true, candidate_ready: true },
    result: { state: "restoring" }, refreshed: ["/installation/host-patch", "/installation"], failed: "Could not start Hermes restore: ",
    done: "Restoring the previous Hermes source. The gateway will restart." },
  { label: "Recover interrupted Hermes change", path: "/installation/recover-hermes", hostPatch: { state: "interrupted" },
    installation: { lifeos: "installed", hermes: "patched_hooks_present", setup_baseline_exists: true, candidate_ready: true },
    result: { state: "recovering" }, refreshed: ["/installation/host-patch"], failed: "Could not start Hermes recovery: ",
    done: "Returning Hermes to its stock files. The gateway will restart." },
  { label: "Prepare latest LifeOS update", path: "/installation/prepare",
    installation: { lifeos: "installed", hermes: "patched_hooks_present", setup_baseline_exists: true, candidate_ready: false },
    result: { upstream_commit: commit, patches: [] }, refreshed: [], failed: "Could not prepare LifeOS: ",
    done: "Candidate prepared from LifeOS commit " + commit + ". The running installation has not changed." },
  { label: "Apply prepared LifeOS update", path: "/installation/update",
    installation: { lifeos: "installed", hermes: "patched_hooks_present", setup_baseline_exists: true, candidate_ready: true },
    result: { state: "queued" }, refreshed: ["/installation/update"], failed: "Could not start LifeOS update: ",
    done: "LifeOS update started. The gateway will restart after native checks pass." },
  { label: "Restore previous LifeOS version", path: "/installation/update/restore", update: { state: "applied" },
    installation: { lifeos: "installed", hermes: "patched_hooks_present", setup_baseline_exists: true, candidate_ready: true },
    result: { state: "restoring" }, refreshed: ["/installation/update", "/installation", "/version-drift"], failed: "Could not restore LifeOS: ",
    done: "Restoring the previous LifeOS version. Hermes will restart." },
  { label: "Restore interrupted update", path: "/installation/update/recover", update: { state: "interrupted", transaction_state: "swapped" },
    installation: { lifeos: "installed", hermes: "patched_hooks_present", setup_baseline_exists: true, candidate_ready: true },
    result: { state: "recovering" }, refreshed: ["/installation/update"], failed: "Could not start LifeOS recovery: ",
    done: "LifeOS recovery started. If no files were replaced, the worker restarts the current version. Otherwise, it restores the prior version and restarts Hermes." },
];

async function installationPage(action, respond, refresh) {
  const calls = [];
  let submitted = false;
  const sdk = {
    fetchJSON(url, init) {
      calls.push({ url, init });
      if (init?.method === "POST") { submitted = true; return respond(); }
      if (submitted && refresh && url.endsWith("/installation")) return refresh();
      if (url.endsWith("/installation/host-patch")) return Promise.resolve(action.hostPatch ?? { state: "none" });
      if (url.endsWith("/installation/update")) return Promise.resolve(action.update ?? { state: "none" });
      if (url.endsWith("/installation")) return Promise.resolve({ version: "7.40.4", ...action.installation });
      if (url.endsWith("/version-drift")) return Promise.resolve({ state: "missing" });
      if (url.includes("/api/model/options")) return Promise.resolve({ providers: [] });
      return Promise.resolve({ fields: [] });
    },
  };
  const render = loadDashboard("bridge", { ...sdk, window: { setTimeout: () => 0 } }).mount();
  await settle();
  const section = () => find(render(), (node) => node.props.id === "lifeos_installation");
  const button = () => find(section(), (node) => node.type === "button" && node.children.includes(action.label));
  const status = () => find(section(), (node) => node.type === "p" && node.props.role === "status" && node.props.className === "mt-3");
  assert.ok(button(), "Missing installation action: " + action.label);
  return { calls, section, button, status };
}

test("installation actions post once, stay busy, then report their result", async () => {
  for (const action of installationActions) {
    const page = await installationPage(action, () => Promise.resolve(action.result));
    const before = page.calls.length;
    page.button().props.onClick();
    const buttons = findAll(page.section(), (node) => node.type === "button");
    assert.ok(buttons.length && buttons.every((node) => node.props.disabled === true), action.label + " must disable installation actions");
    for (let turn = 0; turn < 4; turn++) await settle();
    const after = page.calls.slice(before);
    assert.ok(after[0].url.endsWith(action.path), action.label);
    assert.deepEqual(plain(after[0].init), { method: "POST" });
    assert.deepEqual(after.slice(1).map((call) => call.url.replace("/api/plugins/lifeos-hook-bridge", "")), action.refreshed, action.label);
    assert.ok(after.slice(1).every((call) => call.init === undefined));
    assert.deepEqual(page.status()?.children, [action.done]);
  }
});

test("installation action failures report the reason and release the busy state", async () => {
  for (const action of installationActions) {
    const page = await installationPage(action, () => Promise.reject(new Error("synthetic refusal")));
    const before = page.calls.length;
    page.button().props.onClick();
    for (let turn = 0; turn < 4; turn++) await settle();
    assert.equal(page.calls.length - before, 1, action.label + " must not refresh after a failure");
    assert.deepEqual(page.status()?.children, [action.failed + "synthetic refusal"]);
    assert.equal(page.button().props.disabled, false, action.label);
  }
});

test("installation refresh failures keep actions busy and clear the previous status", async () => {
  const refreshing = ["/installation/apply", "/installation/finalize", "/installation/mount/recover"];
  for (const action of installationActions.filter(action => refreshing.includes(action.path))) {
    let rejectRefresh, attempt = 0;
    const refresh = new Promise((resolve, reject) => { rejectRefresh = reject; });
    const page = await installationPage(action, () => ++attempt === 1 ?
      Promise.reject(new Error("synthetic prior refusal")) : Promise.resolve(action.result), () => refresh);
    page.button().props.onClick();
    await settle();
    assert.deepEqual(page.status()?.children, [action.failed + "synthetic prior refusal"]);
    page.button().props.onClick();
    assert.deepEqual(page.status()?.children ?? [], [], action.label + " clears its previous status");
    await settle();
    try {
      const buttons = findAll(page.section(), node => node.type === "button");
      assert.ok(buttons.length && buttons.every(node => node.props.disabled === true),
        action.label + " waits for its pending refresh");
    } finally {
      rejectRefresh(new Error("synthetic refresh refusal"));
      await settle();
    }
    assert.deepEqual(page.status()?.children, [action.failed + "synthetic refresh refusal"]);
    assert.equal(page.button().props.disabled, false, action.label);
  }
});
