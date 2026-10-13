// ABOUTME: Presents prepared complete releases and their authenticated installation controls.
// ABOUTME: Shows operation results across a Hermes restart without exposing preparation logs or credentials.
(function () {
  "use strict";
  const SDK = window.__HERMES_PLUGIN_SDK__;
  const h = SDK.React.createElement;
  const endpoint = "/api/plugins/lifeos-release-manager/operations";

  function Releases() {
    const [operations, setOperations] = SDK.hooks.useState([]);
    const [reviewed, setReviewed] = SDK.hooks.useState(null);
    const [message, setMessage] = SDK.hooks.useState("");
    const [busy, setBusy] = SDK.hooks.useState(false);
    const [installed, setInstalled] = SDK.hooks.useState(null);
    const [version, setVersion] = SDK.hooks.useState("");
    const [name, setName] = SDK.hooks.useState("User");
    const [assistant, setAssistant] = SDK.hooks.useState("Hermes");

    async function refresh() {
      const result = await SDK.fetchJSON(endpoint);
      setOperations(result.operations);
    }

    SDK.hooks.useEffect(function () {
      let active = true;
      function poll() {
        return Promise.all([SDK.fetchJSON(endpoint), SDK.fetchJSON("/api/plugins/lifeos-release-manager/installation")]).then(function (results) {
          if (active) {
            setOperations(results[0].operations);
            setInstalled(results[1].installed);
          }
        }).catch(function () {
          if (active) setMessage("Release status needs an authenticated installation owner.");
        });
      }
      poll();
      const timer = setInterval(poll, 5000);
      return function () { active = false; clearInterval(timer); };
    }, []);

    async function prepare(intent) {
      setBusy(true);
      setReviewed(null);
      try {
        const selection = {intent: intent};
        if (version.trim()) selection.version = version.trim();
        if (intent === "install") {
          selection.name = name;
          selection.assistant = assistant;
        }
        await SDK.fetchJSON("/api/plugins/lifeos-release-manager/prepare", {
          method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(selection)
        });
        setMessage("Preparation started. You can leave this page. Review the prepared release before installation.");
        await refresh();
      } catch (error) {
        setMessage(error.message);
      } finally {
        setBusy(false);
      }
    }

    async function action(identifier, name) {
      setBusy(true);
      try {
        const result = await SDK.fetchJSON(endpoint + "/" + identifier + "/" + name, {method: "POST"});
        if (name === "review") {
          setReviewed(result);
          setMessage("");
        } else {
          setReviewed(null);
          setMessage("Release operation started. Hermes can restart. Refresh this page to check the result.");
          await refresh();
        }
      } catch (error) {
        setMessage(error.message);
      } finally {
        setBusy(false);
      }
    }

    return h("section", {className: "space-y-4 p-6"},
      h("h1", {className: "text-2xl font-semibold"}, "LifeOS releases"),
      h("p", null, "Prepare a release with these controls or ask Hermes in chat. Review the prepared release before installation."),
      h("p", null, "All update actions prepare the complete tested package: Hermes, LifeOS, the bridge, and the release manager. Your personal data and model settings stay in place."),
      h("label", {className: "block"}, "Release version (leave blank for latest stable)",
        h("input", {type: "text", value: version, disabled: busy, placeholder: "Latest stable",
          className: "block rounded border border-border bg-background p-2", onChange: function (event) { setVersion(event.target.value); }})),
      installed === false ? h("div", {className: "space-y-2"},
        h("label", {className: "block"}, "Your name", h("input", {type: "text", value: name, disabled: busy,
          className: "block rounded border border-border bg-background p-2", onChange: function (event) { setName(event.target.value); }})),
        h("label", {className: "block"}, "Assistant name", h("input", {type: "text", value: assistant, disabled: busy,
          className: "block rounded border border-border bg-background p-2", onChange: function (event) { setAssistant(event.target.value); }}))) : null,
      h("div", {className: "flex flex-wrap gap-2"},
        [["Install LifeOS", "install", installed !== false], ["Update LifeOS", "update", installed !== true],
          ["Update plugin", "plugin", installed !== true]].map(function (entry) {
          return h("button", {key: entry[1], type: "button",
            disabled: busy || entry[2] || operations.some(function (operation) {
              return ["preparing", "applying", "recovering", "restoring", "recovery_required"].includes(operation.state)
                || operation.state.startsWith("queued-");
            }),
            onClick: function () { return prepare(entry[1]); },
            className: "rounded border border-border px-4 py-2 disabled:opacity-50"}, entry[0]);
        })),
      h("button", {type: "button", disabled: busy, onClick: async function () {
        try { await refresh(); setMessage(""); }
        catch (error) { setMessage(error.message); }
      }, className: "rounded border border-border px-4 py-2"}, "Refresh status"),
      operations.map(function (operation) {
        return h("article", {key: operation.identifier, className: "space-y-2 rounded border border-border p-4"},
          h("p", null, "Release " + (operation.version ?? "preparation") + ": " + operation.state),
          h("p", {className: "break-all text-sm"}, "Operation: " + operation.identifier),
          operation.error ? h("p", {role: "status"}, operation.error) : null,
          operation.state === "ready" ? h("button", {type: "button", disabled: busy,
            onClick: function () { return action(operation.identifier, "review"); }}, "Review release") : null,
          operation.restore_available ? h("button", {type: "button", disabled: busy,
            onClick: function () { return action(operation.identifier, "restore"); }}, "Restore prior programs") : null,
          operation.recover_available ? h("button", {type: "button", disabled: busy,
            onClick: function () { return action(operation.identifier, "recover"); }}, "Recover operation") : null);
      }),
      reviewed ? h("article", {className: "space-y-2 rounded border border-border p-4"},
        h("h2", {className: "text-lg font-semibold"}, "Install release " + reviewed.version),
        h("p", null, reviewed.restart_required ? "Hermes services will restart during this update." : "The prepared integration will become available to this profile."),
        h("p", null, "Program commit: " + reviewed.commit),
        h("p", {className: "break-all text-sm"}, "Package SHA-256: " + reviewed.package_sha256),
        h("button", {type: "button", disabled: busy, onClick: function () {
          return action(reviewed.identifier, "apply");
        }, className: "rounded bg-primary px-4 py-2 text-primary-foreground"}, "Install this release")) : null,
      message ? h("p", {role: "status"}, message) : null);
  }
  window.__HERMES_PLUGINS__.register("lifeos-release-manager", Releases);
})();
