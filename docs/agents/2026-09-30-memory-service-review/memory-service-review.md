Date: 2026-09-30
Role: Independent service and MCP implementation reviewer
Question: Do the shared service and installed MCP stdio server preserve grant binding, current configuration, revocation, malformed-input rejection, and unavailable outcomes?
Model: GPT-6 session model. The exact deployed model variant is not exposed to this reviewer.

# Memory service review

The five service tests and one real installed-copy MCP test pass. Independent probes confirm three defects: configuration reads can combine one grant with another store root, the MCP SDK can discard malformed write arguments before shared validation, and database failures escape the service's unavailable-result contract.

This report applies to the source snapshots in `raw/reviewed-*` and hashes in `raw/reviewed-hashes.json`. It does not assess subsequent changes by the primary agent. Each confirmed finding was sent promptly during the review.

## 1. High: one request can use a grant and root from different configuration revisions

Location: `memory_service.py`, `MemoryService.call_client`, `client_scope`, and `call`.

`call_client()` resolves the client's scope by loading configuration. It then calls `call()`, which loads configuration again to select the native root. A configuration change between those reads can apply a previous grant to a different store.

The `mixed_configuration_revision` probe creates two real synthetic roots. Configuration A enables the research client against root A. After the first real configuration read, the probe atomically replaces the file with configuration B, which selects root B and disables sharing. The in-flight search returns a private synthetic marker from root B under A's old grant. The next call correctly rejects the revoked connection.

The probe uses a controlled scheduling point around the real `load()` and `save()` operations. It does not mock the native backend or substitute a fabricated configuration result. It reproduces a configuration replacement that can occur between the two ordinary reads.

Use one authoritative configuration snapshot for grant resolution and store selection, or validate the same configuration revision before access. Do not combine a resolved scope with a later root. The public `call(scope, ...)` path also needs a clear freshness contract for trusted host callers before integration; loading a new configuration does not itself refresh an already resolved scope.

## 2. High: MCP argument preprocessing bypasses rejection before a destructive operation

Location: `memory_mcp.py`, generated `@server.tool()` handlers and their input schemas.

The shared service rejects missing and unknown fields and checks exact integer types. The MCP SDK first parses the decorated function arguments. In the installed SDK, that parsing silently discards unknown top-level fields and coerces some values before the shared validator sees them.

The real installed-copy stdio probe submits a valid forget reference and request ID plus `dry_run: true`:

- Direct `MemoryService.call_client()` rejects the payload because it contains an unknown field.
- The MCP call returns `committed` and forgets the synthetic fact.
- Reading its original reference afterward returns conflict, confirming the mutation occurred.

The probe does not assume that dry-run behavior is supported. The required behavior is to reject an unsupported field consistently before mutating. Instead, the MCP layer removes the field and executes a different valid request.

The MCP tool schema lacks top-level `additionalProperties: false` and exposes reference as an arbitrary object. The schema differs from the shared precise reference schema. The same real connection also accepts `limit: true` after coercion, while the shared validator requires an exact integer.

Enforce the shared strict schema against the original MCP arguments before SDK coercion or field removal. Derive both interface schemas from the same contract so that unknown write arguments cannot be silently discarded. The installed-copy regression should prove that an unsupported field causes rejection and leaves native content and reference status unchanged.

## 3. Medium: native database errors escape the unavailable-result contract

Location: `memory_service.py`, `MemoryService.call` exception handling and status branch.

The service catches `MemoryUnavailable`, `ValueError`, and `OSError`. Native read operations can also raise `sqlite3.Error`. Those errors escape `call()` rather than becoming a structured unavailable result.

The `database_unavailable_contract` probe replaces only its disposable SQLite file with invalid synthetic bytes. Search and get both raise `DatabaseError: file is not a database`. The status tool still returns `status: ok` because it checks the root boundary but does not exercise database availability.

The real MCP probe produces `is_error: true` with a plain error message and no structured content for the same failure. No false save result occurs, but the shared response contract is lost. This also gives trusted service callers an uncaught exception.

Normalize expected backend failures at the service boundary and make the status response accurately distinguish checked availability from configured access. Review timeout handling at the same boundary: native read subprocess timeouts also propagate outside the current exception set. The timeout path was inspected but was not separately delayed or injected in this review.

## Verified behavior

The existing tests establish the following results against actual native synthetic facts:

- Sharing is disabled unless explicitly enabled.
- A reader obtains the same native reference as the local owner.
- Category and project grants exclude principal facts from project readers.
- Read-only clients cannot write.
- Project-write clients cannot write principal memory.
- Normal revocation between tool calls applies to an already open service and an already open MCP connection.
- Get rejects stale references and returns the current corrected fact for its current reference.
- Saved configuration files use mode 0600, and enrollment validation rejects principal write grants.
- The plugin module works from its copied installation directory through the actual MCP stdio client.

The source review also confirms that tool arguments do not select the connected client's grant. The connection's client identifier comes from the server launch. Get checks read grants and active revision before returning content and provenance.

## Authentication and OS boundary

The current `--client` argument selects a server-side grant. It is not authentication by itself for a local process running under the same operating-system user. Such a process can choose another argument, access owner files, or bypass this interface where filesystem permissions permit it.

SSH enrollment and its authenticated forced-command binding are scheduled next work and are not claimed here. This review does not count missing SSH enrollment as a defect in the current service. The installed-copy test verifies grant selection, tool behavior, and revocation. It does not prove remote credential authentication or isolation from the same UID.

## Commands and results

SDK interpreter: `/home/outsider/.cache/lifeos-plugin-memory/sdk-env/bin/python`, with the provided MCP 2.0.0 environment.

- `python -m unittest discover -s tests -p 'test_memory_service.py' -v`: 5 tests passed in 1.541 seconds.
- `python -m unittest discover -s tests -p 'test_memory_mcp.py' -v`: 1 installed-copy stdio test passed in 1.297 seconds.
- `raw/probe_service.py`: both configuration and database probes completed.
- `raw/probe_mcp.py`: actual installed-copy connection confirmed malformed-argument mutation, integer coercion, and database error representation. Server stderr was empty.

All commands used the SDK interpreter above. Full command lines are in `raw/commands.txt`. The diagnostic scripts record observed failures rather than claiming to be passing regression tests.

## Scope and artifacts

Reviewed files: `memory_service.py`, `memory_mcp.py`, the new `NativeMemory.get`, relevant existing access and policy contracts, `test_memory_service.py`, `test_memory_mcp.py`, and the plugin dependency declaration. SDK parsing source was inspected locally to identify the argument preprocessing boundary.

All native data, configuration changes, copied installations, database corruption, and deletion probes occurred under temporary synthetic fixtures. No remote runtime, production memory, production logs, deployed configuration, memory service, or journal service was accessed. This reviewer edited no implementation files and made no commits.

Artifacts:

- `raw/service-tests.txt` and `raw/mcp-tests.txt`: complete baseline outputs.
- `raw/probe_service.py` and `raw/service-probes.jsonl`: configuration and unavailable-result evidence.
- `raw/probe_mcp.py` and `raw/mcp-probes.json`: full installed-copy protocol and mutation evidence, including the exposed schema.
- `raw/reviewed-*` and `raw/reviewed-hashes.json`: reviewed working-tree sources and hashes.
- `raw/commands.txt`: exact commands and probe interpretation.

The configuration snapshot and strict MCP input boundary deserve review before external access is enabled. The service should also return a stable unavailable result for real backend failures. Provider, native delegation, UI, release, and SSH enrollment remain outside this bounded review.
