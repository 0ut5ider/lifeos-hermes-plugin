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
