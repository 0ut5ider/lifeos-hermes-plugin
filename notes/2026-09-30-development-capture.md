# Development capture: loss boundaries and behavior checks

Date: 2026-09-30

The native detached runner sends stderr to `/dev/null` and reads 65,537 characters of stdout for context processing. A recorder outside that subprocess boundary cannot recover discarded output. The development observer captures both streams before that conversion. A real parent-exit test retains 1,100,000 characters of stdout and 1,100,000 bytes of stderr. The native context limit still rejects that oversized response.

The independent implementation review found an instrumentation bug with `{"hookSpecificOutput":"not-an-object"}`. The native bridge returns no directive. The initial recorder raised `AttributeError` while classifying the response. Type checks and an optional observation boundary now preserve the native result. A real traced/untraced test covers the case. Logging must not become a second policy engine.

Plaintext credential filtering missed remote wire data. The transport encodes command text, environment assignments, stdout, and stderr in base64. The recorder now decodes the known protocol, redacts credentials, and encodes it again for storage. The canary test includes a truncated frame that contains stdout but lacks stderr. These records contain credential-redacted wire data, not an exact unredacted network copy.

The `.212` launcher uses an account-owned base Python interpreter and adds its dependency environment with `site.addsitedir`. Detached runners use the base `sys.executable`. A startup file installed only in the dependency environment would miss those children. The development installation targets the base interpreter's site directory. Source fingerprints limit the in-memory observers to the inspected Hermes and plugin files.

No Hermes, LifeOS, or public plugin runtime source file changes are required for this recorder. Raw evidence belongs in the account's private state directory. Completion counts establish execution observations, not semantic parity.
