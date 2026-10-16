# HTTP memory without another Hermes patch

The first transport hypothesis uses Hermes's token-provider extension. That
extension recognizes exact protected routes, but an OAuth client also needs
public metadata, registration, authorization, and token endpoints. Its generic
401 response does not provide MCP protected-resource discovery. An HTTP server
on a fourth service would add another installation and recovery lifecycle.

The bridge already installs response middleware while Hermes imports plugin API
routes. The HTTP transport uses that startup point to serve a small exact set of
MCP and OAuth paths before dashboard cookie authentication. Those paths have
their own host, origin, credential, resource, and memory-grant checks. Owner
configuration and consent remain behind native authenticated dashboard routes.
The native-host test imports an installed plugin copy into the exact prepared
Hermes app. It lists nine tools, preserves the cookie boundary, and refuses
requests after plugin disablement. The Hermes patch count stays at ten.

The SDK supports a stateless server per HTTP request. That makes client binding
local to each authenticated request. The existing memory service rechecks the
grant and credential during its native operation. The actual SDK client saves
and recalls a synthetic fact over TCP and verified TLS. Codex CLI 0.163.0
completes OAuth login. A separate Tailscale peer lists all nine tools, saves and
recalls the exact synthetic reference, then receives 401 after revocation.

A copied profile test catches an installation-binding omission before review.
Root, principal, origin, and epoch alone allow a copied profile to reuse a token
against the same native store. Adding the configuration path to the credential
binding makes the test pass. Recovered profiles also refuse original credentials
after ownership and sharing are reenabled.

Independent review measures two additional boundaries. Refresh replay initially
returns 400 while replacement access and refresh credentials both remain valid
with 200. Consumed token hashes must survive rotation so reuse can revoke the
family. Anonymous registration also fills the four-megabyte credential file to
4,194,185 bytes. The owner then receives an enrollment failure after a grant is
published. Registration admission now has its own metadata and count budget,
and credential publication precedes memory-grant publication.

The pinned SDK represents OAuth errors as frozen dataclasses. Python's generator
context manager assigns an exception traceback while unwinding. That assignment
replaces the intended SDK error with FrozenInstanceError. The class-based
credential update releases the underlying generator lock without passing the
frozen exception through it. The HTTP regression checks receive the intended
OAuth error responses.

The second review measures a plaintext boundary: a non-loopback TCP peer with a
loopback-looking Host header and a valid token receives nine tools. HTTP origins
now require an actual loopback peer. Independent probes receive 400 across all
seven public paths for both a remote peer and absent peer metadata. Direct HTTPS
and a local TLS proxy still work. The third review has no remaining findings.

OpenCode 2.0.30 initially reports no MCP servers in its isolated profile. Its
configuration debugger shows the expected server. The native CLI source reads
MCP status through the background service. A bounded second status query reports
the connection. A single cold-start status query is insufficient client evidence.
Codex completes actual OAuth login, and Claude Code and OpenCode pass bearer
health checks without changing the deployed client configuration.
