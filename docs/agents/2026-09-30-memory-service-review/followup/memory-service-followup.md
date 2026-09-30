Date: 2026-09-30
Role: Independent service and MCP fix reviewer
Question: Do the configuration snapshot, raw MCP validation, and unavailable-result fixes close the three reported service defects?
Model: GPT-6. The session does not expose a more specific deployed model identifier.

# Service and MCP follow-up

All three previously reported defects are fixed in the reviewed versions. Seven service tests and one actual installed-copy MCP stdio test pass. Rerunning the original independent probes confirms consistent grant/root selection, rejection of malformed writes without mutation, and structured unavailable results. No new meaningful defect was found in the bounded reviewed scope.

The reviewed source snapshots and SHA-256 hashes are preserved in `raw/`. Other native curation work was active in the shared checkout. This review did not inspect or change that work; only the `get` method from `memory_access.py` was included in its access-code snapshot.

## Configuration snapshot fix

`call_client()` now loads configuration once, derives the client scope from that object, and passes the same object to `_call()` for root selection. `call_context()` follows the same pattern for trusted host context.

The original configuration-rotation probe now returns an empty allowed result from the original root. It does not return the synthetic marker from the newly selected private root. The following call sees revocation and returns `rejected`.

This establishes the intended per-request snapshot behavior. A request already authorized under its starting snapshot can finish against that same root; the next request loads the new grant. The service no longer combines a previous grant with a later root.

## Raw MCP validation fix

The server now registers the shared tool schemas through the low-level official SDK server and passes the original argument mapping to the shared service validator. It no longer uses decorated function parsing that discarded or coerced fields first.

The original real installed-copy probe confirms:

- Forget with unsupported `dry_run: true` returns `rejected` through both direct service access and MCP.
- The original record remains active at revision 1 with its original content after the rejected call.
- Search with `limit: true` returns `rejected` with reason `Invalid limit`.
- The exposed forget schema includes `additionalProperties: false` at the tool and reference levels.
- The reference schema exposes the required ID and positive integer revision fields.

These are actual SDK stdio calls to a copied installation. The probe uses a client with project write permission, so permission denial cannot conceal a failure to validate the malformed destructive request.

## Unavailable-result fix

The service now catches SQLite errors and native subprocess timeouts alongside its previous backend exceptions. The status path checks database access and native retrieval capability rather than reporting success solely from a valid root boundary.

With the disposable SQLite database deliberately corrupted, the original service probe returns `status: unavailable` for status, search, and get. No database exception escapes the service.

The actual MCP connection returns structured content containing `status: unavailable` and the database failure reason. The SDK does not replace the result with its previous generic tool exception response. Server stderr is empty.

Timeout coverage was inspected in the exception handling but was not separately delayed in this follow-up. The review makes no claim about a measured timeout run.

## Tests and independent evidence

SDK interpreter: `/home/outsider/.cache/lifeos-plugin-memory/sdk-env/bin/python`.

| Check | Result |
| --- | --- |
| Service tests | 7 passed in 2.223 seconds |
| Real installed-copy MCP test | 1 passed in 1.442 seconds |
| Original configuration-rotation probe | Old root retained for the in-flight call; next call rejects |
| Original corrupt-database service probe | Status, search, and get return unavailable |
| Original malformed MCP write probe | Rejected; original record remains active |
| Original boolean-limit MCP probe | Rejected without coercion |
| Original corrupt-database MCP probe | Structured unavailable result |

The existing tests continue to verify disabled sharing, category restrictions, project-write limits, current references, private configuration permissions, and revocation on an already open connection. All executed tests passed without skips or stderr failures.

## Trust boundary and limits

`call_client()` binds the current server-selected client identifier to a fresh configuration snapshot. `call_context()` resolves a trusted host context from the same snapshot used for storage access. The lower-level `call(scope, ...)` remains a trusted helper that accepts a preauthorized scope. It does not authenticate the supplied scope or establish its freshness; future host integration should use the context-bound entry point where current grants must be resolved.

The `--client` argument still selects a grant rather than authenticating a local same-UID process. Filesystem access under that UID remains outside this service boundary. SSH credential binding and enrollment were not part of this review.

Reviewed files are `memory_service.py`, `memory_mcp.py`, the `get` method in `memory_access.py`, and the service/MCP tests. No new native curation methods, delegation paths, provider, UI, release, or deployment were reviewed. This result closes the three service findings and does not establish completion of the full memory integration.

All probes use disposable synthetic configuration, memory records, copied plugin files, and actual native/MCP tools. No live runtime, production memory or logs, remote hosts, deployed configuration, memory service, or journal service was accessed. No implementation file was edited and no commit was made by this reviewer.

## Artifacts

- `raw/service-tests.txt` and `raw/mcp-tests.txt`: complete test output.
- `raw/service-probes.jsonl`: original configuration and database probe outcomes after the fixes.
- `raw/mcp-probes.json`: complete original installed-copy protocol probe after the fixes.
- `raw/reviewed-*` and `raw/reviewed-hashes.json`: exact reviewed source snapshots and hashes.
- `raw/commands.txt`: exact commands and probe source locations.

The independent probes were rerun unchanged from the first report. Their corrected results therefore directly verify the originally observed failures.
