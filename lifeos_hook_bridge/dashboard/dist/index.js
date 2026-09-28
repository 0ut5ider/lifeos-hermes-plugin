// ABOUTME: Renders the bridge settings in a Hermes dashboard plugin tab.
// ABOUTME: Reads and saves fields through the authenticated plugin API.
(function () {
  "use strict";

  const SDK = window.__HERMES_PLUGIN_SDK__;
  const React = SDK.React;
  const h = React.createElement;
  const endpoint = "/api/plugins/lifeos-hook-bridge/settings";

  function LifeOSSettings() {
    const [fields, setFields] = SDK.hooks.useState([]);
    const [values, setValues] = SDK.hooks.useState({});
    const [status, setStatus] = SDK.hooks.useState("Loading settings...");
    const [saving, setSaving] = SDK.hooks.useState(false);

    SDK.hooks.useEffect(function () {
      let active = true;
      SDK.fetchJSON(endpoint).then(function (data) {
        if (!active) return;
        setFields(data.fields);
        setValues(Object.fromEntries(data.fields.map(function (field) {
          return [field.key, field.value ?? ""];
        })));
        setStatus("");
      }).catch(function (error) {
        if (active) setStatus("Could not load settings: " + error.message);
      });
      return function () { active = false; };
    }, []);

    function update(key, value) {
      setValues(function (current) { return Object.assign({}, current, { [key]: value }); });
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

    function renderField(field) {
      const control = field.type === "enum"
        ? h("select", {
          id: field.key,
          value: values[field.key] ?? "",
          onChange: function (event) { update(field.key, event.target.value); },
          className: "w-full rounded border border-border bg-background p-2",
        }, field.choices.map(function (choice) {
          return h("option", { key: choice, value: choice }, choice);
        }))
        : h("input", {
          id: field.key,
          type: "text",
          value: values[field.key] ?? "",
          onChange: function (event) { update(field.key, event.target.value); },
          className: "w-full rounded border border-border bg-background p-2",
        });
      return h("div", { key: field.key, className: "space-y-1" },
        h("label", { htmlFor: field.key, className: "block font-medium" }, field.label),
        control,
        field.description ? h("p", { className: "text-sm text-muted-foreground" }, field.description) : null);
    }

    return h("main", { className: "mx-auto max-w-3xl space-y-6 p-6" },
      h("div", null,
        h("h1", { className: "text-2xl font-semibold" }, "LifeOS Bridge"),
        h("p", { className: "text-muted-foreground" }, "Map LifeOS tiers to Hermes models and effort levels.")),
      h("form", { onSubmit: save, className: "space-y-5" },
        fields.map(renderField),
        fields.length ? h("button", {
          type: "submit", disabled: saving,
          className: "rounded bg-primary px-4 py-2 text-primary-foreground disabled:opacity-50",
        }, saving ? "Saving..." : "Save settings") : null),
      status ? h("p", { role: "status" }, status) : null);
  }

  window.__HERMES_PLUGINS__.register("lifeos-hook-bridge", LifeOSSettings);
})();
