// ABOUTME: Presents prepared complete releases and their authenticated installation controls.
// ABOUTME: Shows operation results across a Hermes restart without exposing preparation logs or credentials.
(function () {
  "use strict";
  const SDK = window.__HERMES_PLUGIN_SDK__;
  const h = SDK.React.createElement;
  const endpoint = "/api/plugins/lifeos-release-manager/operations";

  function MemoryWorkflows() {
    const base = "/api/plugins/lifeos-release-manager/memory-workflows";
    const [operations, setOperations] = SDK.hooks.useState([]);
    const [busy, setBusy] = SDK.hooks.useState(false);
    const [message, setMessage] = SDK.hooks.useState("");
    const [removal, setRemoval] = SDK.hooks.useState({});
    const requests = SDK.hooks.useRef(0);
    const mounted = SDK.hooks.useRef(true);
    async function refresh() {
      const request = ++requests.current;
      try {
        const result = await SDK.fetchJSON(base);
        if (mounted.current && request === requests.current) setOperations(result.operations);
      } catch (error) {
        if (mounted.current && request === requests.current) {
          ++requests.current; setOperations([]); setMessage(error.message);
        }
      }
    }
    SDK.hooks.useEffect(function () {
      mounted.current = true;
      refresh();
      const timer = setInterval(refresh, 5000);
      return function () { mounted.current = false; ++requests.current; clearInterval(timer); };
    }, []);
    async function act(operation, action) {
      ++requests.current;
      setBusy(true); setMessage("");
      try {
        await SDK.fetchJSON(base + "/" + operation.identifier + "/" + action, {
          method: "POST", headers: {"Content-Type": "application/json"},
          body: JSON.stringify({signature: operation.review.signature})
        });
        setMessage("Memory workflow started. Hermes can restart. Refresh this page to check its result.");
        await refresh();
      } catch (error) {
        ++requests.current;
        if (mounted.current) { setOperations([]); setMessage(error.message); }
      }
      finally { if (mounted.current) setBusy(false); }
    }
    async function prepareRemoval(operation) {
      ++requests.current;
      setBusy(true); setMessage("");
      try {
        await SDK.fetchJSON(base, {method: "POST", headers: {"Content-Type": "application/json"},
          body: JSON.stringify({kind: "removal", identifier: operation.identifier,
            signature: operation.review.signature, disable_discord: true})});
        setMessage("Removal preparation started. Review the prepared software changes before application.");
        await refresh();
      } catch (error) {
        ++requests.current;
        if (mounted.current) { setOperations([]); setRemoval({}); setMessage(error.message); }
      } finally { if (mounted.current) setBusy(false); }
    }
    return h("section", {className: "space-y-3 rounded border border-border p-4"},
      h("h2", {className: "text-lg font-semibold"}, "Memory ownership workflows"),
      h("p", null, "Prepare an import activation or provider return from the LifeOS memory page. After a verified return, you can prepare complete LifeOS software removal."),
      h("a", {href: "/lifeos-bridge", className: "underline"}, "Open LifeOS memory controls"),
      h("button", {type: "button", disabled: busy, onClick: refresh}, "Refresh memory workflows"),
      operations.map(function (operation) {
        return h("article", {key: operation.identifier, className: "space-y-2 rounded border border-border p-3"},
          h("p", null, operation.kind + ": " + operation.state),
          h("p", {className: "break-all text-xs"}, "Workflow: " + operation.identifier),
          operation.review.prompt ? h("div", null, h("p", null, "Reviewed replacement Hermes prompt:"),
            h("pre", {className: "whitespace-pre-wrap"}, operation.review.prompt)) : null,
          h("p", null, "Application verified: " + Boolean(operation.receipt?.application_verified) + "."),
          operation.state === "ready" ? h("div", null,
            h("p", null, operation.kind === "activation" ?
              "This operation selects LifeOS memory and restarts Hermes services. The original Hermes memory files stay retained." :
              operation.kind === "removal" ?
              "This operation removes the integration software and selects stock Hermes. It retains built-in memory, native data, exports, and recovery records. Discord stays disabled." :
              "This operation selects the reviewed built-in memory, stops and disables Pulse, and restarts Hermes. It retains native data and exports."),
            operation.kind === "activation" && operation.review.local_owner_access ? h("div", null,
              h("p", null, "Local owner account: " + operation.review.local_owner_access.account),
              h("p", {className: "break-all"}, "Approved profile: " + operation.review.local_owner_access.destination),
              h("p", null, "Selected model: " + operation.review.local_owner_access.provider + " / " + operation.review.local_owner_access.model),
              h("p", {className: "break-all"}, "Approved model route: " + operation.review.local_owner_access.model_route),
              h("p", null, "This activation allows the local owner and selected model route to read and write lasting memory. Other accounts require their own grants.")) : null,
            operation.kind === "removal" ? h("div", null,
              h("p", null, "Stock Hermes commit: " + operation.review.stock_commit),
              h("p", null, "Copy this recovery command before you continue. This integration page closes after removal succeeds."),
              h("code", {className: "break-all"}, operation.review.recovery_command),
              h("p", null, "Run the command with recover or rollback. Recovery requires your dashboard owner username and password.")) : null,
            h("button", {type: "button", disabled: busy, onClick: function () { return act(operation, "apply"); }},
              operation.kind === "activation" ? "Activate reviewed LifeOS ownership" :
              operation.kind === "removal" ? "Remove reviewed LifeOS software" : "Apply reviewed provider return")) : null,
          operation.kind === "return" && operation.state === "verified" && operation.receipt?.application_verified === true ?
            h("div", {className: "space-y-2"},
              h("p", null, "Optional: remove LifeOS software after this verified return. Preparation keeps your data and current Hermes memory."),
              h("label", null, h("input", {type: "checkbox", checked: Boolean(removal[operation.identifier]), disabled: busy,
                onChange: function (event) { setRemoval({...removal, [operation.identifier]: event.target.checked}); }}),
                " I understand that removal disables Discord. Stock Hermes does not include the integration's private-channel restrictions."),
              h("button", {type: "button", disabled: busy || !removal[operation.identifier],
                onClick: function () { return prepareRemoval(operation); }}, "Prepare complete LifeOS removal")) : null,
          ["queued", "interrupted"].includes(operation.state) ? h("button", {type: "button", disabled: busy,
            onClick: function () { return act(operation, "recover"); }}, "Recover memory workflow") : null,
          ["configured", "verified", "verification_required", "interrupted"].includes(operation.state) ?
            h("button", {type: "button", disabled: busy, onClick: function () { return act(operation, "rollback"); }},
              operation.kind === "removal" ? "Restore integration software" : "Restore previous provider settings") : null);
      }), message ? h("p", {role: "status"}, message) : null);
  }

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
      installed === true ? h(MemoryWorkflows) : null,
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
