# Memory provider and sharing foundation

Date: 2026-09-30. Branch: `feature/lifeos-memory`. Ownership activation remains disabled.

The plugin now provides explicit Hermes memory tools backed by native LifeOS records. Required admission checks the actual model route before sending context. Hook and provider loaders share an admission binding. Separate native processes receive the admitted context and fixed profile configuration. Disabled, removed, or changed grants retain their refusal boundary; they cannot erase a private child context and then transmit it without a check.

Optional sharing uses MCP over a restricted SSH key with a server-selected client ID. The real localhost SSH fixture verifies reads, denied writes, private exclusion, command refusal, and active-client revocation. The preferences page shows native health, current facts, and client grants. Real dashboard authentication returns 401 for missing and invalid sessions, and 200 for an authenticated synthetic lookup.

Independent review caught an enrollment compensation race after grant publication. A key-file permission failure disabled whichever grant occupied the client ID at cleanup. Root checks alone did not prevent a same-root replacement from being disabled. The corrected compensation compares both the activated root and its complete grant under the configuration lock. Two unchanged failure probes now preserve the replacement. The original grant is disabled when its own publication fails.

The first full plugin run recorded 86 errors because its isolated environment lacked the declared `tree-sitter` dependency. The corrected environment includes all 56 core, development, and plugin requirements. The rerun passes 503 tests, with 77 skips for missing live fixtures. The bounded host tests pass 131 cases; dashboard interface tests pass seven. These results do not establish complete memory activation or full hook parity.

The native proposal workflow is still being integrated. Its enqueue function can divert a non-global proposal to an upgrade record, while the outer result describes the operation as queued. The managed receipt must inspect the actual native outcome and preserve that diversion. Reporting every successful native add as a saved or pending memory would be incorrect.

No live configuration, SSH keys, or services changed. The isolated SSH test used its own temporary daemon and terminated it. No data was copied from `.211` or `.213`.
