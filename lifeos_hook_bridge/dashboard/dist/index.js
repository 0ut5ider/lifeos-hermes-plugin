// ABOUTME: Maps each LifeOS tier to a configured Hermes provider, model, and effort.
// ABOUTME: Uses Hermes's authenticated model catalog and the bridge settings API.
(function () {
  "use strict";

  const SDK = window.__HERMES_PLUGIN_SDK__;
  const React = SDK.React;
  const h = React.createElement;
  const endpoint = "/api/plugins/lifeos-hook-bridge/settings";
  const modelEndpoint = "/api/model/options?explicit_only=1";
  const tiers = ["haiku", "sonnet", "opus", "fable"];

  function LifeOSSettings() {
    const [fields, setFields] = SDK.hooks.useState([]);
    const [values, setValues] = SDK.hooks.useState({});
    const [models, setModels] = SDK.hooks.useState([]);
    const [status, setStatus] = SDK.hooks.useState("Loading settings...");
    const [saving, setSaving] = SDK.hooks.useState(false);

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
      h("form", { onSubmit: save, className: "space-y-4" },
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
        }, saving ? "Saving..." : "Save settings") : null),
      status ? h("p", { role: "status" }, status) : null);
  }

  window.__HERMES_PLUGINS__.register("lifeos-hook-bridge", LifeOSSettings);
})();
