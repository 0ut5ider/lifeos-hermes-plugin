# Connect external agents to LifeOS memory over HTTP

The LifeOS Bridge includes a Streamable HTTP Model Context Protocol (MCP) server.
The server uses the existing Hermes dashboard listener. Installation does not add
a daemon, an SSH account, or another Hermes patch. HTTP access starts disabled.

Each connection has an owner-approved memory grant. The grant specifies read
categories, projects, project write access, and the declared model route. HTTP
clients use the same governed native operations as Hermes and the stdio server.
They do not receive an owner dashboard session or approval rights for identity
changes. A client name and a model route declaration do not verify the client.

## Recommended private network setup

Use [Tailscale Serve](https://tailscale.com/docs/reference/tailscale-cli/serve)
to provide a private HTTPS origin. The server and each client computer must have
network access through the tailnet. Tailscale provides network access and TLS.
LifeOS still authenticates each MCP connection and checks its memory grant.
Tailscale is optional. Another trusted HTTPS reverse proxy can serve the endpoint.

1. Install Tailscale on the Hermes server and client computers.
2. Sign those computers into the intended tailnet.
3. Restrict tailnet access to the computers that need memory access.
4. Enable HTTPS for the tailnet if Tailscale requests it.
5. Keep Hermes dashboard owner sign-in enabled.
6. Run `tailscale serve --bg http://127.0.0.1:9119` on the Hermes server.
7. Set Hermes `dashboard.public_url` to the HTTPS origin that Tailscale reports.
8. Restart the Hermes dashboard after changing its public URL or installing the plugin.
9. Open **LifeOS Bridge**, then **Lasting memory**, then **Connect agents over HTTP**.
10. Enter that same HTTPS origin and select **Save and enable HTTP MCP**.
11. Enable memory sharing before an agent starts OAuth sign-in.
12. Copy the displayed MCP URL into the agent's MCP configuration.

Use the actual dashboard port if it differs from `9119`. Bind the backend to
loopback when it needs access only through the proxy. Serve the origin without a
path rewrite. The plugin requires an origin without a path, query, or fragment.
HTTP origins are accepted only for localhost tests. The MCP path is:

```text
/api/plugins/lifeos-hook-bridge/memory/http/mcp
```

Tailscale Serve limits access to the tailnet. Tailscale Funnel makes a service
public and is outside this recommended setup. A hosted agent service cannot
reach a private tailnet endpoint unless that service has a network path into
the tailnet. The plugin does not join a tailnet or change Tailscale settings.

## Sign in from an agent

The server supports OAuth authorization codes with S256 Proof Key for Code
Exchange (PKCE), protected-resource discovery, dynamic client registration, and
refresh-token rotation through the installed MCP SDK. Client ID metadata
documents are not supported. Clients must support dynamic registration or use
the separate bearer-token option below.

1. Add the displayed MCP URL to the agent as a remote HTTP MCP server.
2. Start MCP sign-in from the agent.
3. Sign in to the Hermes dashboard as the installation owner when the browser opens.
4. Open **Connect agents over HTTP** and select **Review connection requests**.
5. Check the requesting agent's displayed name and callback address.
6. Enter a distinct connection name, projects, and declared model route.
7. Select the permitted read categories and project write access.
8. Select **Approve** for that request.
9. Select **Return to agent** to deliver the authorization code to its callback.

Requests expire after ten minutes. Codes expire after two minutes and work once.
Access tokens expire after one hour. Refresh tokens expire after thirty days.
Refreshing a connection replaces its access and refresh tokens. Requests must
identify the exact displayed MCP URL as their OAuth resource. The server refuses
credentials from another origin or installation.

Codex CLI configuration can use:

```toml
[mcp_servers.lifeos-memory]
url = "https://YOUR-SERVER.YOUR-TAILNET.ts.net/api/plugins/lifeos-hook-bridge/memory/http/mcp"
```

Run `codex mcp login lifeos-memory` after the server is configured. Claude Code
can add the endpoint with `claude mcp add --transport http lifeos-memory URL`.
OpenCode can configure an MCP server with `"type": "remote"` and `"url": "URL"`.
Use each client's MCP sign-in control. These examples describe client setup.
The verification record states which actual clients have been tested.

## Use a bearer token

Some clients cannot complete browser sign-in. The owner can create a separate
90-day token for one connection.

1. Enter a distinct connection name in **Connect agents over HTTP**.
2. Enter the projects and declared model route.
3. Select the permitted read categories and project write access.
4. Select **Create agent token (90 days)**.
5. Copy the displayed token into the client's private credential configuration.
6. Select **Hide token** after saving it privately.

The page shows the token once. The server stores its hash. Do not put a token
in a URL, prompt, repository, or shared client configuration. The client sends
`Authorization: Bearer TOKEN`. Codex can read a private environment variable:

```toml
[mcp_servers.lifeos-memory]
url = "https://YOUR-SERVER.YOUR-TAILNET.ts.net/api/plugins/lifeos-hook-bridge/memory/http/mcp"
bearer_token_env_var = "LIFEOS_MEMORY_TOKEN"
```

Creating a token enables memory sharing for every connection whose grant remains
enabled. Check the listed connections before creating the token. The default
HTTP grant permits project reads for the selected projects and no writes.
An explicit checkbox permits project writes. Identity reads require separate
checkboxes. Every returned fact can enter the configured model's context.

## Revoke, update, and recover

**Revoke HTTP** disables the grant and removes its active credentials. The server
checks credentials and grants again during tool operations. A dashboard cookie
does not authenticate an MCP request. An MCP token does not authorize dashboard
settings or an owner approval request.

**Disable HTTP MCP and invalidate credentials** stops the endpoint and invalidates
HTTP credentials. Changing the public origin also invalidates credentials and
disables the affected grants. Use a distinct connection name for reauthorization.
The general memory-sharing control pauses all memory connections. Turning it
back on resumes credentials that are still valid and have not been revoked.

The selected Hermes profile stores HTTP settings in `lifeos-memory.json` and
private credential state in `lifeos-memory-http-credentials.json`. Program
updates and dashboard restarts retain these files. Access tokens, refresh tokens,
and authorization codes are stored as hashes. OAuth registration metadata,
including a confidential client's registration secret when requested, remains
in the private credential file. Keep profile backups private.

Profile recovery preserves the files but leaves ownership and sharing disabled.
The changed native root prevents the recovered copy from reusing an original
credential. Reauthorize connections before using a recovered installation. A
whole-guest restore returns historical settings and credentials. Review and
revoke old connections after that restore before allowing remote access.

The HTTP endpoint supports the dashboard's in-process plugin mode. A separately
hosted plugin process does not install the HTTP transport into the dashboard.
Restart the dashboard after installing or enabling the plugin. The existing
optional SSH sharing component remains available for installations that use SSH.

## Verification and protocol references

- [HTTP memory acceptance](verification/2026-10-16-http-memory/README.md)
- [MCP HTTP authorization](https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization)
- [Tailscale Serve reference](https://tailscale.com/docs/reference/tailscale-cli/serve)
- [Claude Code MCP configuration](https://code.claude.com/docs/en/mcp)
- [OpenCode MCP configuration](https://opencode.ai/docs/mcp-servers/)
- [Codex MCP configuration](https://learn.chatgpt.com/docs/extend/mcp?surface=cli)
