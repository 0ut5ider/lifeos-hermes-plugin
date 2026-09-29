// ABOUTME: Maps each LifeOS tier to a configured Hermes provider, model, and effort.
// ABOUTME: Uses Hermes's authenticated model catalog and the bridge settings API.
(function () {
  "use strict";

  const SDK = window.__HERMES_PLUGIN_SDK__;
  const React = SDK.React;
  const h = React.createElement;
  const endpoint = "/api/plugins/lifeos-hook-bridge/settings";
  const installationEndpoint = "/api/plugins/lifeos-hook-bridge/installation";
  const baselineEndpoint = "/api/plugins/lifeos-hook-bridge/version-drift";
  const modelEndpoint = "/api/model/options?explicit_only=1";
  const tiers = ["haiku", "sonnet", "opus", "fable"];

  function LifeOSSettings() {
    const [fields, setFields] = SDK.hooks.useState([]);
    const [values, setValues] = SDK.hooks.useState({});
    const [models, setModels] = SDK.hooks.useState([]);
    const [status, setStatus] = SDK.hooks.useState("Loading settings...");
    const [saving, setSaving] = SDK.hooks.useState(false);
    const [baseline, setBaseline] = SDK.hooks.useState(null);
    const [candidate, setCandidate] = SDK.hooks.useState(null);
    const [baselineStatus, setBaselineStatus] = SDK.hooks.useState("");
    const [baselineBusy, setBaselineBusy] = SDK.hooks.useState(false);
    const [installation, setInstallation] = SDK.hooks.useState(null);
    const [installationStatus, setInstallationStatus] = SDK.hooks.useState("");
    const [installationBusy, setInstallationBusy] = SDK.hooks.useState(false);

    SDK.hooks.useEffect(function () {
      let active = true;
      Promise.all([SDK.fetchJSON(endpoint), SDK.fetchJSON(modelEndpoint)]).then(function (results) {
        if (!active) return;
        const data = results[0];
        const catalog = results[1];
        setFields(data.fields);
        setValues(Object.fromEntries(data.fields.map(function (field) {
          return [field.key, field.value ?? ""];
        })));
        const choices = [];
        for (const provider of catalog.providers ?? []) {
          if (provider.authenticated === false) continue;
          for (const model of provider.models ?? []) {
            if (typeof model !== "string" || !model) continue;
            choices.push({ provider: provider.slug, model: model, label: provider.name + " / " + model });
          }
        }
        setModels(choices);
        setStatus(choices.length ? "" : "No configured Hermes models are available. Add a model on the Models page.");
      }).catch(function (error) {
        if (active) setStatus("Could not load settings or models: " + error.message);
      });
      SDK.fetchJSON(baselineEndpoint).then(function (result) {
        if (active) setBaseline(result);
      }).catch(function (error) {
        if (active) setBaselineStatus("Could not read baseline status: " + error.message);
      });
      SDK.fetchJSON(installationEndpoint).then(function (result) {
        if (active) setInstallation(result);
      }).catch(function (error) {
        if (active) setInstallationStatus("Could not read installation status: " + error.message);
      });
      return function () { active = false; };
    }, []);

    function update(key, value) {
      setValues(function (current) { return Object.assign({}, current, { [key]: value }); });
    }

    function selectModel(tier, selected) {
      if (!selected) {
        setValues(function (current) {
          return Object.assign({}, current, { [tier + "_provider"]: "", [tier + "_model"]: "" });
        });
        return;
      }
      let pair;
      try { pair = JSON.parse(selected); } catch (_error) { return; }
      if (!Array.isArray(pair) || pair.length !== 2 ||
          typeof pair[0] !== "string" || typeof pair[1] !== "string") return;
      setValues(function (current) {
        return Object.assign({}, current, { [tier + "_provider"]: pair[0], [tier + "_model"]: pair[1] });
      });
    }

    function save(event) {
      event.preventDefault();
      setSaving(true);
      setStatus("");
      SDK.fetchJSON(endpoint, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(values),
      }).then(function () {
        setStatus("Saved. Restart the Hermes gateway to apply these settings.");
      }).catch(function (error) {
        setStatus("Could not save settings: " + error.message);
      }).finally(function () { setSaving(false); });
    }

    function previewBaseline() {
      setBaselineBusy(true);
      setBaselineStatus("");
      setCandidate(null);
      SDK.fetchJSON(baselineEndpoint + "/preview", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ source: values.lifeos_source_dir ?? "" }),
      }).then(function (result) {
        setCandidate(result);
        setBaselineStatus("Review the file list before creating this baseline.");
      }).catch(function (error) {
        setBaselineStatus("Could not preview baseline: " + error.message);
      }).finally(function () { setBaselineBusy(false); });
    }

    function applyBaseline() {
      if (!candidate) return;
      setBaselineBusy(true);
      setBaselineStatus("");
      SDK.fetchJSON(baselineEndpoint, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          source: values.lifeos_source_dir ?? "", fingerprint: candidate.fingerprint,
          renew: baseline?.baseline_exists === true,
        }),
      }).then(function (result) {
        setBaseline(result);
        setCandidate(null);
        setBaselineStatus("VersionDrift baseline saved.");
      }).catch(function (error) {
        setBaselineStatus("Could not save baseline: " + error.message);
      }).finally(function () { setBaselineBusy(false); });
    }

    function prepareLifeOS() {
      setInstallationBusy(true);
      setInstallationStatus("");
      SDK.fetchJSON(installationEndpoint + "/prepare", { method: "POST" }).then(function (result) {
        setInstallation(function (current) { return Object.assign({}, current, {
          candidate_ready: true, candidate_commit: result.upstream_commit,
          candidate_patch_count: result.patches.length, candidate_error: null,
        }); });
        setInstallationStatus("Candidate prepared from LifeOS commit " + result.upstream_commit + ". Installation has not changed yet.");
      }).catch(function (error) {
        setInstallationStatus("Could not prepare LifeOS: " + error.message);
      }).finally(function () { setInstallationBusy(false); });
    }

    function installLifeOS() {
      setInstallationBusy(true);
      setInstallationStatus("");
      SDK.fetchJSON(installationEndpoint + "/apply", { method: "POST" }).then(function (result) {
        return SDK.fetchJSON(installationEndpoint).then(function (status) {
          setInstallation(status);
          setInstallationStatus("LifeOS " + result.installed_version + " installed. Restart the Hermes gateway to load its hooks.");
        });
      }).catch(function (error) {
        setInstallationStatus("Could not install LifeOS: " + error.message);
      }).finally(function () { setInstallationBusy(false); });
    }

    function renderTier(tier) {
      const label = tier.charAt(0).toUpperCase() + tier.slice(1);
      const modelKey = tier + "_model";
      const providerKey = tier + "_provider";
      const effortKey = tier + "_effort";
      const effortField = fields.find(function (field) { return field.key === effortKey; });
      const selected = values[modelKey] ? JSON.stringify([values[providerKey] ?? "", values[modelKey]]) : "";
      const listed = models.some(function (choice) {
        return choice.provider === values[providerKey] && choice.model === values[modelKey];
      });
      const options = [h("option", { key: "default", value: "" }, "Use existing LifeOS child default")];
      if (selected && !listed) {
        options.push(h("option", { key: "saved", value: selected },
          "Saved: " + (values[providerKey] || "current provider") + " / " + values[modelKey]));
      }
      for (const choice of models) {
        options.push(h("option", {
          key: choice.provider + "/" + choice.model,
          value: JSON.stringify([choice.provider, choice.model]),
        }, choice.label));
      }
      return h("section", { key: tier, className: "rounded border border-border p-4" },
        h("h2", { className: "mb-3 text-lg font-semibold" }, label),
        h("div", { className: "grid gap-4 md:grid-cols-2" },
          h("div", null,
            h("label", { htmlFor: modelKey, className: "mb-1 block font-medium" }, "Hermes model"),
            h("select", {
              id: modelKey, value: selected,
              onChange: function (event) { selectModel(tier, event.target.value); },
              className: "w-full rounded border border-border bg-background p-2",
            }, options)),
          h("div", null,
            h("label", { htmlFor: effortKey, className: "mb-1 block font-medium" }, "Effort"),
            h("select", {
              id: effortKey, value: values[effortKey] ?? "",
              onChange: function (event) { update(effortKey, event.target.value); },
              className: "w-full rounded border border-border bg-background p-2",
            }, (effortField?.choices ?? []).map(function (choice) {
              return h("option", { key: choice, value: choice }, choice);
            })))));
    }

    const pinField = fields.find(function (field) { return field.key === "pinned_tier"; });
    const stopField = fields.find(function (field) { return field.key === "stop_cap_policy"; });
    return h("main", { className: "mx-auto max-w-4xl space-y-6 p-6" },
      h("div", null,
        h("h1", { className: "text-2xl font-semibold" }, "LifeOS Bridge"),
        h("p", { className: "text-muted-foreground" },
          "Choose a configured Hermes model and effort for each LifeOS tier. Select a model in every row to use Hermes provider routing for LifeOS child calls."),
        h("a", { href: "/models", className: "text-sm underline" }, "Manage Hermes models")),
      h("section", { className: "rounded border border-border p-4" },
        h("h2", { className: "mb-2 text-lg font-semibold" }, "LifeOS installation"),
        installation?.lifeos === "missing" ? h("p", { className: "mb-3 text-sm" },
          "LifeOS is not installed. Prepare the latest supported revision from Daniel Miessler's GitHub repository. This step checks and applies the LifeOS compatibility patches in a private candidate directory. It does not change the running installation.") : null,
        installation?.lifeos === "partial" ? h("p", { role: "status" },
          "A .claude directory already exists. The fresh installer will not overwrite it. Review that directory before installing LifeOS.") : null,
        installation?.lifeos === "installed" ? h("p", null,
          "LifeOS " + installation.version + " is installed.") : null,
        installation?.lifeos === "installed" && installation.hermes === "stock" ? h("div", { className: "space-y-2 text-sm" },
          h("p", null, "Current Hermes runs LifeOS pre-tool, post-tool, prompt-context, and session-end callbacks."),
          h("p", null, "Reduced mode cannot enforce LifeOS Bash permission decisions, block a user prompt, gate a final answer, or reliably add post-tool warnings after another result transformer. It also lacks the patched child model routes and remote file guards.")) : null,
        installation?.lifeos === "installed" && installation.hermes === "patched_hooks_present" ? h("p", { className: "text-sm" },
          "The required Hermes hook names are present. The complete patch set still needs a release verification before full parity can be claimed.") : null,
        installation?.hermes === "partial" ? h("p", { role: "status" },
          "Hermes exposes only part of the required hook contract. Use a tested compatible release before enabling the full bridge.") : null,
        installation?.lifeos === "missing" ? h("button", {
          type: "button", disabled: installationBusy || installation.candidate_ready,
          onClick: prepareLifeOS,
          className: "rounded bg-primary px-4 py-2 text-primary-foreground disabled:opacity-50",
        }, installationBusy ? "Preparing..." : "Prepare latest LifeOS") : null,
        installation?.candidate_ready && installation?.lifeos === "missing" ? h("div", { className: "mt-3 space-y-2 text-sm" },
          h("p", null, "Prepared commit " + installation.candidate_commit + " with " +
            installation.candidate_patch_count + " compatibility patches. The fresh installer will create ~/.claude and run six LifeOS setup steps."),
          h("button", {
            type: "button", disabled: installationBusy, onClick: installLifeOS,
            className: "rounded border border-border px-4 py-2 disabled:opacity-50",
          }, installationBusy ? "Installing..." : "Install prepared LifeOS")) : null,
        installation?.candidate_error ? h("p", { role: "status", className: "mt-2 text-sm" },
          "Candidate cannot be installed: " + installation.candidate_error) : null,
        installationStatus ? h("p", { role: "status", className: "mt-3" }, installationStatus) : null),
      installation?.lifeos === "installed" ? h("form", { onSubmit: save, className: "space-y-4" },
        fields.length ? tiers.map(renderTier) : null,
        stopField ? h("section", { className: "rounded border border-border p-4" },
          h("h2", { className: "mb-2 text-lg font-semibold" }, "Stop hook limit"),
          h("p", { className: "mb-3 text-sm text-muted-foreground" }, stopField.description),
          h("select", {
            id: "stop_cap_policy", value: values.stop_cap_policy ?? "claude",
            onChange: function (event) { update("stop_cap_policy", event.target.value); },
            className: "w-full rounded border border-border bg-background p-2",
          }, [
            h("option", { key: "claude", value: "claude" }, "Match Claude Code: allow the last answer"),
            h("option", { key: "fail_closed", value: "fail_closed" }, "Fail the turn: withhold the last answer"),
          ])) : null,
        pinField ? h("details", { className: "rounded border border-border p-4" },
          h("summary", { className: "cursor-pointer font-medium" }, "Advanced: pinned LifeOS tier"),
          h("p", { className: "mt-2 text-sm text-muted-foreground" }, pinField.description),
          h("select", {
            id: "pinned_tier", value: values.pinned_tier ?? "fable",
            onChange: function (event) { update("pinned_tier", event.target.value); },
            className: "mt-2 w-full rounded border border-border bg-background p-2",
          }, (pinField.choices ?? []).map(function (choice) {
            return h("option", { key: choice, value: choice }, choice);
          }))) : null,
        fields.length ? h("button", {
          type: "submit", disabled: saving,
          className: "rounded bg-primary px-4 py-2 text-primary-foreground disabled:opacity-50",
        }, saving ? "Saving..." : "Save settings") : null) : null,
      installation?.lifeos === "installed" ? h("section", { className: "rounded border border-border p-4" },
        h("h2", { className: "mb-2 text-lg font-semibold" }, "VersionDrift baseline"),
        h("p", { className: "mb-3 text-sm text-muted-foreground" },
          "Track installed LifeOS system files without adding a Git repository to Hermes home."),
        baseline?.state === "ready" ? h("p", null,
          "Version " + baseline.version + ", " + baseline.file_count + " files, " +
          baseline.changed_count + " changed since baseline. Source commit " + baseline.source_commit + ".") :
          h("p", null, baseline?.state === "error" ? "Baseline error: " + baseline.message : "No baseline created."),
        baseline?.version_mismatch ? h("p", { role: "status" },
          "Installed LifeOS version " + baseline.installed_version + " differs from the baseline. " +
          "Review the updated source and renew the baseline after its tests pass.") : null,
        h("label", { htmlFor: "lifeos_source_dir", className: "mb-1 block font-medium" },
          "LifeOS source install path"),
        h("input", {
          id: "lifeos_source_dir", type: "text", value: values.lifeos_source_dir ?? "",
          onChange: function (event) { update("lifeos_source_dir", event.target.value); setCandidate(null); },
          placeholder: "/home/user/workspace/LifeOS/LifeOS/install",
          className: "mb-3 w-full rounded border border-border bg-background p-2",
        }),
        h("button", {
          type: "button", disabled: baselineBusy || !values.lifeos_source_dir,
          onClick: previewBaseline,
          className: "rounded bg-primary px-4 py-2 text-primary-foreground disabled:opacity-50",
        }, baselineBusy ? "Working..." : "Preview baseline files"),
        candidate ? h("div", { className: "mt-4" },
          h("p", null, "Version " + candidate.version + ", " + candidate.file_count +
            " files from source commit " + candidate.source_commit + "."),
          h("details", { className: "my-3" },
            h("summary", { className: "cursor-pointer" }, "Review file list"),
            h("pre", { className: "max-h-80 overflow-auto whitespace-pre-wrap text-xs" },
              candidate.files.join("\n"))),
          h("button", {
            type: "button", disabled: baselineBusy, onClick: applyBaseline,
            className: "rounded border border-border px-4 py-2 disabled:opacity-50",
          }, baseline?.baseline_exists === true ? "Renew reviewed baseline" : "Create reviewed baseline")) : null,
        baselineStatus ? h("p", { role: "status", className: "mt-3" }, baselineStatus) : null) : null,
      status ? h("p", { role: "status" }, status) : null);
  }

  window.__HERMES_PLUGINS__.register("lifeos-hook-bridge", LifeOSSettings);
})();
