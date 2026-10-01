# Independent primary validation

Date: 2026-10-01

Role: Primary agent

Question: Do the fresh review findings reproduce with the real native source and dashboard authentication fixtures?

Model: GPT-6.1-Sol, high reasoning effort

## Reviewed state

The implementation remains at `e313d32`. The primary makes no implementation or live configuration change during this review. The primary compares all 38 source hashes in the reviewer manifests and checks their current disk bytes. None changes during the review.

The runs use the complete Python environment at `/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python`.
They use the owned public source fixture at `/home/outsider/.cache/lifeos-plugin-memory/source-gate-20261001-cortex-final/`.
Each test creates synthetic user data. The runs do not import a live server checkout.

## Reproduced findings

1. A revoked dashboard account receives HTTP 403 from the PULSE owner route. The older review route still returns its principal fact. The sharing route still accepts a configuration change. The adoption preview route still succeeds. The anonymous control also succeeds when the host authentication gate is disabled. A distinct authenticated BasicAuth account without a memory binding receives the same unauthorized fact. A revoked owner can forget that fact through the older review route. Its response reports a committed operation, and native recall then returns no fact.
2. An explicit governed addition to a hot file with unadopted native content returns a committed receipt. The next governed hot read raises `MemoryConflict`. The new fact appears in search, but the full hot snapshot remains inconsistent with the registry.
3. A forgotten diagnostic key causes the native diagnostic shape check to reject the filtered report. The managed control without the forgotten key publishes its critical report. The standalone control also publishes its critical report. The affected managed run returns unavailable JSON and publishes no health log. Exit code 2 occurs in all three controls, so the output and publication establish the difference. An additional exact contract probe confirms that Python returns `ok: true` with the filtered key omitted. The real native adapter rejects that response with `The native diagnostic service returned an invalid result`.
4. A project-only reader receives a rejected forget receipt for a principal reference. Python audit events show that the server opens the principal file before it rejects the request. The receipt does not contain fact content. This proves incorrect authorization order, not response-body disclosure.

The unchanged reviewer probes and the primary results are in this directory. The first copied controls file was incomplete and failed with `SyntaxError`. Its source and log remain available. The finalized controls file runs successfully and reproduces the findings.

## Regression result

The primary independently runs the same 12 test modules as the reviewer:

```text
test_memory_native test_memory_curation test_memory_service
test_memory_proposals test_memory_diagnostics test_memory_cortex_health
test_memory_pulse test_memory_pulse_auth test_memory_runtime
test_memory_sharing test_memory_context test_memory_adoption
```

The primary run passes all 188 tests in 119.628 seconds. The reviewer run passes all 188 tests in 122.313 seconds. Neither run skips a test.

The passing existing tests do not cover the four reproduced cases. This result does not establish activation readiness or close the known native reader, writer, installation, lifecycle, or release requirements.

## Limits

The primary verifies the synthetic reproduction programs and the selected regression suite. This review does not test browser delivery, live server memory ownership, actual shared client enrollment, or every native LifeOS memory consumer. Ownership remains disabled. The review does not change `.211`, `.212`, or `.213`.
