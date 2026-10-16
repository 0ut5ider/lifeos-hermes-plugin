# HTTP memory review 3

Date: 2026-10-16

Role: Independent security and correctness reviewer

Question: Does PR32 resolve previous findings and safely provide HTTP MCP with owner-approved memory grants?

Model: GPT-6.1-sol, high reasoning effort

Reviewed commit: `1c50bbc4f03dee337b432225a042c85b01df32f7` on `feature/http-memory-mcp`.

Baseline: `67c5641b57608537526414991a652b6ad6f78b0e`.

Pull request: <https://github.com/0ut5ider/lifeos-hermes-plugin/pull/32>

## Result

No findings remain in this review. The reviewed changes resolve all four findings from the first two rounds.

All 19 targeted Python tests pass. All three HTTP dashboard component tests pass. Independent synthetic probes pass. The raw results are `targeted-tests.txt`, `ui-tests.txt`, `probe-output.txt`, and `probe-results.json`. The probe source is `review_probes.py`.

The review uses disposable native memory fixtures. It does not change product source, deployed configurations, services, client settings, or personal memory. It does not call memory or journal tools. It does not push or merge.

## Previous finding verification

### Refresh replay

A consumed refresh token returns HTTP 400 and revokes its replacement family. The replacement access token fails authentication. The replacement refresh token also returns HTTP 400. An unrelated connection remains valid.

The preloaded refresh race test receives the SDK `TokenError` and revokes the family. A wrong OAuth client cannot use a consumed token to revoke another client's family. A fresh service object recognizes the persisted consumed markers.

### Anonymous registration limits and owner recovery

All 128 unapproved registration slots admit requests. The next request returns HTTP 400 with `invalid_client_metadata`. Owner bearer enrollment still succeeds after that limit. Owner cleanup removes unused registrations and preserves an active refresh credential. A new registration then receives HTTP 201.

Registration metadata has a separate 4096-byte limit. Expired unapproved registrations leave the admission count. The pending-request limit returns a normal OAuth error redirect. A full credential file does not publish an enabled grant or enable sharing.

### Frozen SDK exceptions

The credential transaction releases the generator lock without forwarding the frozen SDK exception through it. Pending-capacity and binding-change probes return the intended OAuth error types. The targeted tests also cover the preloaded refresh race.

### Localhost HTTP peer restriction

Independent probes test every intercepted public path with a non-loopback peer and with no peer metadata. All fourteen requests return HTTP 400. This includes both discovery paths, authorization, registration, token exchange, revocation, and MCP.

The valid bearer-token probe returns HTTP 400 and no tools for a non-loopback peer. A valid loopback bearer request succeeds in the targeted tests. Direct HTTPS requests from a non-loopback peer remain valid. A local TLS proxy remains valid. An untrusted `X-Forwarded-Proto` header does not authorize plaintext LAN access. Default HTTPS and HTTP ports normalize to their canonical origins.

## Additional review scope

- The credential binding includes the configuration path, native root, principal, HTTP epoch, and public origin.
- Authorization code exchange uses SDK PKCE validation and single-use code admission. Token exchange requires the exact configured resource.
- Owner grant admission publishes credentials before the policy grant. A credential without its grant cannot authorize a request.
- Revocation disables policy before credential cleanup. Native calls recheck the credential and current grant.
- The existing MemoryService selects the client from the verified token. Tool arguments cannot select another identity.
- Dashboard owner routes require a verified owner session. An MCP bearer token does not authenticate those routes.
- The native Hermes host test verifies plugin mounting and live disablement without another host patch.
- The dashboard shows callback addresses and explicit read, project, and write controls. React renders client names and callback labels as text.
- The documentation describes the default-disabled endpoint, Tailscale Serve, private credential storage, revocation, and recovery limits.

## Limits

I rerun the targeted tests with actual TCP and TLS listeners and native synthetic facts. I do not repeat the full integration suite, which the primary runs in parallel. I read the Codex OAuth and cross-peer Tailscale receipts but do not repeat those external-client runs.

The peer-boundary probes use ASGI TestClient metadata. They complement the actual TCP and TLS tests. They do not simulate another physical LAN or another tailnet.

The documented separate plugin-host process mode and Client ID Metadata Documents remain unsupported. The version bump follows review closure. These are not findings.
