# Governed health diagnostics

Date: 2026-09-30

Native health checks need operational evidence even when the memory reader refuses invalid facts. The governed hot reader correctly refuses a file with dropped invalid entries. Reusing that reader in MemoryHealthCheck hid the native pending-silent-loss warning. A diagnostic-only operation now returns invalid-entry diagnostics, without returning valid fact entries, and filters retained text before delivery.

The first invalid-entry test used a plain malformed line. Native parsing treats that line as body text, so the test found zero dropped entries. A genuine `RULE: ` entry longer than 256 characters reproduces the warning. The corrected test preserves the dropped count and warning while excluding a retired claim. Another test with a retired state string passed because the health report omits details for healthy findings. That test does not prove text filtering by itself.

Independent review found three further defects. An optional report destination bypassed the normal log path checks and overwrote a synthetic configuration sentinel. Filtering an exactly retired ISO timestamp changed valid skipped-reviewer evidence into a false critical assessment. A report containing 500 overlength entries produced a 207,100-byte request, which exceeded the RPC input reader's 131,073-character limit. The CLI threw with empty standard output, while unmanaged native health returned a valid report.

The corrections confine managed optional reports to `LIFEOS/MEMORY/OBSERVABILITY/reports/*.json`, preserve validated structural clock fields as operational metadata, and permit diagnostic-filter requests up to 3 MiB. Other operations retain the smaller request limit. Timestamps inside free text remain filtered. Reports that exceed a transport limit must return an explicit unavailable result before publication. These are measured requirements, with failing regressions retained in `docs/verification/2026-09-30-memory-cortex-health/`.

Ownership remains disabled. These tests use synthetic isolated profiles and prepared public sources. They do not establish PULSE request authentication, corpus governance, atomic restore, or release readiness.

## Closure corrections

The first fresh closure passes 105 tests, but independent review finds two more defects. A field-name-only clock exemption leaks a retired ISO value inside an object-valued reviewer error. A primary probe also reproduces the same problem for enum names inside arbitrary error content. Exemptions now use declared native metadata locations. A genuine structured error test checks the collector, CLI output, and published log.

The clean-unavailable wrapper also changed an unmanaged invalid clock override from a native RangeError with exit 1 to JSON with exit 2. Managed refusal remains explicit, while unmanaged execution now retains its native exception. The corrected 56-case suite passes in 48.381 seconds. The first clock-comparison assertion compared filtered display fields and changing age measurements. It now fixes the comparison clock and checks native finding identifiers, severity, thresholds, and overall decisions. The failed runs remain in the evidence.

Final fresh-source verification passes 56 cases in 41.269 seconds. Independent final closure passes 56 in 38.914 seconds and all five archived programs. It reports no material defect in the bounded health unit. The primary reruns the additional metadata-path probe and the original reproductions before committing. This is not a full release result or permission to activate memory ownership.
