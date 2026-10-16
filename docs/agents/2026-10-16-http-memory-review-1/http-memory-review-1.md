# HTTP memory review 1

Date: 2026-10-16

Role: Independent security and correctness reviewer

Question: Does PR32 safely add built-in HTTP MCP and OAuth without breaking governed memory or owner controls?

Model: GPT-6.1-sol, high reasoning effort

Reviewed commit: `f4f0c8e8` on `feature/http-memory-mcp`.

Baseline: `67c5641b57608537526414991a652b6ad6f78b0e` (`origin/main`).

Pull request: <https://github.com/0ut5ider/lifeos-hermes-plugin/pull/32>

## Result

Changes are required. I reproduced three defects. The first affects refresh-token compromise detection. The second permits persistent registration exhaustion. The third converts expected OAuth errors into server failures.

The supplied targeted test command passes 13 tests. See `targeted-tests.txt`. The independent synthetic probes succeed and record the defects in `probe-results.json` and `probe-output.txt`. The reproduction program is `review_probes.py`. These probes use disposable native fixtures. They do not read or change a live profile, a credential, a service, or a personal record.

## Finding 1: P1, refresh-token reuse does not revoke the active family

Location: `lifeos_hook_bridge/memory_oauth.py:123-130` and `lifeos_hook_bridge/memory_oauth.py:140-152`.

`_issue()` removes every previous token in a family. The server retains no consumed refresh-token record. Consequently, `load_refresh_token()` treats a replay as an unknown token. The active replacement tokens stay valid.

The probe completes dynamic registration, PKCE authorization, owner approval, and a code exchange through the actual HTTP router. It refreshes the first token once, then replays the first refresh token. The replay receives HTTP 400. The replacement access token still lists tools with HTTP 200. The replacement refresh token still obtains another token pair with HTTP 200.

If an attacker steals a public client's refresh token and uses it first, the legitimate client's next refresh detects a conflict. This implementation rejects that client request but leaves the attacker's replacement credentials usable. The attacker can continue refreshing the connection.

