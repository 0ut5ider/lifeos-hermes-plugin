# HTTP memory review 2

Date: 2026-10-16

Role: Independent security and correctness reviewer

Question: Does PR32 correct the first review findings and safely provide HTTP MCP with owner-approved memory grants?

Model: GPT-6.1-sol, high reasoning effort

Reviewed commit: `85ddb3df295518bd087d05288d386fdaca9a5990` on `feature/http-memory-mcp`.

Baseline: `67c5641b57608537526414991a652b6ad6f78b0e` (`origin/main`).

Pull request: <https://github.com/0ut5ider/lifeos-hermes-plugin/pull/32>

## Result

The three first-round findings are corrected. One additional P2 finding remains at the localhost transport boundary. Changes are required before approval.

I rerun the supplied targeted command. All 18 tests pass. The three HTTP dashboard component tests also pass. The independent probes record protocol outcomes in `probe-results.json` and `probe-output.txt`. Their source is `review_probes.py`.

All probes use disposable native fixtures and synthetic records. I do not change a product file, live configuration, service, deployed client, or personal memory. I do not use memory tools or subagents.

## Finding: P2, localhost HTTP mode accepts plaintext requests from non-loopback peers

Location: `lifeos_hook_bridge/memory_remote.py:306-311`.

The transport accepts an HTTP origin only when its hostname is localhost or a loopback address. However, the middleware checks the actual socket peer only when the configured origin uses HTTPS. A Host header that names localhost does not establish a local connection.

The independent probe configures `http://127.0.0.1:9100` and creates a valid owner-approved bearer token. It then supplies a non-loopback ASGI client address, `192.0.2.20`, with an HTTP request and the configured Host header. The request receives HTTP 200 and lists all nine memory tools. The probe uses the real middleware and SDK request handlers.

This matters because the MCP transport shares the Hermes dashboard listener. An installation can bind that listener to a LAN address or all interfaces. Selecting a localhost origin must not make that listener accept remote plaintext credentials and memory operations. The setup guide reserves HTTP origins for localhost tests. The current middleware does not enforce that restriction.

Minimal correction: require a loopback socket peer whenever the configured origin uses HTTP. Keep the existing HTTPS rule that permits a trusted local TLS proxy. Add coverage for remote discovery, authorization, token exchange, and MCP requests with a localhost Host header. Loopback HTTP tests and actual Tailscale HTTPS must remain valid.

This finding does not grant anonymous memory access. The request still needs a valid bearer token. It concerns transport confidentiality and enforcement of the explicitly permitted local HTTP exception.

## First-round finding closure

### Refresh-token family revocation

The store now retains only hashes of consumed refresh tokens. Sequential reuse revokes the replacement access and refresh credentials. The direct preloaded refresh race raises SDK `TokenError` and revokes that family.

The independent probe confirms that replay returns HTTP 400, replacement authentication fails, and replacement refresh returns HTTP 400. An unrelated connection remains valid. Presenting the consumed refresh token with another registered client does not revoke the first client's family. A fresh `MemoryRemote` object recognizes persisted consumed markers.

### Anonymous registration exhaustion and owner recovery

The server now bounds all registration metadata to 4096 bytes. Unapproved registrations have a separate 128-client admission budget and expire after ten minutes. Approved registrations use a separate budget.

The independent probe fills all 128 unapproved slots. The next request returns the OAuth `invalid_client_metadata` response with HTTP 400. Owner token enrollment still succeeds. Owner cleanup admits a new registration and preserves an active refresh credential. Expired registrations leave the quota before the next admission.

The supplied regression test also confirms that a nearly full credential file cannot publish an enabled grant or enable sharing. Credential admission precedes grant publication. An orphan credential cannot authorize a call because the corresponding grant must exist and remain enabled.

### Frozen SDK exceptions

`CredentialUpdate` is a class context manager. It releases the underlying generator lock without passing the SDK exception through that generator. Registration capacity errors and pending-request capacity errors now reach SDK handlers.

The independent pending-request probe returns a normal authorization redirect with `temporarily_unavailable`. A sharing change after refresh lookup produces the actual SDK `TokenError`. The supplied preloaded refresh race test also passes. I find no remaining path where the reviewed SDK exceptions cross the nested configuration generator lock in `_admit()`.

## Additional checks

- The native Hermes host test mounts the transport from an installed plugin copy and refuses calls after plugin disablement.
- Dashboard owner routes still require an authenticated owner session. An MCP bearer token does not authenticate those routes.
- The server selects the memory client from the verified credential. Tool arguments cannot select an owner or another grant.
- Credentials bind to the configuration path, native root, principal, HTTP epoch, and origin.
- Native operations recheck credentials and client grants during tool execution.
- The SDK validates PKCE and redirect continuity. The middleware requires the exact configured resource at token exchange.
- Owner revocation disables policy before removing credentials. This order fails closed if cleanup fails.
- Approval publishes credentials before policy. Storage failure cannot publish a usable grant without credentials.
- The component UI exposes explicit grant controls, owner consent, revocation, and registration cleanup. It escapes client-supplied strings through React.
- The documentation accurately distinguishes Tailscale Serve, Funnel, network reachability, and application authorization.

## Limits

I do not repeat the actual Codex CLI or cross-peer Tailscale run. I read their safe receipts and source. I do not independently repeat the full integration suite. The primary owns that parallel run. The HTTP tests exercise actual TCP and TLS listeners with native synthetic facts. The reported localhost peer probe uses the real ASGI application through TestClient, not a separately routed LAN socket.

The planned version bump is intentionally pending review closure. It is not a finding.
