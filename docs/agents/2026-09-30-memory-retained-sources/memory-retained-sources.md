# Retained native source readback review

Date: 2026-09-30
Role: Independent code reviewer
Question: Do the bounded retained-source readers enforce permission and path checks, retained claim exclusion, and safe native fallback before emitting startup context?
Model: GPT-6. The exact model variant is not exposed in this agent context.

## Conclusion

Three material findings are confirmed with real native fixtures. All 11 supplied source tests pass, but startup and advisory output can still restore excluded text in the cases below. This unit is not closed.

The primary agent received each finding with reproduction paths. This report records the reviewed snapshot, not any later fixes. No implementation edits or commits were made. All source records and configuration were temporary synthetic fixtures. No live services, accounts, SSH, runtime bootstrap, actual memory records, or journal tools were accessed.

## Finding 1: WORK filename fallback restores a forgotten claim

Severity: High for retained claim exclusion.

memory_sources.read filters content plus the raw relative pathname at line 35. The native startup reader later derives a display title from the WORK directory slug by removing hyphens. A normal native directory prefix ends with an underscore, and _claim_words treats underscore as part of a word. The prefix therefore joins the first claim word during the retained-token comparison.

The probe saved and forgot Synthetic forgotten work title marker. It created a current WORK directory named with the standard YYYYMMDD-HHMMSS_ prefix followed by that hyphenated title, containing an ISA.md with only phase: build. The direct governed read returned ok=true. Actual LoadContext startup then emitted the complete forgotten marker as an active-work title.

This bypass does not require a failed read. The added early continue correctly protects rejected ISA/metadata, but the read succeeds because its source representation does not match the title produced later.

Evidence: raw/probe_sources.py case work-filename, with full native output in raw/probes.jsonl.

Recommended correction: apply the retained filter to the actual derived title before emitting it, including the filename fallback and any session-name override. Keep source permission/path checks as a separate pre-read requirement.

## Finding 2: Advisory readback bypasses governed physical-path checks

Severity: High for source boundary enforcement.

advisory-readback.ts calls readLatestByType directly before it invokes filterMemorySource on individual findings. The content filter has no source path, so the advisory path does not use memory_sources.read's redirect and physical-location checks.

The probe placed a synthetic event record in USER/CONFIG/synthetic-secret.jsonl and redirected MEMORY/STATE/events.jsonl to it with a symlink. A direct read_source request correctly returned excluded=true because the physical destination changed. The actual native loadAdvisoryDigest call nevertheless emitted SYNTHETIC_CONFIG_ONLY_ADVISORY_MARKER from that config file.

No actual secret was used. The synthetic record demonstrates that a path explicitly rejected by the new governed reader still feeds model-visible native output through the separately filtered advisory path. It also shows that advisory file reading happens before the new policy service has admitted that source.

Evidence: raw/probe_sources.py case advisory-redirect. raw/probes.jsonl contains the direct rejection and the contrasting native digest.

Recommended correction: authorize and validate the event source path before its body is read. Preserve per-finding filtering after event parsing so one excluded finding does not unnecessarily suppress unrelated accepted findings. Apply the same requirement to explicit eventsPath options in managed mode.

## Finding 3: JSON escaping hides exact claims from filtering before decoded output

Severity: High for retained claim exclusion.

Advisory readback passes JSON.stringify(finding) to the content filter, then renders the original decoded finding. Progress readback passes the raw JSON file through read_source, then parses and emits its decoded fields. These filtered representations differ from the displayed text.

The probe saved and forgot Synthetic forgotten escaped marker. It then provided a current advisory detail with a real newline between forgotten and escaped. JSON serialization represents that newline as backslash+n, so _claim_words sees a different token sequence. Native advisory rendering collapses whitespace and emits the exact original forgotten phrase.

A second real fixture placed the same decoded newline variant in progress.project. Actual startup emitted that title across two lines, restoring the same normalized retained claim.

This is a whitespace-normalized exact quote, not a semantic paraphrase. The previously promised normalized claim defense should cover it.

Evidence: raw/probe_escaped_text.py and raw/escaped-probes.jsonl. Both outputs record normalized_marker_emitted=true; the advisory output contains the original phrase exactly.

Recommended correction: filter the decoded fields or final human-facing strings that will be emitted. Avoid using serialized container syntax as the only claim-comparison surface. Continue validating the original source and filtering timestamps before publication.

## Verified passing behavior

All 11 tests in test_memory_sources.py passed in 4.786 seconds against the requested prepared distributed source:

- Native unmanaged wisdom behavior remains available when no connector exists.
- Allowed relationship and progress context appears in startup.
- Straightforward forgotten relationship, work, wisdom, learning, synthesis, cache, and advisory text is excluded.
- Native private markup and missing authority suppress wisdom and advisory output.
- Current policy changes revoke source reading.
- Restricted project scopes cannot read unclassified source history.
- Direct read_source rejects config paths and in-user symlink redirects.
- All five learning-readback file paths use governed reads.

An extra dangling-connector probe confirms actual loadWisdomFrames returns null without falling back to the unmanaged file read. The malformed connector is never treated as absent.

The inspected read_source implementation checks scope before loading the requested source body, restricts logical prefixes and exact files, verifies the expected physical destination, validates content, and applies timestamp/claim filtering. These checks work in the direct path tested. Finding 2 concerns the advisory route that does not call this reader.

The patch filters advisory findings before emission-state comparison and persistence. This ordering is appropriate, but findings must first pass the correct source and decoded-text checks.

## Scope and evidence

Reviewed plugin files: memory_sources.py and the native read_source/filter_source dispatch in memory_service.py. Reviewed native changes: MemoryAccess.ts, learning-readback.ts, LoadContext.hook.ts, and advisory-readback.ts through the paired LifeOS patch and actual prepared source. events.ts was read to verify how advisory source bytes are obtained.

Native source: /home/outsider/.cache/lifeos-plugin-memory/source-gate-20260930-retained-sources/lifeos/LifeOS/install.

Python environment: /home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python.

Exact commands are in raw/commands.txt. Complete suite output is raw/tests.txt. The two probe scripts and their JSONL results are retained. Source snapshots, initial and ending hashes, drift results, and patch equality verification are in raw/. Top-level and bundled LifeOS patches are byte-identical at review completion.

Raw native outputs are preserved exactly, including punctuation produced by upstream code. Authored report prose contains no em dash.

## Limits and next review

Full restricted prompting, complete host/source/tool inventory, activation, browser behavior, and lifecycle were explicitly outside scope. No broad release gate was run. Fix and reproduce the three findings before treating this retained-source unit as closed. A closure review should rerun the unchanged probes alongside the bounded test suite.
