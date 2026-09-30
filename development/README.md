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

Small JSON Lines records contain schema version 1, UTC and monotonic time, process identity, local sequence, session and callback identity, dispatch and hook invocation identity, registration position, workspace scope, status, duration, and artifact references. Duplicate commands have separate registration identities. Inventory records identify registrations that were not exercised.

Full inputs and outputs are compressed artifacts. Identical redacted content shares an artifact. Prompts and conversation content remain intact. Known account credentials, credential fields, bearer strings, private keys, and encoded credentials in the remote hook protocol are removed before hashing. This filter cannot recognize every unknown credential in arbitrary prose or an unrelated encoding.

Each process appends to its own daily file. A child runner retains its parent's invocation identity and records a different process UUID. SQLite is rebuilt offline. Capture does not write to SQLite during a conversation.

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

The configuration pins inspected source hashes. A source mismatch generates `capture_gap` and runs the original source. After a Hermes or plugin update, inspect the affected observers and reinstall the capture configuration. Do not count a source mismatch as a successful hook observation.

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

Tests run real hook processes and compare traced results with native results. They cover large streams, detached parent exit, HTTP limits, duplicate registrations, malformed output, encoded credential redaction, storage failure, and partial JSON Lines tails. Live host enforcement, systemd, SSH, Docker, and Discord observations require the deployed environment and separate evidence.
