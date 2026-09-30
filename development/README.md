# Development hook capture

This recorder collects private evidence for development tests. The public plugin installer copies `lifeos_hook_bridge/`. It does not install this directory, its Python startup file, or captured data.

The recorder observes Hermes callbacks, bridge translation, selected and skipped registrations, native command and HTTP results, remote transport, detached runners, host tool boundaries, model context construction, and Discord admission and delivery. It records the registered Hermes event separately from the bridge method. A returned directive is not proof of host enforcement.

## Evidence layout

```text
private-capture-root/
  runs/<run-id>/events/<UTC-date>/<process-uuid>.jsonl
  artifacts/sha256/<prefix>/<digest>.json.gz
  analysis/index.sqlite
```

Small JSON Lines records contain schema version 1, UTC and monotonic time, process identity, local sequence, session and callback identity, dispatch and hook invocation identity, registration position, workspace scope, status, duration, and artifact references. Observed function calls also carry span and parent span IDs. Discord records retain message IDs across admission and reply delivery. Duplicate commands have separate registration identities. Inventory records identify registrations that were not exercised.

Full inputs and outputs are compressed artifacts. Identical redacted content shares an artifact. Ordinary prompts and conversation content remain intact. Known account credentials, credential fields, bearer strings, private keys, and encoded credentials in the remote hook protocol are removed before hashing. Credential fields remain filtered when JSON appears inside stdin, stdout, or a partial text fragment. Each process also learns declared credential values from structured artifacts, so later output that repeats a value can be filtered. This filter cannot recognize every unknown credential in arbitrary prose or an unrelated encoding.

Each process appends to its own daily file. A child runner retains its parent's invocation identity and records a different process UUID. SQLite is rebuilt offline. Capture does not write to SQLite during a conversation.

The development observer forwards its own trace context through `ThreadPoolExecutor` jobs. It does not forward unrelated application context variables. This preserves correlation when Hermes executes a hook on a worker thread.

## Install on a development account

Run the installer with the interpreter that launches Hermes and its detached hooks. Hermes can use a base interpreter and add a separate dependency environment. Check `sys.executable` and the base interpreter's `site.getsitepackages()` first. The source and configuration must be owned by the development account.

1. Copy `development/` outside the installed plugin directory.
2. Use that interpreter to import `hook_capture.setup` from the copied directory.
3. Run `install` with the inspected plugin and Hermes paths.
4. Restart the gateway and dashboard after active turns finish.
5. Verify source-loaded records and a real hook invocation.

```bash
PYTHONPATH=/path/to/development python -m hook_capture.setup install \
  --plugin-root /path/to/installed/lifeos-hook-bridge \
  --host-root /path/to/hermes-agent
```

The installer writes `~/.config/lifeos-development-capture/config.json` with mode 0600. It places `lifeos_development_capture.pth` in the interpreter's site directory. The startup file also enables systemd-launched children that do not inherit `PYTHONPATH`. The capture root defaults to `~/.local/state/lifeos-development-capture` with mode 0700.

The configuration pins inspected source hashes. Startup also compares the recorder's actual source files with its configured manifest. A recorder mismatch records `capture_gap` and leaves native execution active without installing observers. A pinned Hermes or plugin source mismatch leaves that source unmodified and records `capture_gap`. After an update, inspect the affected observers and reinstall the capture configuration. Do not count a source mismatch as a successful hook observation.

## Review captured behavior

```bash
PYTHONPATH=/path/to/development python -m hook_capture.analysis /private/capture/root
PYTHONPATH=/path/to/development python -m hook_capture.analysis /private/capture/root \
  --session SESSION_ID --limit 200
PYTHONPATH=/path/to/development python -m hook_capture.analysis /private/capture/root \
  --status timeout --from-utc 2026-09-30T00:00:00+00:00
PYTHONPATH=/path/to/development python -m hook_capture.analysis /private/capture/root \
  --invocation INVOCATION_ID
PYTHONPATH=/path/to/development python -m hook_capture.analysis /private/capture/root \
  --artifact artifacts/sha256/ab/REST.json.gz
```

Start with the summary. Inspect capture gaps and integrity errors before judging hook outcomes. Separate expected exit-code-2 interventions, parse failures, transport failures, native timeouts, and incomplete invocations. Follow one invocation through input, result, returned directive, host action, context construction, and delivery where applicable. A hook's intended file or memory side effect needs its own observed evidence.

`known_lost_events` sums the highest reported recorder failure count per run and process. `capture_failure_processes` identifies how many processes reported loss. A process that loses every event, or exits before its next successful write, cannot report its final failure count this way. A zero count is the absence of reported loss, not proof of complete capture. Malformed records and compressed artifact errors are reported while the index continues through valid evidence.

Hook tables separate `terminal_outcomes`, `successful_executions`, `interventions`, and `failures`. Duration statistics include terminal outcomes. Registration identity includes its observed settings origin and execution scope. The inventory count covers registration versions seen across captured runs, rather than only the currently installed configuration. Use the inventory records and source manifest when comparing versions.

HTTP capture retains only the bytes Hermes actually reads. `unknown_at_limit` means the read reached the native limit; the recorder does not drain the response. Unknown Python objects are represented by type names rather than arbitrary object representations. Attachment metadata is recorded, but the recorder does not download an attachment solely for tracing.

No automatic deletion or scheduled review is configured. Monitor the capture directory's size. Generate summaries for a day or session, then expand only the relevant artifacts. Keep these files private and outside Git.

## Disable or remove

```bash
PYTHONPATH=/path/to/development python -m hook_capture.setup disable
PYTHONPATH=/path/to/development python -m hook_capture.setup remove
```

`disable` prevents activation in subsequent processes. `remove` also removes the startup file. Restart the gateway and dashboard to stop an already active recorder. Raw evidence remains for review. The installer retains an existing configuration as `config.json.before-install` on its first replacement. Restore that file if it is needed.

## Tests

```bash
python3 -m unittest discover -s development/tests -v
```

The 28 tests include real hook processes and traced versus native comparisons. They cover large streams, detached parent exit, HTTP limits, duplicate registrations, distinct settings origins, malformed output and evidence, credential redaction in JSON and encoded transport, URL and header credentials, echoed credentials, storage failure, reported capture loss, source drift, turn identity, partial JSON Lines tails, and thread context propagation.

The initial 11-test suite passed locally and on `.212` on 2026-09-30. The corrected 28-test suite passes locally. It also validates decoded transport declarations, malformed inventories, and integer bounds before index insertion, Bearer, Basic authorization, and cookie-value echoes, and per-reference checksum checks. Separate live probes verified an actual systemd detached runner, SSH and Docker detached success and failure, a Hermes terminal tool turn, and Discord admission and reply delivery. See the [deployment record](../notes/2026-09-30-development-capture-212.md). These observations do not establish all permission cases or semantic parity for every registration. Comparative latency has not been measured.

The [independent review and fixes](../notes/2026-09-30-logging-review-fixes.md) distinguish the initial 11-test deployment from later review corrections. The record identifies which corrected revision has reached `.212`.

`development/probes/remote_capture.py` runs against disposable SSH and Docker fixtures supplied through environment variables. It exercises the remote execution boundary directly. It does not establish trusted project selection or full remote tool behavior. The operator must prepare and remove its keys, container, account access, and workspace.
