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

    async function refresh() {
      const result = await SDK.fetchJSON(endpoint);
      setOperations(result.operations);
    }

    SDK.hooks.useEffect(function () {
      let active = true;
      SDK.fetchJSON(endpoint).then(function (result) {
        if (active) setOperations(result.operations);
      }).catch(function () {
        if (active) setMessage("Release status needs an authenticated installation owner.");
      });
      return function () { active = false; };
    }, []);

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
      h("p", null, "Ask Hermes to prepare a LifeOS integration release. Review the prepared release here before installation."),
      h("button", {type: "button", disabled: busy, onClick: async function () {
        try { await refresh(); setMessage(""); }
        catch (error) { setMessage(error.message); }
      }, className: "rounded border border-border px-4 py-2"}, "Refresh status"),
      operations.map(function (operation) {
        return h("article", {key: operation.identifier, className: "space-y-2 rounded border border-border p-4"},
          h("p", null, "Release " + (operation.version ?? "preparation") + ": " + operation.state),
          operation.state === "ready" ? h("button", {type: "button", disabled: busy,
            onClick: function () { return action(operation.identifier, "review"); }}, "Review release") : null,
          operation.state === "applied" ? h("button", {type: "button", disabled: busy,
            onClick: function () { return action(operation.identifier, "restore"); }}, "Restore prior programs") : null,
          operation.state === "recovery_required" ? h("button", {type: "button", disabled: busy,
            onClick: function () { return action(operation.identifier, "recover"); }}, "Recover operation") : null);
      }),
      reviewed ? h("article", {className: "space-y-2 rounded border border-border p-4"},
        h("h2", {className: "text-lg font-semibold"}, "Install release " + reviewed.version),
        h("p", null, reviewed.restart_required ? "Hermes services will restart during this update." : "The prepared integration will become available to this profile."),
        h("p", null, "Program commit: " + reviewed.commit),
        h("button", {type: "button", disabled: busy, onClick: function () {
          return action(reviewed.identifier, "apply");
        }, className: "rounded bg-primary px-4 py-2 text-primary-foreground"}, "Install this release")) : null,
      message ? h("p", {role: "status"}, message) : null);
  }
  window.__HERMES_PLUGINS__.register("lifeos-release-manager", Releases);
})();
