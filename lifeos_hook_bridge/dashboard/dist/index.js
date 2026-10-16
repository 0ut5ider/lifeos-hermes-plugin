// ABOUTME: Maps each LifeOS tier to a configured Hermes provider, model, and effort.
// ABOUTME: Uses Hermes's authenticated model catalog and the bridge settings API.
(function () {
  "use strict";

  const SDK = window.__HERMES_PLUGIN_SDK__;
  const React = SDK.React;
  const h = React.createElement;
  const endpoint = "/api/plugins/lifeos-hook-bridge/settings";
  const installationEndpoint = "/api/plugins/lifeos-hook-bridge/installation";
  const hostPatchEndpoint = installationEndpoint + "/host-patch";
  const lifeosUpdateEndpoint = installationEndpoint + "/update";
  const baselineEndpoint = "/api/plugins/lifeos-hook-bridge/version-drift";
  const modelEndpoint = "/api/model/options?explicit_only=1";
  const tiers = ["haiku", "sonnet", "opus", "fable"];

  function MemoryImportReview() {
    const base = "/api/plugins/lifeos-hook-bridge/memory/import";
    const [review, setReview] = SDK.hooks.useState(null);
    const [snapshot, setSnapshot] = SDK.hooks.useState(null);
    const [decisions, setDecisions] = SDK.hooks.useState({});
    const [plan, setPlan] = SDK.hooks.useState(null);
    const [publication, setPublication] = SDK.hooks.useState(null);
    const [busy, setBusy] = SDK.hooks.useState(false);
    const [message, setMessage] = SDK.hooks.useState("");
    const [resumeId, setResumeId] = SDK.hooks.useState("");
    const [resumeSignature, setResumeSignature] = SDK.hooks.useState("");
    const [sourceLabel, setSourceLabel] = SDK.hooks.useState("");
    const [uploads, setUploads] = SDK.hooks.useState({});
    const [portableUpload, setPortableUpload] = SDK.hooks.useState("");

    async function post(path, body) {
      return SDK.fetchJSON(base + path, { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body) });
    }
    function binding() {
      return { identifier: snapshot.identifier, snapshot_signature: snapshot.snapshot_signature };
    }
    async function run(operation) {
      setBusy(true); setMessage("");
      try { await operation(); }
      catch (error) {
        setReview(null); setSnapshot(null); setPlan(null); setPublication(null); setDecisions({});
        setUploads({});
        setPortableUpload("");
        setMessage(error.message);
      } finally { setBusy(false); }
    }
    function draft(identifier, field, value) {
      setDecisions(function (current) { return { ...current, [identifier]: { ...current[identifier], [field]: value } }; });
      setPlan(null); setPublication(null);
    }
    async function begin(sourceIdentifier) {
      setReview(null); setSnapshot(null); setPlan(null); setPublication(null);
      const source = sourceIdentifier ? { source_identifier: sourceIdentifier } : {};
      const current = await post("/preview", source);
      const saved = await post("/snapshot", { signature: current.signature, ...source });
      const selected = {};
      for (const source of current.sources) {
        for (const item of source.chunks.filter(function (chunk) { return chunk.content; })) {
          selected[item.id] = { id: item.id, action: "pending", required: true,
            reason: "Awaiting owner review.", category: item.source_category ?? (source.path.endsWith("USER.md") ? "principal" : "project"),
            content: item.content, title: "Imported Hermes memory", project: item.source_project ?? "" };
        }
      }
      setDecisions(selected); setReview(current); setSnapshot(saved);
      setResumeId(saved.identifier); setResumeSignature(saved.snapshot_signature);
    }
    async function prepare() {
      const items = Object.values(decisions).map(function (item) {
        if (item.action === "import") return { id: item.id, action: item.action, required: item.required,
          category: item.category, content: item.content, title: item.title, project: item.project };
        return { id: item.id, action: item.action, required: item.required, reason: item.reason };
      });
      setPlan(await post("/plan", { ...binding(), decisions: items }));
    }
    async function refresh() {
      const request = snapshot ? binding() : { identifier: resumeId, snapshot_signature: resumeSignature };
      const result = await post("/status", request);
      setReview(result.review); setSnapshot({ ...request }); setPlan(result.plan); setPublication(result.publication);
      if (!result.plan) setMessage("This saved review has no plan. Start a fresh review to choose the items.");
    }
    function field(item, key, label, multiline) {
      const id = "import_" + item.id + "_" + key;
      return h("label", { htmlFor: id, className: "block text-sm" }, label,
        h(multiline ? "textarea" : "input", { id: id, value: item[key], disabled: busy || Boolean(plan),
          className: "block w-full rounded border border-border bg-background p-2",
          onChange: function (event) { draft(item.id, key, event.target.value); } }));
    }
    return h("details", { id: "memory_import" },
      h("summary", { className: "cursor-pointer font-semibold" }, "Import Hermes memory"),
      h("div", { className: "space-y-3 pt-3" },
        h("p", null, "Review each entry before publication. Source files stay intact. Import does not switch your memory provider."),
        h("button", { type: "button", disabled: busy, onClick: function () { return run(function () { return begin(); }); } }, "Review Hermes memory"),
        h("details", null, h("summary", null, "Import files from another Hermes profile"),
          h("p", null, "Choose original MEMORY.md or USER.md files. They are copied privately for review and do not replace this profile's files."),
          h("label", null, "Source label", h("input", { value: sourceLabel, disabled: busy, maxLength: 256,
            onChange: function (event) { setSourceLabel(event.target.value); } })),
          ["MEMORY.md", "USER.md"].map(function (name) { return h("label", { key: name, className: "block" }, name,
            h("input", { type: "file", accept: ".md,text/plain,text/markdown", disabled: busy,
              onChange: function (event) {
                const file = event.target.files[0];
                return run(async function () {
                  if (!file) { setUploads(function (current) { const next = { ...current }; delete next[name]; return next; }); return; }
                  if (file.size > 1024 * 1024) throw new Error("Each source file must be at most 1 MiB.");
                  const bytes = new Uint8Array(await file.arrayBuffer());
                  let binary = "";
                  for (const value of bytes) binary += String.fromCharCode(value);
                  const encoded = window.btoa(binary);
                  setUploads(function (current) { return { ...current, [name]: encoded }; });
                });
              } })); }),
          h("button", { type: "button", disabled: busy || !sourceLabel.trim() || !Object.keys(uploads).length,
            onClick: function () { return run(async function () {
              const source = await post("/upload", { label: sourceLabel, files: uploads });
              setUploads({}); await begin(source.identifier);
            }); } }, "Upload files for review")),
        h("details", null, h("summary", null, "Import a portable LifeOS bundle"),
          h("p", null, "The review includes retained overflow. Excluded and known retired source items cannot be published through this import."),
          h("label", null, "Portable memory JSON file", h("input", { type: "file", accept: ".json,application/json", disabled: busy,
            onChange: function (event) {
              const file = event.target.files[0];
              return run(async function () {
                if (!file) { setPortableUpload(""); return; }
                if (file.size > 16 * 1024 * 1024) throw new Error("A portable bundle must be at most 16 MiB.");
                const bytes = new Uint8Array(await file.arrayBuffer());
                let binary = "";
                for (const value of bytes) binary += String.fromCharCode(value);
                setPortableUpload(window.btoa(binary));
              });
            } })),
          h("button", { type: "button", disabled: busy || !portableUpload,
            onClick: function () { return run(async function () {
              const source = await post("/upload", { label: "Uploaded portable LifeOS bundle", bundle_bytes: portableUpload });
              setPortableUpload(""); await begin(source.identifier);
            }); } }, "Upload portable bundle for review")),
        h("details", null, h("summary", null, "Resume a saved import"),
          h("label", null, "Import identifier", h("input", { value: resumeId, disabled: busy,
            onChange: function (event) { setResumeId(event.target.value); setSnapshot(null); } })),
          h("label", null, "Snapshot signature", h("input", { value: resumeSignature, disabled: busy,
            onChange: function (event) { setResumeSignature(event.target.value); setSnapshot(null); } })),
          h("button", { type: "button", disabled: busy || !resumeId || !resumeSignature,
            onClick: function () { return run(refresh); } }, "Load saved import")),
        message ? h("p", { role: "status" }, message) : null,
        review ? h("div", { className: "space-y-3" },
          h("p", null, "Target: " + review.installed + ". Principal: " + review.principal + "."),
          h("p", null, "Source: " + (review.source_origin?.label ?? "Selected Hermes profile") + "."),
          h("p", null, "Possible meaning conflicts require manual review. Exact duplicate and retirement checks do not detect every contradiction."),
          h("details", null, h("summary", null, "Current readers"),
            h("pre", { className: "whitespace-pre-wrap" }, JSON.stringify(review.readers, null, 2))),
          h("p", { className: "text-xs break-all" }, "Import identifier: " + snapshot.identifier + ". Snapshot signature: " + snapshot.snapshot_signature),
          review.sources.map(function (source) {
            return h("div", { key: source.path, className: "space-y-2" }, h("h4", null, source.path + ": " + source.status),
              source.chunks.filter(function (chunk) { return chunk.content; }).map(function (chunk) {
                const item = decisions[chunk.id];
                if (!item) return h("p", { key: chunk.id, className: "whitespace-pre-wrap" }, chunk.content);
                return h("article", { key: chunk.id, className: "rounded border border-border p-3 space-y-2" },
                  h("p", { className: "whitespace-pre-wrap" }, chunk.content),
                  h("p", null, "Original author and date: unknown. Exact matches: " + chunk.exact_native_matches.length +
                    ". Known retired claim: " + Boolean(chunk.retired_claim) + ". Source status: " + chunk.disposition + "."),
                  chunk.source_reference ? h("p", null, "Source reference: " + chunk.source_reference.id +
                    ", revision " + chunk.source_reference.revision + ". Source category: " + chunk.source_category + ".") : null,
                  chunk.source_origin ? h("details", null, h("summary", null, "Source provenance"),
                    h("pre", { className: "whitespace-pre-wrap" }, JSON.stringify(chunk.source_origin, null, 2))) : null,
                  h("label", null, "Decision", h("select", { value: item.action, disabled: busy || Boolean(plan),
                    onChange: function (event) { draft(item.id, "action", event.target.value); } },
                    ["pending", "import", "exclude"].map(function (action) { return h("option", { key: action, value: action }, action); }))),
                  h("label", null, h("input", { type: "checkbox", checked: item.required, disabled: busy || Boolean(plan),
                    onChange: function (event) { draft(item.id, "required", event.target.checked); } }), " Required for complete import"),
                  item.action === "import" ? h("div", null,
                    h("label", null, "Category", h("select", { value: item.category, disabled: busy || Boolean(plan),
                      onChange: function (event) { draft(item.id, "category", event.target.value); } },
                      ["principal", "assistant", "project"].map(function (category) { return h("option", { key: category, value: category }, category); }))),
                    field(item, "content", "Text to publish", true), field(item, "title", "Title", false),
                    item.category === "project" ? field(item, "project", "Project", false) : null) : field(item, "reason", "Reason", false));
              }));
          }),
          !plan && Object.keys(decisions).length ? h("button", { type: "button", disabled: busy,
            onClick: function () { return run(prepare); } }, "Review publication plan") : null,
          plan ? h("div", { className: "space-y-2" },
            h("h4", null, "Publication plan"),
            plan.items.map(function (item) { return h("article", { key: item.id, className: "rounded border border-border p-2" },
              h("p", null, item.action + ": " + (item.content ?? item.reason)),
              item.destination ? h("p", null, "Destination: " + item.destination) : null,
              item.transformation ? h("p", { className: "whitespace-pre-wrap" }, "Published text: " + item.transformation.published) : null); }),
            h("p", null, "Required held or excluded entries keep this import incomplete. No existing entry is evicted."),
            h("button", { type: "button", disabled: busy, onClick: function () { return run(async function () {
              setPublication(await post("/apply", { ...binding(), plan_signature: plan.signature }));
            }); } }, "Apply reviewed import"),
            h("button", { type: "button", disabled: busy, onClick: function () { return run(refresh); } }, "Check import status")) : null,
          publication ? h("div", { role: "status" },
            h("p", null, "Import state: " + publication.state + ". Required entries verified: " + publication.required_items_verified + "."),
            publication.state === "published" && publication.required_items_verified && !review.ownership_enabled ?
              h("div", { className: "space-y-2" },
                h("p", null, "Prepare a separate ownership review to use LifeOS memory in new Hermes sessions. The preparation saves a private backup and restarts Hermes services."),
                h("button", { type: "button", disabled: busy, onClick: function () { return run(async function () {
                  const result = await SDK.fetchJSON("/api/plugins/lifeos-release-manager/memory-workflows", {
                    method: "POST", headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ kind: "activation", ...binding(), plan_signature: plan.signature }) });
                  setMessage("Ownership review started. Workflow: " + result.identifier + ". Open LifeOS releases to review the cutover.");
                }); } }, "Prepare LifeOS ownership activation"),
                h("a", { href: "/lifeos-releases", className: "underline" }, "Open LifeOS releases")) : null,
            publication.reason ? h("p", null, publication.reason) : null,
            publication.items.map(function (item) { return h("p", { key: item.id }, item.action + ": " +
              (item.receipt?.reference ? item.receipt.reference.id + ", revision " + item.receipt.reference.revision : "No published reference") +
              ". Current verification: " + item.verified + "."); })) : null) : null));
  }

  function MemoryExportReview() {
    const base = "/api/plugins/lifeos-hook-bridge/memory/export";
    const [review, setReview] = SDK.hooks.useState(null);
    const [snapshot, setSnapshot] = SDK.hooks.useState(null);
    const [decisions, setDecisions] = SDK.hooks.useState({});
    const [plan, setPlan] = SDK.hooks.useState(null);
    const [receipt, setReceipt] = SDK.hooks.useState(null);
    const [busy, setBusy] = SDK.hooks.useState(false);
    const [message, setMessage] = SDK.hooks.useState("");
    const [prompt, setPrompt] = SDK.hooks.useState("");
    async function post(path, body) {
      return SDK.fetchJSON(base + path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    }
    function binding() { return { identifier: snapshot.identifier, signature: snapshot.signature }; }
    async function run(operation) {
      setBusy(true); setMessage("");
      try { await operation(); }
      catch (error) { setReview(null); setSnapshot(null); setPlan(null); setReceipt(null); setDecisions({}); setMessage(error.message); }
      finally { setBusy(false); }
    }
    async function begin() {
      setReview(null); setPlan(null); setReceipt(null);
      const current = await post("/preview", {});
      const saved = await post("/snapshot", { signature: current.signature });
      const selected = {};
      for (const item of current.items) selected[item.id] = { id: item.id, action: "retain", required: true,
        reason: "Awaiting owner review.", content: item.content, file: item.category === "principal" ? "USER.md" : "MEMORY.md" };
      setReview(current); setSnapshot(saved); setDecisions(selected);
    }
    function draft(id, field, value) {
      setDecisions(function (current) { return { ...current, [id]: { ...current[id], [field]: value } }; });
      setPlan(null); setReceipt(null);
    }
    async function prepare() {
      const selected = Object.values(decisions).map(function (item) {
        return item.action === "export" ? { id: item.id, action: item.action, required: item.required, file: item.file, content: item.content } :
          { id: item.id, action: item.action, required: item.required, reason: item.reason };
      });
      setPlan(await post("/plan", { ...binding(), decisions: selected }));
    }
    async function download() {
      const response = await SDK.authedFetch(base + "/download", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(binding()) });
      if (!response.ok) throw new Error("Export download is unavailable. Refresh the owner session and review the source state.");
      const url = window.URL.createObjectURL(await response.blob());
      try {
        const link = window.document.createElement("a"); link.href = url; link.download = "lifeos-portable-memory.json";
        window.document.body.appendChild(link); link.click(); link.remove();
      } finally { window.URL.revokeObjectURL(url); }
    }
    return h("details", { id: "memory_export" }, h("summary", { className: "cursor-pointer font-semibold" }, "Export memory and return to Hermes"),
      h("div", { className: "space-y-3 pt-3" },
        h("p", null, "Export current facts and review the active Hermes entries. The bundle retains overflow. Export does not switch providers or remove LifeOS."),
        h("button", { type: "button", disabled: busy, onClick: function () { return run(begin); } }, "Review reverse export"),
        message ? h("p", { role: "status" }, message) : null,
        review ? h("div", { className: "space-y-3" },
          h("p", null, "Hermes limits: MEMORY.md " + review.settings.memory_char_limit + " characters; USER.md " + review.settings.user_char_limit + " characters."),
          h("p", null, "Every item starts retained. Required items must be exported before provider return. Existing Hermes entries also require a decision."),
          review.items.map(function (source) {
            const item = decisions[source.id];
            return h("article", { key: source.id, className: "rounded border border-border p-3 space-y-2" },
              h("p", { className: "whitespace-pre-wrap" }, source.content),
              h("p", null, source.category + (source.project ? ", project " + source.project : "") +
                (source.reference ? ", reference " + source.reference.id + ", revision " + source.reference.revision : ". Preserved Hermes occurrence") + "."),
              h("p", null, "Known retired claim: " + source.retired_claim + ". Quarantined: " + source.quarantined + "."),
              h("label", null, "Decision", h("select", { value: item.action, disabled: busy || Boolean(plan),
                onChange: function (event) { draft(item.id, "action", event.target.value); } },
                ["retain", "export", "exclude"].map(function (action) { return h("option", { key: action, value: action }, action); }))),
              h("label", null, h("input", { type: "checkbox", checked: item.required, disabled: busy || Boolean(plan),
                onChange: function (event) { draft(item.id, "required", event.target.checked); } }), " Required for provider return"),
              item.action === "export" ? h("div", null,
                h("label", null, "Hermes file", h("select", { value: item.file, disabled: busy || Boolean(plan),
                  onChange: function (event) { draft(item.id, "file", event.target.value); } },
                  ["MEMORY.md", "USER.md"].map(function (file) { return h("option", { key: file, value: file }, file); }))),
                h("label", null, "Text to export", h("textarea", { value: item.content, disabled: busy || Boolean(plan),
                  className: "block w-full rounded border border-border bg-background p-2",
                  onChange: function (event) { draft(item.id, "content", event.target.value); } }))) :
                h("label", null, "Reason", h("input", { value: item.reason, disabled: busy || Boolean(plan),
                  onChange: function (event) { draft(item.id, "reason", event.target.value); } })));
          }),
          !plan ? h("button", { type: "button", disabled: busy, onClick: function () { return run(prepare); } }, "Review export plan") : null,
          plan ? h("div", { className: "space-y-2" },
            Object.entries(plan.files).map(function (entry) { return h("div", { key: entry[0] },
              h("p", null, entry[0] + ": " + Array.from(entry[1]).length + "/" + plan.limits[entry[0]] + " characters."),
              h("pre", { className: "whitespace-pre-wrap" }, entry[1])); }),
            h("p", null, "Ready for provider return: " + plan.ready_for_return + ". Retained items remain outside active Hermes recall."),
            h("button", { type: "button", disabled: busy, onClick: function () { return run(async function () {
              setReceipt(await post("/apply", { ...binding(), plan_signature: plan.signature }));
            }); } }, "Create reviewed export")) : null,
          receipt ? h("div", { role: "status" }, h("p", null, "Export state: " + receipt.state + "."),
            h("p", { className: "text-xs break-all" }, "Export identifier: " + snapshot.identifier + ". Signature: " + snapshot.signature),
            h("button", { type: "button", disabled: busy, onClick: function () { return run(download); } }, "Download portable memory"),
            plan.ready_for_return && receipt.state === "exported" ? h("div", { className: "space-y-2" },
              h("p", null, "Return selects built-in Hermes memory, replaces the LifeOS prompt, stops Pulse, and restarts Hermes. Native data and the complete export remain retained."),
              h("label", null, "Replacement Hermes prompt", h("textarea", { value: prompt, disabled: busy,
                className: "block w-full rounded border border-border bg-background p-2",
                onChange: function (event) { setPrompt(event.target.value); } })),
              h("button", { type: "button", disabled: busy || !prompt.trim(), onClick: function () { return run(async function () {
                const result = await SDK.fetchJSON("/api/plugins/lifeos-release-manager/memory-workflows", {
                  method: "POST", headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({ kind: "return", ...binding(), plan_signature: plan.signature, prompt: prompt }) });
                setMessage("Provider return review prepared. Workflow: " + result.identifier + ". Open LifeOS releases to review and apply it.");
              }); } }, "Prepare return to built-in Hermes"),
              h("a", { href: "/lifeos-releases", className: "underline" }, "Open LifeOS releases")) : null) : null) : null));
  }

  function MemoryHTTPPreferences() {
    const base = "/api/plugins/lifeos-hook-bridge/memory/http";
    const [settings, setSettings] = SDK.hooks.useState(null);
    const [origin, setOrigin] = SDK.hooks.useState("");
    const [client, setClient] = SDK.hooks.useState("");
    const [projects, setProjects] = SDK.hooks.useState("");
    const [route, setRoute] = SDK.hooks.useState("unknown");
    const [principal, setPrincipal] = SDK.hooks.useState(false);
    const [assistant, setAssistant] = SDK.hooks.useState(false);
    const [write, setWrite] = SDK.hooks.useState(false);
    const [token, setToken] = SDK.hooks.useState("");
    const [callback, setCallback] = SDK.hooks.useState("");
    const [message, setMessage] = SDK.hooks.useState("");
    const [busy, setBusy] = SDK.hooks.useState(false);

    async function refresh() {
      const value = await SDK.fetchJSON(base + "/settings");
      setSettings(value); setOrigin(value.public_url);
    }
    SDK.hooks.useEffect(function () { refresh().catch(function (error) { setMessage(error.message); }); }, []);
    async function run(operation) {
      setBusy(true); setMessage(""); setCallback("");
      try { await operation(); await refresh(); }
      catch (error) { setToken(""); setMessage(error.message); }
      finally { setBusy(false); }
    }
    function post(path, body) {
      return SDK.fetchJSON(base + path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    }
    function field(id, label, value, setter) {
      return h("label", { htmlFor: id, className: "block text-sm" }, label,
        h("input", { id: id, value: value, required: true, disabled: busy,
          className: "block w-full rounded border border-border bg-background p-2",
          onChange: function (event) { setter(event.target.value); } }));
    }
    function permission(id, label, value, setter) {
      return h("label", { htmlFor: id, className: "block text-sm" },
        h("input", { id: id, type: "checkbox", checked: value, disabled: busy,
          onChange: function (event) { setter(event.target.checked); } }), " " + label);
    }
    function grant() {
      const read = ["project"]; if (principal) read.push("principal"); if (assistant) read.push("assistant");
      return { client: client, read: read, projects: projects.split(",").map(function (value) { return value.trim(); }).filter(Boolean),
        model_route: route, write_project: write };
    }
    function authorize(request, decision) {
      return run(async function () {
        const result = await post("/authorization/" + encodeURIComponent(request.id),
          decision === "approve" ? { decision: decision, grant: grant() } : { decision: decision });
        setCallback(result.redirect_url);
      });
    }
    const validGrant = Boolean(client.trim() && projects.trim() && route.trim());
    return h("details", { id: "memory_http" },
      h("summary", { className: "cursor-pointer font-semibold" }, "Connect agents over HTTP"),
      h("div", { className: "space-y-3 pt-3" },
        h("p", null, "Use Tailscale Serve for private HTTPS access from your computers. Each agent still needs owner-approved memory permissions. Tailscale is optional."),
        h("p", null, "Serve this dashboard's origin without a path rewrite. Use Tailscale Serve, which limits access to your tailnet. Keep dashboard sign-in enabled."),
        h("form", { id: "http_settings", onSubmit: function (event) {
          event.preventDefault(); return run(function () { return post("/settings", { enabled: true, public_url: origin }); });
        } }, field("http_public_url", "Public HTTPS origin (for example https://hermes.example.ts.net)", origin, setOrigin),
          h("button", { type: "submit", disabled: busy || !origin.trim() }, "Save and enable HTTP MCP")),
        settings?.enabled ? h("button", { type: "button", disabled: busy, onClick: function () {
          return run(function () { setToken(""); return post("/settings", { enabled: false, public_url: settings.public_url }); });
        } }, "Disable HTTP MCP and invalidate credentials") : null,
        h("p", null, "Changing the origin or disabling HTTP invalidates existing credentials. Add a fresh connection afterward."),
        settings?.mcp_url ? h("label", { className: "block" }, "MCP URL",
          h("input", { readOnly: true, value: settings.mcp_url, className: "block w-full p-2" })) : null,
        h("button", { type: "button", disabled: busy, onClick: function () { return run(refresh); } }, "Review connection requests"),
        h("button", { type: "button", disabled: busy, onClick: function () {
          return run(function () { return post("/registrations/clear", {}); });
        } }, "Clear unused OAuth registrations"),
        h("p", null, "Clearing removes unused registrations and waiting sign-in requests. Active connections keep their credentials."),
        settings && !settings.sharing_enabled ? h("p", null,
          "Memory sharing is disabled. Enable memory sharing above before agent sign-in. Approving a request or creating a token enables sharing for all enabled connections.") : null,
        h("p", null, "Add the MCP URL in your agent, then sign in. Review its name and callback below. Choose permissions before approving. Client names and declared model routes are unverified."),
        h("p", null, "A cloud model can receive every fact returned through this connection. Project access starts read-only. Use a distinct name for each connection."),
        h("form", { id: "http_enrollment", onSubmit: function (event) {
          event.preventDefault(); return run(async function () { const result = await post("/connections", grant()); setToken(result.token); });
        } }, field("http_client", "Connection name", client, setClient),
          field("http_projects", "Projects (comma separated; * permits all projects)", projects, setProjects),
          field("http_model_route", "Declared model route", route, setRoute),
          permission("http_principal", "Allow reading owner preferences and identity", principal, setPrincipal),
          permission("http_assistant", "Allow reading assistant preferences", assistant, setAssistant),
          permission("http_write", "Allow writing project facts", write, setWrite),
          h("button", { type: "submit", disabled: busy || !settings?.enabled || !validGrant }, "Create agent token (90 days)")),
        token ? h("div", null,
          h("p", null, "Store this token privately in your agent. The server shows it once. Use the Authorization: Bearer header. Do not put it in a URL or chat."),
          h("textarea", { readOnly: true, value: token, spellCheck: false, autoComplete: "off", className: "block w-full p-2" }),
          h("button", { type: "button", onClick: function () { setToken(""); } }, "Hide token")) : null,
        (settings?.pending ?? []).map(function (request) { return h("article", { key: request.id, className: "rounded border p-3" },
          h("p", null, "Agent requests access: " + request.client_name),
          h("p", null, "Callback: " + request.redirect_uri),
          h("p", null, "Approval uses the permissions selected above."),
          h("button", { type: "button", disabled: busy || !validGrant, onClick: function () { return authorize(request, "approve"); } }, "Approve " + request.client_name),
          h("button", { type: "button", disabled: busy, onClick: function () { return authorize(request, "deny"); } }, "Deny " + request.client_name)); }),
        callback ? h("a", { href: callback, referrerPolicy: "no-referrer", rel: "noreferrer" }, "Return to agent") : null,
        (settings?.connections ?? []).map(function (connection) { return h("article", { key: connection.client, className: "rounded border p-3" },
          h("p", null, connection.client + ": " + (connection.enabled ? "enabled" : "revoked")),
          h("p", null, "Reads: " + connection.read.join(", ") + ". Writes: " + (connection.write.join(", ") || "none") + ". Projects: " + connection.projects.join(", ")),
          connection.enabled ? h("button", { type: "button", disabled: busy, onClick: function () {
            return run(function () { setToken(""); return SDK.fetchJSON(base + "/connections/" + encodeURIComponent(connection.client), { method: "DELETE" }); });
          } }, "Revoke HTTP " + connection.client) : null); }),
        message ? h("p", { role: "status" }, message) : null));
  }

  function MemoryPreferences() {
    const memoryEndpoint = "/api/plugins/lifeos-hook-bridge/memory";
    const [memory, setMemory] = SDK.hooks.useState(null);
    const [message, setMessage] = SDK.hooks.useState("Loading memory status...");
    const [busy, setBusy] = SDK.hooks.useState(false);
    const [query, setQuery] = SDK.hooks.useState("");
    const [results, setResults] = SDK.hooks.useState([]);
    const [proposals, setProposals] = SDK.hooks.useState(null);
    const [drafts, setDrafts] = SDK.hooks.useState({});
    const [adoption, setAdoption] = SDK.hooks.useState(null);
    const [assignments, setAssignments] = SDK.hooks.useState({});
    const [adoptionRequest, setAdoptionRequest] = SDK.hooks.useState("");
    const [sourcePage, setSourcePage] = SDK.hooks.useState(0);
    const [client, setClient] = SDK.hooks.useState("");
    const [publicKey, setPublicKey] = SDK.hooks.useState("");
    const [projects, setProjects] = SDK.hooks.useState("");
    const [modelRoute, setModelRoute] = SDK.hooks.useState("unknown");
    const [principal, setPrincipal] = SDK.hooks.useState(false);
    const [assistant, setAssistant] = SDK.hooks.useState(false);
    const [writeProject, setWriteProject] = SDK.hooks.useState(false);

    SDK.hooks.useEffect(function () {
      let active = true;
      SDK.fetchJSON(memoryEndpoint).then(function (data) {
        if (active) { setMemory(data); setMessage(""); }
      }).catch(function (error) {
        if (active) setMessage("Could not check memory: " + error.message);
      });
      return function () { active = false; };
    }, []);

    async function refresh() {
      setBusy(true);
      try { setMemory(await SDK.fetchJSON(memoryEndpoint)); setMessage(""); }
      catch (error) { setMessage("Could not check memory: " + error.message); }
      finally { setBusy(false); }
    }

    async function action(path, method, body) {
      setBusy(true);
      try {
        const result = await SDK.fetchJSON(memoryEndpoint + path, {
          method: method, headers: { "Content-Type": "application/json" },
          ...(body === undefined ? {} : { body: JSON.stringify(body) }),
        });
        if (path === "/adoption/preview") {
          setAdoption(result); setAssignments({}); setSourcePage(0); setAdoptionRequest(requestId()); setMessage("");
        } else if (path === "/adoption") {
          if (result.status === "committed") {
            const outcome = "Added " + result.facts_adopted + " fact(s) and " + result.proposals_adopted + " pending change(s). Native files remain unchanged.";
            setAdoption(null); setMessage(outcome);
            try { setMemory(await SDK.fetchJSON(memoryEndpoint)); }
            catch (error) { setMessage(outcome + " Could not refresh memory status: " + error.message); }
          } else { setMessage(result.reason ?? result.status); }
        } else if (path === "/review") {
          if (body.tool === "lifeos_memory_proposals") {
            if (result.status === "ok") setProposals(result.results ?? []);
            setMessage(result.status === "ok" ? "" : (result.reason ?? result.status));
          } else if (body.tool === "lifeos_memory_decide_proposal") {
            if (result.status === "committed") {
              const outcome = "Change " + result.proposal_status + ".";
              setMessage(outcome);
              try {
                const pending = await SDK.fetchJSON(memoryEndpoint + "/review", {
                  method: "POST", headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({ tool: "lifeos_memory_proposals", arguments: {} }),
                });
                if (pending.status !== "ok") throw new Error(pending.reason ?? pending.status);
                setProposals(pending.results ?? []);
              } catch (error) { setMessage(outcome + " Could not refresh pending changes: " + error.message); }
            } else { setMessage(result.reason ?? result.status); }
          } else {
            setResults(result.results ?? []);
            setMessage(result.status === "ok" ? "" : (result.reason ?? result.status));
          }
        } else if (path === "/owner") {
          setMemory(result);
          setMessage("This dashboard account now owns the LifeOS installation. Ownership and sharing stay disabled.");
        } else {
          setMemory(await SDK.fetchJSON(memoryEndpoint));
          setMessage(result.status === "enrolled" ?
            "Connection added. Use its private key with SSH and the lifeos-memory command. The private key stays on the other agent's computer." :
            result.status === "revoked" ? "Connection revoked. Its contributed facts remain." :
              "Memory sharing is " + (result.sharing_enabled ? "enabled." : "disabled."));
        }
      } catch (error) { setMessage(error.message); }
      finally { setBusy(false); }
    }

    function input(id, label, value, setter, required) {
      return h("label", { className: "block text-sm", htmlFor: id }, label,
        h("input", { id: id, value: value, required: required, className: "mt-1 block w-full rounded border border-border bg-background p-2",
          onChange: function (event) { setter(event.target.value); } }));
    }
    function checkbox(id, label, value, setter) {
      return h("label", { htmlFor: id, className: "block text-sm" },
        h("input", { id: id, type: "checkbox", checked: value,
          onChange: function (event) { setter(event.target.checked); } }), " " + label);
    }
    function draft(record, field, value) {
      setDrafts(function (current) {
        return { ...current, [record.reference.id]: { ...(current[record.reference.id] ?? {}), [field]: value } };
      });
    }
    function requestId() {
      return "dashboard-" + Array.from(window.crypto.getRandomValues(new Uint32Array(4)), function (value) {
        return value.toString(16).padStart(8, "0");
      }).join("");
    }
    function decide(record, decision) {
      const values = drafts[record.reference.id] ?? {};
      return action("/review", "POST", { tool: "lifeos_memory_decide_proposal", arguments: {
        reference: record.reference, decision: decision, request_id: requestId(),
        ...(decision === "edit" ? { content: values.content ?? record.edit } : {}),
        ...(decision === "applied_elsewhere" ? { note: values.note ?? "" } : {}),
      } });
    }
    const configured = memory && ["prepared", "configured"].includes(memory.state);
    return h("section", { id: "lifeos_memory", className: "rounded border border-border p-4 space-y-3" },
      h("h2", { className: "text-lg font-semibold" }, "Lasting memory"),
      h(MemoryHTTPPreferences),
      h("p", { className: "text-sm" }, "LifeOS keeps durable facts and preferences. Hermes keeps conversation history and context compression."),
      memory?.state === "not_configured" ? h("p", null, "Memory setup is not configured. Your current memory settings have not been changed.") : null,
      memory?.state === "not_configured" ? h("p", { className: "text-sm" },
        "Claim the installation to prepare a fresh store or review memory. The claim binds this dashboard account as the owner. It does not enable ownership or sharing.") : null,
      memory?.state === "not_configured" ? h("button", { type: "button", disabled: busy,
        onClick: function () { return action("/owner", "POST"); },
        className: "rounded border border-border px-4 py-2 disabled:opacity-50" }, "Claim this LifeOS installation") : null,
      memory?.state === "unavailable" ? h("p", { role: "alert" }, "Memory is unavailable: " + memory.message) : null,
      configured ? h("p", null, "Native memory check: " + memory.native_health + ". Current indexed facts: " + (memory.active_facts ?? "unknown") + ".") : null,
      configured ? h("p", { className: "text-sm" }, memory.ownership_enabled
        ? "LifeOS owns lasting memory. Export current facts and review a return to switch to built-in Hermes memory."
        : "After the required import entries are verified, prepare an ownership review. Open LifeOS releases to review and apply the provider switch.") : null,
      h("button", { type: "button", disabled: busy, onClick: refresh, className: "rounded border border-border px-3 py-2" }, "Check memory status"),
      message ? h("p", { role: "status", className: "text-sm" }, message) : null,
      configured ? h("div", { className: "space-y-3" },
        h(MemoryImportReview),
        h(MemoryExportReview),
        h("details", null,
          h("summary", { className: "cursor-pointer font-semibold" }, "Add existing LifeOS memory"),
          h("div", { className: "space-y-3 pt-3" },
            h("p", { className: "text-sm" }, "Preview native notes before adding them to governed recall. This does not copy or change their files. Unknown authors stay unknown. Learning notes remain historical."),
            h("p", { className: "text-sm" }, "Leave a project name blank to keep an unclassified note private to the owner. Assign a project only if agents with access to that project can read the note."),
            h("button", { type: "button", disabled: busy, onClick: function () {
              return action("/adoption/preview", "POST", {});
            } }, "Preview existing LifeOS memory"),
            adoption ? h("div", { className: "space-y-3" },
              h("p", null, "Preview: " + adoption.records.length + " fact(s), " + adoption.proposals.length + " pending change(s), " + adoption.excluded.length + " excluded source(s)."),
              adoption.excluded.map(function (source, index) {
                return h("p", { key: index, className: "text-sm" }, source.path + ": " + source.reason);
              }),
              adoption.records.slice(sourcePage * 25, (sourcePage + 1) * 25).map(function (source, offset) {
                const index = sourcePage * 25 + offset;
                const id = "memory_source_project_" + index;
                return h("article", { key: index, className: "rounded border border-border p-3 space-y-2" },
                  h("p", { className: "text-sm" }, source.path),
                  h("p", { className: "text-xs" }, (source.source_kind === "learning" ? "Historical learning" : "Native fact") + ". Author: unknown."),
                  h("p", { className: "whitespace-pre-wrap" }, source.content),
                  source.category === "project" ? h("label", { htmlFor: id, className: "block text-sm" }, "Project name (optional, applies to this file)",
                    h("input", { id: id, disabled: busy, value: assignments[source.path] ?? "", className: "block w-full rounded border border-border bg-background p-2",
                      onChange: function (event) {
                        const value = event.target.value;
                        setAssignments(function (current) { return { ...current, [source.path]: value }; });
                        setAdoptionRequest(requestId());
                      } })) : null);
              }),
              adoption.records.length > 25 ? h("div", { className: "flex gap-2" },
                h("button", { type: "button", disabled: busy || sourcePage === 0,
                  onClick: function () { setSourcePage(sourcePage - 1); } }, "Previous sources"),
                h("p", null, "Page " + (sourcePage + 1) + " of " + Math.ceil(adoption.records.length / 25)),
                h("button", { type: "button", disabled: busy || (sourcePage + 1) * 25 >= adoption.records.length,
                  onClick: function () { setSourcePage(sourcePage + 1); } }, "Next sources")) : null,
              adoption.proposals.map(function (proposal) {
                return h("article", { key: proposal.reference.id, className: "rounded border border-border p-3" },
                  h("p", null, "Pending change: " + proposal.row.edit), h("p", { className: "text-sm" }, "Target: " + proposal.target));
              }),
              h("p", { className: "text-sm" }, "Adding pending changes does not accept them. Review them separately after adoption."),
              h("button", { type: "button", disabled: busy || adoption.records.length + adoption.proposals.length === 0,
                onClick: function () {
                  const projects = Object.fromEntries(Object.entries(assignments).filter(function (entry) { return entry[1].trim(); })
                    .map(function (entry) { return [entry[0], entry[1].trim()]; }));
                  return action("/adoption", "POST", { signature: adoption.signature, projects: projects, request_id: adoptionRequest });
                } }, "Add reviewed sources to memory")) : null)),
        h("h3", { className: "font-semibold" }, "Review current facts"),
        h("form", { id: "memory_search", className: "space-y-2", onSubmit: function (event) {
          event.preventDefault(); return action("/review", "POST", { tool: "lifeos_memory_search", arguments: { query: query } });
        } }, input("memory_query", "Find a fact", query, setQuery, true),
        h("button", { type: "submit", disabled: busy, className: "rounded border border-border px-3 py-2" }, "Search memories")),
        results.map(function (record) {
          return h("article", { key: record.reference.id, className: "rounded border border-border p-3" },
            h("p", { className: "whitespace-pre-wrap" }, record.content),
            h("p", { className: "text-xs" }, record.reference.id + ", revision " + record.reference.revision + ". Writer: " + record.writer + "."));
        }),
        h("p", { className: "text-sm" }, memory.ownership_enabled
          ? "Ask your agent to correct or forget a fact using its reference. Forget removes ordinary recall; it does not erase conversation history, audits, or backups."
          : "Agent corrections and forgetting are unavailable until LifeOS memory ownership is enabled. Complete the reviewed import activation from LifeOS releases."),
        memory.proposal_review_available ? h("details", null,
          h("summary", { className: "cursor-pointer font-semibold" }, "Pending preference and rule changes"),
          h("div", { className: "space-y-3 pt-3" },
            h("p", { className: "text-sm" }, "Pending changes have not been applied. Check the proposed text and its target before accepting. Changed targets require a fresh review. Applied identity changes require a new conversation."),
            h("button", { type: "button", disabled: busy, onClick: function () {
              return action("/review", "POST", { tool: "lifeos_memory_proposals", arguments: {} });
            } }, "Review pending changes"),
            proposals?.length === 0 ? h("p", null, "No pending changes.") : null,
            (proposals ?? []).map(function (record) {
              const values = drafts[record.reference.id] ?? {};
              const editId = "memory_edit_" + record.reference.id;
              const noteId = "memory_note_" + record.reference.id;
              return h("article", { key: record.reference.id, className: "rounded border border-border p-3 space-y-2" },
                h("p", { className: "whitespace-pre-wrap" }, record.edit),
                h("p", { className: "text-sm" }, "Target: " + record.target_file),
                h("p", { className: "text-sm" }, "Reason: " + record.rationale),
                h("p", { className: "text-xs" }, "Proposed by " + record.writer + ". Reference: " + record.reference.id + ", revision " + record.reference.revision + "."),
                h("div", { className: "flex gap-2" },
                  h("button", { type: "button", disabled: busy, onClick: function () { return decide(record, "accept"); } }, "Accept change"),
                  h("button", { type: "button", disabled: busy, onClick: function () { return decide(record, "reject"); } }, "Reject change")),
                h("details", null, h("summary", null, "Edit or record another outcome"),
                  h("label", { htmlFor: editId, className: "block text-sm" }, "Text to apply",
                    h("textarea", { id: editId, value: values.content ?? record.edit, maxLength: 65536,
                      className: "block w-full rounded border border-border bg-background p-2",
                      onChange: function (event) { draft(record, "content", event.target.value); } })),
                  h("button", { type: "button", disabled: busy || !(values.content ?? record.edit).trim(),
                    onClick: function () { return decide(record, "edit"); } }, "Apply edited change"),
                  input(noteId, "Where was this change applied?", values.note ?? "", function (value) { draft(record, "note", value); }, false),
                  h("button", { type: "button", disabled: busy || !(values.note ?? "").trim(),
                    onClick: function () { return decide(record, "applied_elsewhere"); } }, "Mark applied elsewhere")));
            }))) : null,
        h("details", null, h("summary", { className: "cursor-pointer font-semibold" }, "Share memory with another agent"),
          h("div", { className: "space-y-3 pt-3" },
            h("p", { className: "text-sm" }, "Sharing is " + (memory.sharing_enabled ? "enabled" : "disabled") + ". Each agent gets its own SSH key and permissions. This shares memory operations, not LifeOS hooks or Hermes conversations."),
            h("button", { type: "button", disabled: busy, className: "rounded border border-border px-3 py-2",
              onClick: function () { return action("/sharing", "POST", { enabled: !memory.sharing_enabled }); }
            }, memory.sharing_enabled ? "Disable memory sharing" : "Enable memory sharing"),
            (memory.connections ?? []).map(function (connection) {
              return h("article", { key: connection.client, className: "rounded border border-border p-3 text-sm" },
                h("p", null, connection.client + ": " + (connection.enabled ? "enabled" : "revoked")),
                h("p", null, "Reads: " + (connection.read ?? ["project"]).join(", ") + ". Writes: " + ((connection.write ?? []).join(", ") || "none") + "."),
                h("p", null, "Projects: " + (connection.projects ?? []).join(", ") + ". Declared model route: " + (connection.model_route ?? "unknown") + "."),
                connection.enabled ? h("button", { type: "button", disabled: busy,
                  onClick: function () { return action("/connections/" + encodeURIComponent(connection.client), "DELETE"); }
                }, "Revoke " + connection.client) : null,
                !connection.enabled && connection.credential_entry_pending ? h("p", null,
                  "The SSH entry of this connection is still present. It cannot reach memory. Install the sharing component to remove it.") : null,
                !connection.enabled && connection.credential_entry_pending && memory.connection_enrollment_available !== false ? h("button", { type: "button", disabled: busy,
                  onClick: function () { return action("/connections/" + encodeURIComponent(connection.client), "DELETE"); }
                }, "Remove SSH entry of " + connection.client) : null);
            }),
            h("p", { className: "text-sm" }, "A cloud model can receive every fact this connection returns. An unknown model route is unverified. Adding a connection enables sharing for the enabled connections listed above."),
            memory.connection_enrollment_available === false ? h("p", { id: "memory_enrollment_unavailable", className: "text-sm" },
              "Adding a connection needs the optional SSH sharing component. Install it on the server, then reload this page. Existing connections can still be revoked here.") :
            h("form", { id: "memory_enrollment", className: "space-y-3", onSubmit: function (event) {
              event.preventDefault();
              const read = ["project"]; if (principal) read.push("principal"); if (assistant) read.push("assistant");
              return action("/connections", "POST", { client: client, public_key: publicKey,
                projects: projects.split(",").map(function (value) { return value.trim(); }).filter(Boolean),
                model_route: modelRoute, read: read, write_project: writeProject });
            } }, input("memory_client", "Connection name", client, setClient, true),
              input("memory_public_key", "Agent's Ed25519 public key", publicKey, setPublicKey, true),
              input("memory_projects", "Project names (comma separated; * allows all projects)", projects, setProjects, true),
              input("memory_model_route", "Agent's declared model route", modelRoute, setModelRoute, true),
              checkbox("memory_principal", "Allow reading owner preferences and identity", principal, setPrincipal),
              checkbox("memory_assistant", "Allow reading assistant preferences", assistant, setAssistant),
              checkbox("memory_project_write", "Allow writing project facts", writeProject, setWriteProject),
              h("button", { type: "submit", disabled: busy, className: "rounded border border-border px-3 py-2" }, "Add agent connection"))))) : null);
  }

  function FreshStores() {
    const endpoint = "/api/plugins/lifeos-hook-bridge/memory/fresh";
    const selectionEndpoint = "/api/plugins/lifeos-hook-bridge/installation/selection";
    const [listing, setListing] = SDK.hooks.useState(null);
    const [selection, setSelection] = SDK.hooks.useState(null);
    const [principalName, setPrincipalName] = SDK.hooks.useState("");
    const [assistantName, setAssistantName] = SDK.hooks.useState("");
    const [busy, setBusy] = SDK.hooks.useState(false);
    const [notice, setNotice] = SDK.hooks.useState("");

    async function load() {
      try { setListing(await SDK.fetchJSON(endpoint + "/status")); }
      catch (error) { setNotice("Could not list fresh stores: " + error.message); }
      try { setSelection(await SDK.fetchJSON(selectionEndpoint)); }
      catch (error) { setNotice("Could not read the selected installation: " + error.message); }
    }
    async function choose(path, body, started) {
      setBusy(true);
      try {
        await SDK.fetchJSON(selectionEndpoint + path, { method: "POST",
          ...(body === undefined ? {} : { headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }) });
        setNotice(started);
        await load();
      } catch (error) { setNotice(error.message); }
      finally { setBusy(false); }
    }
    SDK.hooks.useEffect(function () { load(); }, []);

    async function start(event) {
      event.preventDefault();
      setBusy(true);
      try {
        await SDK.fetchJSON(endpoint + "/start", { method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ principal_name: principalName, assistant_name: assistantName }) });
        setNotice("Preparation started. It continues if this page closes.");
        await load();
      } catch (error) { setNotice(error.message); }
      finally { setBusy(false); }
    }
    async function remove(identifier) {
      setBusy(true);
      try {
        await SDK.fetchJSON(endpoint + "/stores/" + encodeURIComponent(identifier), { method: "DELETE" });
        setNotice("Store removed. The current installation is unchanged.");
        await load();
      } catch (error) { setNotice(error.message); }
      finally { setBusy(false); }
    }
    function describe(store) {
      const names = store.names ? store.names.principal + " and " + store.names.assistant : "Unknown names";
      if (store.state === "review") return names + ": ready for review, " + store.active_facts + " active facts";
      if (store.state === "failed") return names + ": failed: " + store.reason;
      if (store.state === "preparing") return names + ": preparing";
      if (store.state === "interrupted") return names + ": interrupted. Remove it and start again.";
      return "A store with unreadable or altered records";
    }
    const stores = listing ? listing.stores : [];
    const job = selection?.job?.state ?? "none";
    const pending = ["queued", "running", "recovering", "rolling_back", "interrupted"].includes(job);
    const selectedStore = selection?.configured ? stores.find(function (store) {
      return selection.home.includes("/" + store.identifier + "/");
    }) : null;
    return h("section", { className: "space-y-3" },
      h("h3", { className: "font-semibold" }, "Fresh LifeOS store"),
      h("p", { className: "text-sm" }, "Prepare a separate store with no existing facts. The current installation stays selected; preparing a store does not switch memory."),
      h("form", { id: "fresh_store_start", className: "space-y-2", onSubmit: start },
        h("label", { className: "block text-sm", htmlFor: "fresh_principal" }, "Your name",
          h("input", { id: "fresh_principal", value: principalName, required: true,
            className: "mt-1 block w-full rounded border border-border bg-background p-2",
            onChange: function (event) { setPrincipalName(event.target.value); } })),
        h("label", { className: "block text-sm", htmlFor: "fresh_assistant" }, "Assistant name",
          h("input", { id: "fresh_assistant", value: assistantName, required: true,
            className: "mt-1 block w-full rounded border border-border bg-background p-2",
            onChange: function (event) { setAssistantName(event.target.value); } })),
        h("button", { type: "submit", disabled: busy || !listing || listing.busy,
          className: "rounded border border-border px-3 py-2" }, "Prepare fresh store")),
      selection?.configured ? h("div", { className: "space-y-2 text-sm" },
        h("p", null, "This profile uses the fresh store " + (selectedStore ? selectedStore.identifier.slice(0, 8) : selection.home) +
          ". The previous installation and its data stay unchanged."),
        h("button", { type: "button", disabled: busy || pending,
          onClick: function () { return choose("/return", undefined, "Return started. Hermes restarts when it finishes."); },
          className: "rounded border border-border px-3 py-2" }, "Return to the previous installation")) : null,
      job === "interrupted" ? h("button", { type: "button", disabled: busy,
        onClick: function () { return choose("/recover", undefined, "Recovery started."); },
        className: "rounded border border-border px-3 py-2" }, "Recover interrupted selection") : null,
      job !== "none" ? h("p", { role: "status", className: "text-sm" }, "Installation selection: " + job +
        (selection.job.error ? ". " + selection.job.error : "")) : null,
      stores.map(function (store) {
        return h("article", { key: store.identifier, className: "rounded border border-border p-3 text-sm" },
          h("p", null, describe(store)),
          store.state === "review" && store !== selectedStore && !pending ? h("button", { type: "button", disabled: busy,
            onClick: function () { return choose("", { store: store.identifier },
              "Selection started. Hermes restarts with the fresh store when it finishes."); } },
            "Use " + store.identifier.slice(0, 8)) : null,
          h("button", { type: "button", disabled: busy || store.state === "preparing",
            onClick: function () { return remove(store.identifier); } }, "Remove " + store.identifier.slice(0, 8)));
      }),
      notice ? h("p", { role: "status", className: "text-sm" }, notice) : null);
  }

  function LifeOSSettings() {
    const [fields, setFields] = SDK.hooks.useState([]);
    const [values, setValues] = SDK.hooks.useState({});
    const [models, setModels] = SDK.hooks.useState([]);
    const [suggestedDefaults, setSuggestedDefaults] = SDK.hooks.useState(false);
    const [status, setStatus] = SDK.hooks.useState("Loading settings...");
    const [saving, setSaving] = SDK.hooks.useState(false);
    const [baseline, setBaseline] = SDK.hooks.useState(null);
    const [candidate, setCandidate] = SDK.hooks.useState(null);
    const [baselineStatus, setBaselineStatus] = SDK.hooks.useState("");
    const [baselineBusy, setBaselineBusy] = SDK.hooks.useState(false);
    const [installation, setInstallation] = SDK.hooks.useState(null);
    const [installationStatus, setInstallationStatus] = SDK.hooks.useState("");
    const [installationBusy, setInstallationBusy] = SDK.hooks.useState(false);
    const [hostPatch, setHostPatch] = SDK.hooks.useState(null);
    const [lifeosUpdate, setLifeosUpdate] = SDK.hooks.useState(null);

    SDK.hooks.useEffect(function () {
      let active = true;
      Promise.all([SDK.fetchJSON(endpoint), SDK.fetchJSON(modelEndpoint)]).then(function (results) {
        if (!active) return;
        const data = results[0];
        const catalog = results[1];
        setFields(data.fields);
        const nextValues = Object.fromEntries(data.fields.map(function (field) {
          return [field.key, field.value ?? ""];
        }));
        const choices = [];
        for (const provider of catalog.providers ?? []) {
          if (provider.authenticated === false) continue;
          for (const model of provider.models ?? []) {
            if (typeof model !== "string" || !model) continue;
            choices.push({ provider: provider.slug, model: model,
              label: provider.name + " / " + model, isCurrent: provider.is_current === true });
          }
        }
        const current = choices.find(function (choice) {
          return choice.provider === catalog.provider && choice.model === catalog.model;
        }) ?? choices.find(function (choice) {
          return choice.isCurrent && choice.model === catalog.model;
        });
        if (current) {
          for (const tier of tiers) {
            if (!nextValues[tier + "_model"] && nextValues[tier + "_inherit_child_default"] !== true) {
              nextValues[tier + "_provider"] = current.provider;
              nextValues[tier + "_model"] = current.model;
              setSuggestedDefaults(true);
            }
          }
        }
        setValues(nextValues);
        setModels(choices);
        setStatus(!choices.length ? "No configured Hermes models are available. Add a model on the Models page." :
          !current && tiers.some(function (tier) {
            return !nextValues[tier + "_model"] && nextValues[tier + "_inherit_child_default"] !== true;
          }) ? "Hermes's current model is not available in this list. Choose a model for each tier." : "");
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
      refreshHostPatch(0);
      refreshLifeOSUpdate(0);
      return function () { active = false; };
    }, []);

    function update(key, value) {
      setValues(function (current) { return Object.assign({}, current, { [key]: value }); });
    }

    function selectModel(tier, selected) {
      if (!selected) {
        setValues(function (current) {
          return Object.assign({}, current, {
            [tier + "_provider"]: "", [tier + "_model"]: "", [tier + "_inherit_child_default"]: true,
          });
        });
        return;
      }
      let pair;
      try { pair = JSON.parse(selected); } catch (_error) { return; }
      if (!Array.isArray(pair) || pair.length !== 2 ||
          typeof pair[0] !== "string" || typeof pair[1] !== "string") return;
      setValues(function (current) {
        return Object.assign({}, current, {
          [tier + "_provider"]: pair[0], [tier + "_model"]: pair[1],
          [tier + "_inherit_child_default"]: false,
        });
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
        setSuggestedDefaults(false);
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
        setInstallationStatus("Candidate prepared from LifeOS commit " + result.upstream_commit + ". The running installation has not changed.");
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
          setInstallationStatus("LifeOS " + result.installed_version + " installed. Finish setup to mount it into Hermes and record the VersionDrift baseline.");
        });
      }).catch(function (error) {
        setInstallationStatus("Could not install LifeOS: " + error.message);
      }).finally(function () { setInstallationBusy(false); });
    }

    function finalizeLifeOS() {
      setInstallationBusy(true);
      setInstallationStatus("");
      SDK.fetchJSON(installationEndpoint + "/finalize", { method: "POST" }).then(function () {
        return Promise.all([SDK.fetchJSON(installationEndpoint), SDK.fetchJSON(baselineEndpoint)]).then(function (results) {
          setInstallation(results[0]);
          setBaseline(results[1]);
          setInstallationStatus("LifeOS is mounted and the baseline is recorded. Restart the Hermes gateway to load the new configuration.");
        });
      }).catch(function (error) {
        setInstallationStatus("Could not finish LifeOS setup: " + error.message);
      }).finally(function () { setInstallationBusy(false); });
    }

    function recoverLifeOSMount() {
      setInstallationBusy(true);
      setInstallationStatus("");
      SDK.fetchJSON(installationEndpoint + "/mount/recover", { method: "POST" }).then(function () {
        return SDK.fetchJSON(installationEndpoint).then(function (result) {
          setInstallation(result);
          setInstallationStatus("The previous Hermes files are restored. You can finish setup again.");
        });
      }).catch(function (error) {
        setInstallationStatus("Could not restore the mount: " + error.message);
      }).finally(function () { setInstallationBusy(false); });
    }

    function prepareHermes() {
      setInstallationBusy(true);
      setInstallationStatus("");
      SDK.fetchJSON(installationEndpoint + "/prepare-hermes", { method: "POST" }).then(function (result) {
        setInstallation(function (current) { return Object.assign({}, current, {
          hermes_candidate_ready: true, hermes_candidate_commit: result.base_commit,
          hermes_candidate_patch_count: result.patches.length, hermes_candidate_error: null,
        }); });
        setInstallationStatus("Hermes candidate prepared. The running Hermes installation has not changed.");
      }).catch(function (error) {
        setInstallationStatus("Could not prepare Hermes: " + error.message);
      }).finally(function () { setInstallationBusy(false); });
    }

    function refreshHostPatch(attempt) {
      SDK.fetchJSON(hostPatchEndpoint).then(function (result) {
        setHostPatch(result);
        if (["staged", "applying", "restoring"].includes(result.state) && attempt < 60) {
          window.setTimeout(function () { refreshHostPatch(attempt + 1); }, 3000);
        } else if (["applied", "rolled_back"].includes(result.state)) {
          return SDK.fetchJSON(installationEndpoint).then(setInstallation);
        }
      }).catch(function (error) {
        if (attempt < 60) {
          window.setTimeout(function () { refreshHostPatch(attempt + 1); }, 3000);
        } else {
          setInstallationStatus("Could not read Hermes patch status: " + error.message);
        }
      });
    }

    function applyHermes() {
      setInstallationBusy(true);
      setInstallationStatus("");
      SDK.fetchJSON(installationEndpoint + "/apply-hermes", { method: "POST" }).then(function () {
        setInstallationStatus("Hermes patch worker started. The gateway will restart while it applies the tested extension.");
        refreshHostPatch(0);
      }).catch(function (error) {
        setInstallationStatus("Could not start Hermes patch: " + error.message);
      }).finally(function () { setInstallationBusy(false); });
    }

    function restoreHermes() {
      setInstallationBusy(true);
      setInstallationStatus("");
      SDK.fetchJSON(installationEndpoint + "/restore-hermes", { method: "POST" }).then(function () {
        setInstallationStatus("Restoring the previous Hermes source. The gateway will restart.");
        refreshHostPatch(0);
      }).catch(function (error) {
        setInstallationStatus("Could not start Hermes restore: " + error.message);
      }).finally(function () { setInstallationBusy(false); });
    }

    function recoverHermes() {
      setInstallationBusy(true);
      setInstallationStatus("");
      SDK.fetchJSON(installationEndpoint + "/recover-hermes", { method: "POST" }).then(function () {
        setInstallationStatus("Returning Hermes to its stock files. The gateway will restart.");
        refreshHostPatch(0);
      }).catch(function (error) {
        setInstallationStatus("Could not start Hermes recovery: " + error.message);
      }).finally(function () { setInstallationBusy(false); });
    }

    function refreshLifeOSUpdate(attempt) {
      SDK.fetchJSON(lifeosUpdateEndpoint).then(function (result) {
        setLifeosUpdate(result);
        if (["queued", "preparing", "applying", "restoring", "recovering"].includes(result.state) && attempt < 120) {
          window.setTimeout(function () { refreshLifeOSUpdate(attempt + 1); }, 3000);
        } else if (["applied", "rolled_back"].includes(result.state)) {
          return Promise.all([SDK.fetchJSON(installationEndpoint), SDK.fetchJSON(baselineEndpoint)]).then(function (results) {
            setInstallation(results[0]);
            setBaseline(results[1]);
          });
        }
      }).catch(function (error) {
        setInstallationStatus("Could not read LifeOS update status: " + error.message);
      });
    }

    function applyLifeOSUpdate() {
      setInstallationBusy(true);
      setInstallationStatus("");
      SDK.fetchJSON(lifeosUpdateEndpoint, { method: "POST" }).then(function () {
        setInstallationStatus("LifeOS update started. The gateway will restart after native checks pass.");
        refreshLifeOSUpdate(0);
      }).catch(function (error) {
        setInstallationStatus("Could not start LifeOS update: " + error.message);
      }).finally(function () { setInstallationBusy(false); });
    }

    function recoverLifeOSUpdate() {
      setInstallationBusy(true);
      setInstallationStatus("");
      SDK.fetchJSON(lifeosUpdateEndpoint + "/recover", { method: "POST" }).then(function () {
        setInstallationStatus("LifeOS recovery started. If no files were replaced, the worker restarts the current version. Otherwise, it restores the prior version and restarts Hermes.");
        refreshLifeOSUpdate(0);
      }).catch(function (error) {
        setInstallationStatus("Could not start LifeOS recovery: " + error.message);
      }).finally(function () { setInstallationBusy(false); });
    }

    function restoreLifeOSUpdate() {
      setInstallationBusy(true);
      setInstallationStatus("");
      SDK.fetchJSON(lifeosUpdateEndpoint + "/restore", { method: "POST" }).then(function () {
        setInstallationStatus("Restoring the previous LifeOS version. Hermes will restart.");
        refreshLifeOSUpdate(0);
      }).catch(function (error) {
        setInstallationStatus("Could not restore LifeOS: " + error.message);
      }).finally(function () { setInstallationBusy(false); });
    }

    function renderTier(tier) {
      const label = tier.charAt(0).toUpperCase() + tier.slice(1);
      const modelKey = tier + "_model";
      const providerKey = tier + "_provider";
      const effortKey = tier + "_effort";
      const effortField = fields.find(function (field) { return field.key === effortKey; });
      const selected = values[tier + "_inherit_child_default"] === true || !values[modelKey] ? "" :
        JSON.stringify([values[providerKey] ?? "", values[modelKey]]);
      const listed = models.some(function (choice) {
        return choice.provider === values[providerKey] && choice.model === values[modelKey];
      });
      const options = [h("option", { key: "default", value: "" },
        values[tier + "_inherit_child_default"] === true || selected ?
          "Keep existing child routing (advanced)" : "Choose a Hermes model")];
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
            }, options),
            !values[modelKey] ? h("p", { className: "mt-2 text-sm text-muted-foreground" },
              "Delegated tasks use this Hermes conversation's model. Other LifeOS child calls use a separate connection set up outside this page. Check where that connection sends data.") : null),
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
      h(MemoryPreferences),
      h(FreshStores),
        h("p", { className: "text-muted-foreground" },
          "LifeOS asks for four levels of work. Choose a Hermes model and effort for each one. Using one model in every row is fine. The model currently selected in Hermes fills empty rows by default. Effort controls the amount of reasoning requested."),
        suggestedDefaults ? h("p", { role: "status", className: "mt-2 text-sm" },
          "Hermes's current model is selected for the empty rows. Save settings to keep these choices when you change Hermes's main model.") : null,
        h("a", { href: "/models", className: "text-sm underline" }, "Manage Hermes models")),
      h("section", { className: "rounded border border-border p-4" },
        h("h2", { className: "mb-2 text-lg font-semibold" }, "LifeOS installation"),
        installation?.lifeos === "missing" ? h("p", { className: "mb-3 text-sm" },
          "LifeOS is not installed. Prepare the latest supported revision from Daniel Miessler's GitHub repository. This step checks and applies the LifeOS compatibility patches in a private candidate directory. It does not change the running installation.") : null,
        installation?.lifeos === "partial" ? h("p", { role: "status" },
          "A .claude directory already exists. The fresh installer will not overwrite it. Review that directory before installing LifeOS.") : null,
        installation?.lifeos === "installed" ? h("p", null,
          "LifeOS " + installation.version + " is installed.") : null,
        installation?.lifeos === "installed" && installation.setup_baseline_exists ? h("div", { className: "space-y-2 text-sm" },
          h("p", null, "Updates use a tested LifeOS commit and compatibility patch set. The worker stages dependencies and hook registrations, restarts Hermes, then verifies the installed result."),
          (!installation.candidate_ready || lifeosUpdate?.state === "applied") ? h("button", {
            type: "button", disabled: installationBusy || ["queued", "preparing", "applying"].includes(lifeosUpdate?.state),
            onClick: prepareLifeOS,
            className: "rounded border border-border px-4 py-2 disabled:opacity-50",
          }, installationBusy ? "Preparing..." : lifeosUpdate?.state === "applied" ? "Check for newer supported LifeOS" : "Prepare latest LifeOS update") : null,
          installation.candidate_ready ? h("p", null,
            "Prepared commit " + installation.candidate_commit + " with " + installation.candidate_patch_count + " compatibility patches.") : null,
          installation.candidate_ready && (["none", "failed", "rolled_back"].includes(lifeosUpdate?.state)
            || (lifeosUpdate?.state === "applied" && installation.candidate_newer)) ? h("button", {
            type: "button", disabled: installationBusy, onClick: applyLifeOSUpdate,
            className: "rounded border border-border px-4 py-2 disabled:opacity-50",
          }, installationBusy ? "Starting..." : "Apply prepared LifeOS update") : null,
          lifeosUpdate?.state === "applied" ? h("p", { role: "status" }, "LifeOS update applied and verified.") : null,
          lifeosUpdate?.state === "applied" ? h("div", { className: "space-y-2" },
            h("p", null, "Restore the program version saved before this update. Memory and audit data in the same external user directory stay current. Restore stops if its directory links, user data inside the program directory, or Hermes configuration have changed. Your conversations stay in Hermes."),
            h("button", { type: "button", disabled: installationBusy, onClick: restoreLifeOSUpdate,
              className: "rounded border border-border px-4 py-2 disabled:opacity-50" }, "Restore previous LifeOS version")) : null,
          ["queued", "preparing", "applying", "restoring", "recovering"].includes(lifeosUpdate?.state) ? h("p", { role: "status" },
            "LifeOS update: " + lifeosUpdate.state + ". The gateway may be unavailable during restart.") : null,
          ["failed", "rollback_failed", "rolled_back", "interrupted"].includes(lifeosUpdate?.state) ? h("p", { role: "status" },
            "LifeOS update: " + lifeosUpdate.state + (lifeosUpdate.error ? ". " + lifeosUpdate.error : "")) : null,
          lifeosUpdate?.state === "interrupted" && ["stopped", "swapped", "restoring", "rollback_failed"].includes(lifeosUpdate.transaction_state) ? h("button", {
            type: "button", disabled: installationBusy, onClick: recoverLifeOSUpdate,
            className: "rounded border border-border px-4 py-2 disabled:opacity-50",
          }, "Restore interrupted update") : null) : null,
        installation?.mount?.recovery_required ? h("div", { className: "space-y-2 text-sm" },
          h("p", { role: "status" }, "LifeOS setup was interrupted. Restore the previous Hermes files before mounting again. Recovery preserves later edits and stops if a file has changed."),
          h("button", {type: "button", disabled: installationBusy, onClick: recoverLifeOSMount,
            className: "rounded border border-border px-4 py-2 disabled:opacity-50"},
            "Restore interrupted mount")) : null,
        installation?.lifeos === "installed" && !installation.setup_baseline_exists ? h("div", { className: "space-y-2 text-sm" },
          h("p", null, installation.candidate_ready ?
            "Finish setup to mount LifeOS into Hermes and record the installed system files." :
            "A prepared LifeOS source is required to finish setup. Review the VersionDrift controls below if this is an existing installation."),
          installation.candidate_ready ? h("button", {
            type: "button", disabled: installationBusy, onClick: finalizeLifeOS,
            className: "rounded border border-border px-4 py-2 disabled:opacity-50",
          }, installationBusy ? "Finishing..." : "Finish LifeOS setup") : null) : null,
        installation?.dashboard_restart_required ? h("p", { role: "status" },
          "Restart the Hermes dashboard to load the changed Hermes hooks. Until then, this page shows the hooks that the running dashboard loaded at start.") : null,
        installation?.lifeos === "installed" && installation.hermes === "stock" && !installation.dashboard_restart_required ? h("div", { className: "space-y-2 text-sm" },
          h("p", null, "Current Hermes runs LifeOS pre-tool, post-tool, prompt-context, and session-end callbacks."),
          h("p", null, "Reduced mode cannot enforce LifeOS Bash permission decisions, block a user prompt, gate a final answer, or reliably add post-tool warnings after another result transformer. It also lacks the patched child model routes and remote file guards."),
          h("details", null,
            h("summary", { className: "cursor-pointer font-medium" }, "Read all reduced-mode limits"),
            h("ul", { className: "ml-5 mt-2 list-disc space-y-1" }, [
              "Bash allow, ask, deny, replacement, and recheck decisions cannot be enforced for every command.",
              "A LifeOS denial may be bypassed by a Hermes allowlist, prepared approval, or bypass mode.",
              "LifeOS cannot block a user prompt or withhold a rejected final answer before delivery.",
              "Post-tool advice may not reach the model after another result transformer.",
              "Child calls do not have the tested per-tier provider and effort route.",
              "SSH and Docker whole-file writes lack the patched stale-write guard.",
              "Nested tool identity, session reasons, and final-turn watchdog activity lack tested host signals.",
              "Scheduled workers may start outside the managed plugin dependency environment.",
            ].map(function (item) { return h("li", { key: item }, item); }))),
          h("p", null, "You can keep Hermes unchanged and use these limited callbacks."),
          h("button", {
            type: "button", disabled: installationBusy || installation.hermes_candidate_ready,
            onClick: prepareHermes,
            className: "rounded border border-border px-4 py-2 disabled:opacity-50",
          }, installationBusy ? "Preparing..." : "Prepare tested Hermes extension"),
          installation.hermes_candidate_ready ? h("p", null,
            "Candidate base " + installation.hermes_candidate_commit + " contains " +
            installation.hermes_candidate_patch_count + " Hermes patches.") : null,
          installation.hermes_candidate_ready && installation.setup_baseline_exists &&
          ["none", "rolled_back", "failed_preflight"].includes(hostPatch?.state) ? h("button", {
            type: "button", disabled: installationBusy, onClick: applyHermes,
            className: "rounded border border-border px-4 py-2 disabled:opacity-50",
          }, installationBusy ? "Starting..." : "Apply tested Hermes extension") : null,
          installation.hermes_candidate_error ? h("p", { role: "status" },
            "Hermes candidate cannot be used: " + installation.hermes_candidate_error) : null) : null,
        hostPatch?.state === "applied" ? h("div", { className: "space-y-2 text-sm" },
          h("p", null, "Hermes extension is active. Full LifeOS hook parity remains unverified."),
          hostPatch.error ? h("p", { role: "status" }, hostPatch.error) : null,
          h("button", {
            type: "button", disabled: installationBusy, onClick: restoreHermes,
            className: "rounded border border-border px-4 py-2 disabled:opacity-50",
          }, "Restore previous Hermes")) : null,
        ["staged", "applying", "restoring"].includes(hostPatch?.state) ? h("p", { role: "status" },
          "Hermes patch job is " + hostPatch.state + ". The gateway may be unavailable during restart.") : null,
        hostPatch?.state === "interrupted" ? h("div", { className: "space-y-2 text-sm" },
          h("p", { role: "alert" }, "A Hermes patch change stopped before it finished. The gateway may be stopped. Recovery returns Hermes to its stock files and starts the gateway."),
          h("button", { type: "button", disabled: installationBusy, onClick: recoverHermes,
            className: "rounded border border-border px-4 py-2 disabled:opacity-50" }, "Recover interrupted Hermes change")) : null,
        ["rolled_back", "rollback_failed", "restore_failed", "failed_preflight", "error"].includes(hostPatch?.state) ? h("p", { role: "status" },
          "Hermes patch job: " + hostPatch.state + (hostPatch.error ? ". " + hostPatch.error : "")) : null,
        installation?.lifeos === "installed" && installation.hermes === "patched_hooks_present" && !installation.dashboard_restart_required ? h("p", { className: "text-sm" },
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