The OAuth security best practice requires the rotation mechanism to retain the relationship between old and current refresh tokens. Reuse must revoke the active refresh token. The rule applies to public clients that do not use sender-constrained tokens. See [RFC 9700, section 4.14.2](https://www.rfc-editor.org/rfc/rfc9700.html#section-4.14.2).

Minimal correction: retain private hashes of consumed refresh tokens with the family, client, binding, and bounded expiry. Atomically recognize reuse and revoke the active family. Do not let an unrelated client revoke another client's family by presenting a token. Test sequential reuse, simultaneous exchange attempts, a restart, and unrelated-family isolation. Do not return plaintext consumed tokens.

## Finding 2: P2, unapproved registrations exhaust persistent shared credential storage

Location: `lifeos_hook_bridge/memory_oauth.py:35-49`; `lifeos_hook_bridge/memory_remote.py:81-94` and `lifeos_hook_bridge/memory_remote.py:189-198`.

The registration endpoint accepts requests without owner authentication. It keeps 512 registrations for one year. The owner page has no registered-client cleanup action. Changing the HTTP epoch does not remove registrations.

The count probe sends 512 small anonymous registrations. All return HTTP 201. The next registration fails. Disabling and enabling HTTP preserves all 512 entries, and the next registration still fails. No owner memory grant exists for any of those clients. The current error response is HTTP 500 because of finding 3.

The byte probe is more severe. It registers four clients with a one-million-character `software_id` each. All return HTTP 201 within the one-megabyte request limit. Two further registrations fill the shared credential file to 4,194,185 bytes. This leaves 119 bytes below the four-megabyte cap. The owner then creates a normal connection. Enrollment raises `MemoryUnavailable: HTTP credential storage exceeds its limit`. `_admit()` has already persisted an enabled grant, although no token is published. The count limit does not prevent this attack.

A caller who can reach the endpoint can block new agent sign-in and owner token creation without receiving a memory grant. The caller needs tailnet reachability under the recommended setup. An owner-configured public proxy also exposes this path. A global HTTP disable/enable cycle does not repair the registry.

Minimal correction: bound all persisted registration metadata, not only the name and redirect addresses. Keep unapproved registrations short-lived or use a separate bounded admission budget. Reserve credential capacity for approved connections and rotation. Add an authenticated owner cleanup action that works when admission is full. Do not persist an enabled grant or enable sharing if credential publication fails. Test count exhaustion, byte exhaustion, and recovery through owner controls.

## Finding 3: P2, OAuth errors cross generator contexts as FrozenInstanceError

Location: `lifeos_hook_bridge/memory_remote.py:81-94`; `lifeos_hook_bridge/memory_oauth.py:45-47`, `lifeos_hook_bridge/memory_oauth.py:133-152`.

The pinned MCP SDK declares `RegistrationError`, `AuthorizeError`, and `TokenError` as frozen dataclasses. The credential transaction and configuration lock use `contextlib.contextmanager`. When a frozen OAuth exception leaves these generator contexts, Python attempts to assign its traceback. The assignment raises `dataclasses.FrozenInstanceError` before the SDK handler can produce the OAuth response.

The 513th registration triggers this exact stack. A deterministic refresh race also triggers it. The probe loads a valid refresh credential, exchanges it once, then presents the previously loaded credential to `exchange_refresh_token()`. This is the same ordering that occurs when two workers load one credential before either obtains the transaction lock. The second exchange raises `FrozenInstanceError: cannot assign to field '__traceback__'`, rather than `TokenError('invalid_grant', ...)`.

This path fails closed, but clients receive a server error for expected invalid-grant and admission failures. It also prevents the documented OAuth error handling from operating in those races.

Minimal correction: do not raise SDK frozen exception instances through generator context managers. Use a normal internal exception inside the transaction and translate it to the SDK error after the context exits. An appropriate class-based transaction context is another option. That class must not forward the frozen exception to the underlying `MemoryConfiguration._lock()` generator context. Test registration-limit errors, pending-request limits, code and refresh exchange races, and binding changes between lookup and exchange through HTTP.

## Proposed correction assessment

The primary proposes hashed consumed refresh markers, atomic family revocation on reuse, a normal transaction context, bounded short-lived unapproved registrations, and owner cleanup. Those changes address the measured findings. The owner cleanup must preserve active approved clients and remain usable when admission storage is full. Unapproved metadata must not consume the budget required for approved credentials. Consent and enrollment must not publish an enabled grant before credential storage admission succeeds. No additional product architecture is required to fix these defects.

## Reviewed behavior without a confirmed defect

- Dashboard owner routes require a real Hermes dashboard session and the configured owner binding.
- MCP bearer credentials do not authenticate dashboard settings routes.
- The HTTP endpoint binds credentials to the configuration path, native root, owner principal, epoch, and origin.
- The middleware rejects an unconfigured host, an unrelated Origin, plaintext LAN requests, and query-string MCP credentials.
- Native tool calls recheck the bearer credential and the existing client scope during governed operations.
- The existing code-exchange path uses SDK PKCE and redirect checks. Credential exchange consumes one authorization code under the store lock.
- Client grant revocation disables the grant before credential cleanup. A concurrent token publication cannot bypass the disabled grant check.
- Copied and recovered profile tests reject credentials from the original profile.
- The setup guide correctly distinguishes private Tailscale Serve from public Funnel. It documents unsupported client metadata documents and the in-process host limitation.

## Scope and limits

I did not repeat the actual Codex CLI or cross-peer Tailscale run. I read their safe evidence and reproduction programs. I did not independently repeat the full integration suite, which the primary agent runs in parallel. I reviewed the actual pinned Hermes host mounting and the pinned MCP SDK handlers. The supplied native-host test passes.

I made no product changes. Only this report and its reproduction artifacts were created. No subagents were used.
