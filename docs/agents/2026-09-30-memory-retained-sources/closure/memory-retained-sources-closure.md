# Retained native source closure review

Date: 2026-09-30
Role: Independent code reviewer
Question: Do the retained-source fixes close the three confirmed output leaks while preserving accepted native behavior and failing closed on invalid paths and connectors?
Model: GPT-6. The exact model variant is not exposed in this agent context.

## Conclusion

All three findings from the initial retained-source review are closed in the reviewed snapshot. Fourteen tests passed against the fresh distributed LifeOS source. Both original reproduction scripts ran unchanged and now show the expected safe outcomes. No additional material defect was found in the bounded paths reviewed.

This is closure of the retained-source readback unit. It is not approval for memory activation or a complete source, host, tool, or lifecycle audit.

## Findings closed

### 1. Forgotten WORK filename titles

memory_sources.read now derives a second label representation that removes the native WORK timestamp prefix and replaces hyphens with spaces. The retained filter includes this representation alongside source content and the original path.

The unchanged work-filename probe now receives ok=false and excluded=true from read_source. Actual LoadContext startup contains no forgotten title. The managed catch branch skips the rejected work item, so the slug cannot return through fallback rendering.

### 2. Advisory source redirects

The new check_source service action validates scope, logical source eligibility, and the expected physical source path. checkMemorySource invokes that action before advisory-readback calls readLatestByType. It checks both the default events path and an explicit eventsPath option.

The unchanged advisory-redirect probe still receives a direct path rejection, and the actual native advisory reader now returns null. The synthetic marker in USER/CONFIG no longer appears in a digest.

The source check does not return body content. Actual advisory findings remain individually filtered after parsing, before emission-state comparison and marker persistence.

### 3. Escaped JSON text

memory_sources.read now parses JSON and JSONL sources and includes decoded string values and keys in native validation and retained-claim filtering. Advisory readback filters the decoded finding type, key, and detail directly rather than JSON.stringify(finding).

The unchanged advisory-newline and progress-newline probes both record normalized_marker_emitted=false. Advisory output is null, and startup omits the rejected progress entry. The whitespace-normalized forgotten phrase remains excluded.

## Other inspected boundaries

The shared source-path function requires all native read categories and wildcard project access before reading the requested body. It rejects unsupported paths, missing or non-file sources, and physical redirects. The native read_source response must explicitly indicate success and excluded=false before readMemorySource returns its content.

Configured but malformed connector states still throw instead of becoming unmanaged reads. The unchanged dangling-connector wisdom probe returns null. The no-connector test continues to verify accepted standalone native wisdom behavior.

The JSON decoder does not silently accept malformed serialized sources. Its parsing errors reach the service failure response, and the native wrapper refuses that response. The prior permission, private-markup, ordinary forgotten-claim, and accepted-context tests all continue to pass.

No new public tool grant or owner activation control was introduced by the reviewed native service operations.

## Independent verification

Command environment:

- Python: /home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python
- LIFEOS_MEMORY_SOURCE: /home/outsider/.cache/lifeos-plugin-memory/source-gate-20260930-retained-sources-fixed/lifeos/LifeOS/install

Results:

| Verification | Result | Raw output |
|---|---|---|
| test_memory_sources.py | 14 passed, zero failures or skips, 7.763 seconds | raw/tests.txt |
| Original WORK-title probe | Governed read rejected; marker absent from startup | raw/probe_sources.py.txt |
| Original advisory-redirect probe | Direct path rejected; native digest null | raw/probe_sources.py.txt |
| Original dangling-connector probe | Wisdom output null | raw/probe_sources.py.txt |
| Original advisory decoded-newline probe | Marker not emitted; digest null | raw/probe_escaped_text.py.txt |
| Original progress decoded-newline probe | Marker not emitted in startup | raw/probe_escaped_text.py.txt |

The test suite also verifies current allowed relationship/work context, valid advisory output, private-markup exclusion, missing authority, restricted project scopes, direct secret-path rejection, and all five learning-reader paths.

Exact commands and the source environment are in raw/commands.txt. The original probe scripts were executed from their original locations and copied unchanged into this closure directory for reproducibility. Raw stdout is saved as .txt so it is not hidden by the repository's JSONL ignore rule.

## Snapshot and scope

Reviewed plugin files: memory_sources.py and the read_source/check_source/filter_source dispatch in memory_service.py. Reviewed native files: MemoryAccess.ts, learning-readback.ts, LoadContext.hook.ts, and advisory-readback.ts in the fresh distributed source. Both paired LifeOS memory patches were inspected.

Initial and ending hashes match for every reviewed source. Snapshots and hashes are retained in raw/. Top-level and bundled LifeOS memory patches are byte-identical.

No implementation edits or commits were made. Every operation used isolated synthetic fixtures. No SSH, live accounts, live Hermes imports or bootstrap, actual memory records, or journal tools were used.

## Remaining limits

The review verifies the supplied source paths and ordinary configured-source exclusions. It does not establish protection against a hostile process with the same operating-system identity replacing files between a separate source attestation and a native read. The existing local operating-system trust boundary remains relevant.

No full browser runtime, ownership activation, complete restricted-prompt audit, whole host/source/tool inventory, or lifecycle gate was run. Normalized exact claims and decoded whitespace variants were tested; universal semantic paraphrase exclusion is not claimed. Those limits do not reopen the three reproduced findings closed above.
