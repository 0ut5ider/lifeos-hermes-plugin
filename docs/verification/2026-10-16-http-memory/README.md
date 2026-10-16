# HTTP memory MCP acceptance

The branch adds Streamable HTTP memory access to the existing Hermes dashboard
listener. The installed MCP SDK remains `2.0.0`. Hermes remains v0.21.7 with ten
patches. The transport requires no additional Hermes patch or Python dependency.

The targeted local check passes 43 tests. The initial dashboard check passes all 35 UI
tests. These checks cover native memory operations, authenticated owner controls,
private hashed credentials, explicit project grants, cross-client isolation,
PKCE, one-time codes, refresh rotation, revocation, request limits, copied-profile
refusal, recovered-profile refusal, and the existing stdio and SSH paths.

The actual native Hermes dashboard imports an installed copy of the bridge and
mounts its HTTP transport at startup. Anonymous discovery succeeds. MCP tokens
cannot access owner settings. Runtime plugin disablement refuses MCP requests.
The network tests use real TCP listeners and native synthetic memory. The HTTPS
test verifies a test certificate through an explicit certificate authority.

The [development receipt](development-verification.json) records 28 passing tests
on `.252` with its selected 0.6.0 Python environment and native Hermes source.
The source copy and native records are isolated. No active release files change.
The first development run points at extracted native source without installed
YAML dependencies. That run fails. The corrected fixture uses a separate copy
of public source and the installed public YAML dependency. It preserves the
selected production program.

The [Codex receipt](codex-oauth-verification.json) records actual Codex CLI
0.163.0 login. Discovery, dynamic registration, S256 PKCE, owner consent, callback,
and credential persistence pass. The probe uses a disposable `CODEX_HOME` and a
synthetic store. It does not change a deployed client configuration. The probe
approves the synthetic owner request through the owner helper. Separate HTTP
tests verify authenticated owner session protection for the dashboard API.

The [Tailscale receipt](tailscale-verification.json) records HTTPS requests from
a separate tailnet peer. The peer lists nine tools, saves a synthetic project
fact, recalls its exact reference, and receives 401 after revocation. It verifies
the server certificate through its system trust store. The temporary Serve
listener is removed. The prior Serve configuration remains unchanged. The peer
does not create a credential file or access its existing memory server.

Serve initially requires the owner to enable the tailnet feature. Adrian enables
it during acceptance. A same-machine HTTPS probe then reaches a connection
timeout. The separate tailnet peer passes. This record establishes remote access
between tailnet machines. It does not establish same-machine Serve access.

The private probe outputs remain outside Git. The replay programs in this
directory contain synthetic fixture setup and safe receipts. They contain no
credentials or private memory. The full integration result and independent
review closure are recorded here before merge.

The [first independent review](../../agents/2026-10-16-http-memory-review-1/http-memory-review-1.md)
finds refresh replay, registration exhaustion, and frozen SDK exception defects.
The primary independently repeats all three probes. Regression tests verify
family revocation and unrelated-client isolation, the original refresh exchange
race, bounded registration metadata, owner cleanup, and refusal of a partial
grant when credential storage is full. The owner cleanup has an authenticated
API and a tested button. The next review checks the corrections before merge.

The [second independent review](../../agents/2026-10-16-http-memory-review-2/http-memory-review-2.md)
confirms those three corrections and finds a remaining plaintext boundary.
A valid bearer from a non-loopback peer can reach a localhost HTTP origin when
its Host header matches. The primary reproduces HTTP 200 before the correction.
The corrected transport requires a loopback peer for HTTP origins. Tests verify
HTTP 400 for LAN and absent peer addresses, successful local requests, and the
existing HTTPS proxy path. Explicit default HTTPS ports normalize to the same
origin. The updated direct check passes 19 tests.

This acceptance does not publish or deploy a release package. Development and
daily remain on qualified 0.6.0. Claude Code and OpenCode HTTP login have not yet
been replayed. Their configuration examples are instructions, not acceptance
claims. No current Codex, Claude Code, OpenCode, or Hermes MCP connection changes.
