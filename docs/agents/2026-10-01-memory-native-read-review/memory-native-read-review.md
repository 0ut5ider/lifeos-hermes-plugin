Date: 2026-10-01
Agent role: Independent native memory read and publication reviewer
Question: Do the wiki and Knowledge read changes preserve admission and native behavior, and what remains before safe write and ownership release?
Model: Parent assigned the Astra reviewer role. The exact runtime model identifier is not exposed to this agent.

Adrian, this review confirms two introduced defects in the wiki retained-source collector. Private markers in filenames bypass the body validator and appear in returned metadata. Directory enumeration also exceeds the stated source-count protection before refusal, and some paths have no effective enumeration bound. Neither finding permits an anonymous request to borrow owner authority. Both need focused corrections before claiming this collector is complete.

The Knowledge read relay has no additional confirmed material defect in this review. Its deliberate PUT refusal, graph-cache refusal, documentation exclusions, and unfinished publication and ownership work are accurately documented. The reported 514 memory tests and 12 neighboring tests are an implementation regression result, not a release-readiness result.

Review identity and evidence:

- Repository: `/home/outsider/Projects/Hermes_agent/LifeOS_plugin`.
- Reviewed HEAD: `d920dd1`; branch: `feature/lifeos-memory`.
- Requested implementation delta: `3eb2acf..b6fd86a`, including `830505d` and `b6fd86a`.
- Full relevant source copies, SHA-256 hashes, and the reviewed diff are in `raw/sources/`, `raw/source-manifest.json`, and `raw/reviewed.diff`.
- Reproductions are in `probe_boundaries.py`; exact JSON output is in `raw/boundary-probes.json`.
- Focused test command and output are in `run_review.py` and `raw/focused-tests.txt`. The independent gate passes all 107 tests in 111.379 seconds, without skips, failures, or errors. `raw/focused-tests.done` contains exit status 0.
- All fixtures use disposable synthetic data and localhost services. This review did not connect to `.211`, `.212`, or `.213`, invoke memory or journal tools, change product code or prepared sources, or commit or push.

1. P2, confirmed introduced defect: private source labels bypass admission.

Location: `lifeos_hook_bridge/memory_sources.py:101`, with returned metadata selected in `lifeos_hook_bridge/memory_wiki.py:46` and `lifeos_hook_bridge/memory_wiki.py:58`.

`read_markdown` passes only each source body to `validate_source_batch`. The native validator rejects malformed private openers and control characters in that body. The collector then returns the original path and derives slugs, groups, and fallback titles from its unchecked filename and directory names. The later history check includes the path, but that check detects retired claims, not private markup.

Reproduction:

1. Start the existing `MemoryWikiCorpusTests` disposable fixture.
2. Create `LIFEOS/DOCUMENTATION/<private>SyntheticPrivateFilename.md` with `Safe body without title` as its body.
3. Invoke the real `view(memory, OWNER, '/api/wiki')` path, including its real Bun renderer.
4. Observe status 200 and the marker in the tree label, slug, recent-change title, and filePath.

The raw result includes `"private_marker_returned": true`. The malformed opener is relevant because the existing private-source contract already excludes malformed body openers. The same boundary must cover text that the collector introduces from source metadata. This does not demonstrate a leak from a private-marked file body, which remains excluded, or an authentication bypass.

Fresh-install impact: this is latent until an admitted retained-source filename or directory label contains private markup or another prohibited character. The pinned public documentation fixture does not establish that such a label exists. It can occur after ordinary retained-source publication and does not require importing an old memory database.

Smallest safe correction: apply the same native private/control validation to every source-derived string that can reach the renderer, including the declared path and its labels, together with the body. Exclude the entire source on failure and keep its on-disk bytes unchanged. Do not strip only the emitted title, since filePath, group, and slug also carry the text. Add filename, directory/group, control-character, and ordinary-label controls through actual native rendering.

2. P2, confirmed introduced defect: enumeration precedes the count bound and some traversals bypass it.

Locations: `lifeos_hook_bridge/memory_wiki.py:27`, `lifeos_hook_bridge/memory_wiki.py:28`, and `lifeos_hook_bridge/memory_wiki.py:65`.

`sorted(parent.iterdir())` consumes the entire directory before `visited` is checked. Hidden entries are skipped before the counter increments. WORK enumerates and sorts every child, but counts only selected ISA files. `_files` also resets its traversal counter for each corpus root. The selected-source cap remains real; it is not a bound on discovery work or allocation.

The probe wraps `Path.iterdir` solely to count its actual filesystem yields. It does not replace directory contents or the source reader. It records:

| Disposable directory contents | Observed enumeration | Result |
| --- | ---: | --- |
| 6,000 visible non-Markdown files | 6,000 entries | Count refusal occurs after all entries are consumed |
| 3,000 hidden files | 3,000 entries | Returns an empty source list |
| 3,000 non-source WORK files | 3,000 entries | Wiki response is 200 |
| 1,100 non-source files in each of three selected roots | 3,300 entries | Wiki response is 200 |

Fresh-install impact: an empty installation is unaffected. A long-lived installation can accumulate enough retained or hidden entries to make each owner wiki request do unbounded work while holding the cooperating memory transaction. The probe establishes missing work/allocation bounds; it does not claim measured exhaustion, a measured service outage, or an unauthenticated denial of service.

Smallest safe correction: use a streaming directory iterator, such as `os.scandir`, with an explicit traversal budget that is checked before filtering and before sorting. Share that budget across the complete retained-corpus selection, including WORK, and separately retain the selected-source limit. Sort only the bounded collected entries. Python versions that materialize `Path.iterdir` internally require more than moving the existing counter above `sorted`. Add actual enumeration tests for hidden, non-Markdown, WORK, and several source roots. Keep the existing exact-path and symlink refusals.

The staged queue has a similar pre-existing eager-enumeration pattern at `memory_staging.py:50`. This review did not run a staged-queue reproduction and does not count that adjacent static observation as a third confirmed finding in these commits.

The read contracts otherwise examined:

| Contract | Assessment and evidence |
| --- | --- |
| Exact physical source paths | Retained reads reject parent traversal and source redirects. System sources must resolve to their exact installed paths. Canonical Knowledge notes must resolve to the configured physical USER/MEMORY path. Existing source and relay tests exercise redirected sources and foreign roots. No introduced path escape was confirmed. |
| Authenticated credential forwarding | The Python relay permits a fixed literal loopback endpoint, filters incoming session cookies, validates Bearer formatting, disables proxies and redirects, and forwards actual request credentials. Ambient agent metadata is not HTTP authority. The real HTTP fixtures exercise this. |
| Installation binding | Successful and missing-page source responses require the hash of the configured root, Hermes profile, and principal. The dashboard resolves the actual session to its current owner account binding. Wrong local installations fail closed. |
| Fail-closed behavior | Missing or invalid connectors, persistent managed mode, backend failure, unknown routes, cross-origin reads, unreviewed writes, and raw graph access refuse rather than returning native raw files. Standalone controls remain separate and intentional. |
| Current facts and retention | The governed canonical corpus reconstructs current registered entries; correction and forget exclude old entries from body, index, search, and graph output while retaining raw history. Retained unclassified sources use conservative age and claim checks. The new filename finding is an additional metadata admission issue. |
| Transaction consistency | Canonical selection, retained-source selection, retirement checks, and native rendering share one cooperating transaction. The native renderer receives declared content and does not reopen note bodies or the raw master index. This is consistency among cooperating operations; it is not evidence of an atomic snapshot against arbitrary outside filesystem writers. |
| Renderer isolation and native outcomes | The wiki worker is isolated per request; the Knowledge map belongs to one invocation. Empty later corpora cannot reuse prior content. Paired tests cover native body shapes, categories, grouping, quality metadata, and ordinary standalone behavior. Timestamp precision and equal-date ordering are intentionally normalized in the paired comparisons. |
| Transport bounds | The collector enforces per-source and aggregate content limits, and the relay checks response bytes and length. Those checks do not fix the confirmed discovery bound. Whole-operation latency under lock contention and all serialization expansion at maximum capacity are not established by these tests. No new transport disclosure was confirmed. |

The documented exclusions are known limits, not additional newly discovered defects:

- The pinned documentation corpus admits 58 of 60 pages. `DOCUMENTATION/Memory/CortexContract.md` and `DOCUMENTATION/Memory/MemorySystem.md` contain literal private-boundary examples. Whole-source exclusion follows the current native private policy. The evidence and implementation plan explicitly say this is not complete document parity.
- The unclassified-source retirement clock excludes an older document even when its text does not match the retired claim. Documentation and the installed system prompt currently inherit this rule. Existing tests explicitly reproduce the exclusion. This is conservative loss of availability, with a documented parity cost.
- Neither exclusion should be fixed with a blanket DOCUMENTATION or system-prompt path exemption, by changing timestamps, or by treating all fenced private markup as safe. Those approaches permit mutable or derived user text to bypass the existing boundary.
- A minimal safe future design can distinguish immutable released documentation by authenticated publication provenance and exact content identity. Mutable files and generated prompts still require their ordinary policy and reviewed publication. For literal private examples, release-source escaping or an exact reviewed public representation can preserve the example without admitting a live private delimiter. Continue to exclude the source unless that representation is verified. The present code implements none of these exemptions.

The remaining whole-note write and publication requirements are real unfinished work:

- The current Knowledge UI calls `/api/wiki/search`, `/api/wiki`, and `/api/wiki/knowledge/:category/:slug`. The source scan finds no PUT, POST, textarea, or save call. `raw/knowledge-ui-calls.txt` preserves the exact lines. No new editor is required merely to complete this existing UI.
- The Observability whole-file PUT remains a reachable public API in standalone mode. Managed mode deliberately returns 405. That is a safe temporary refusal and an incomplete write capability, not an introduced blind-write bug. External API callers can exist even though no in-repository caller was identified.
- Existing fact correction handles a referenced fact. Existing staged promotion handles new destinations, refuses an existing destination at `memory_staging.py:75`, and requires one complete fact body at `memory_staging.py:83`. Neither establishes multi-fact whole-note edit parity.

Before replacing the managed refusal, the edit contract needs all of the following:

1. Bind preview and apply to the same authenticated installation and owner, the exact note path and observed raw content identity, the complete set of active fact references and revisions, source metadata, and applicable project grants. Checking one selected reference is insufficient for a whole-note rewrite.
2. Recompute that identity under the cooperating publication lock. Refuse a stale preview after a fact correction, forget, unrelated append, metadata change, outside-file modification, or grant change. A source timestamp alone is not compare-and-swap.
3. Preserve references and provenance for unchanged facts. Retire replaced facts and register their replacements. Interpret removed facts under an explicit forget policy. Keep retained history outside the ordinary current projection so that the caller cannot accidentally re-admit old appended text through a whole-file save.
4. Validate new fact content and every published metadata field with the native rules. Do not silently broaden a project's grant when a source contains several facts or when a metadata edit changes the note's classification.
5. Publish the raw note representation, record revisions and status, derived indexes, and relevant publication state in one recoverable operation. The journal must cover every written, renamed, and deleted path. Build indexes from the admitted current corpus, not raw directory scans. Keep graph-cache and unmanaged harvest data unavailable until they have equivalent provenance.
6. Preserve request-id retry semantics. Prove crash recovery before and after commit and prove that recovery cannot roll back a later acknowledged write. Test stale previews, multi-fact notes, metadata-only edits, fact removal, append, retained history, duplicate identities, index-generation failure, and process death.
7. Exercise the real existing API or native caller after its integration. If the eventual reviewed write API has a different request shape, document the explicit managed refusal or replacement contract for the legacy PUT. Do not add a new UI editor as an assumed parity requirement.

Actual mount and sidecar publication remain separate release requirements. RenderSoul, the install and update Mount callers, skill name and summary metadata, sidecar core-file reads and writes, backup readers, derived consumers, restricted delivery, session lifecycle, and recoverable ownership setup still require coverage. The existing runtime prompt guard refusing an obsolete prompt does not prove that managed mount can generate a usable current prompt. The original inventory's exclusion of HERMES is explicitly documented and prevents a complete inventory claim.

Suggested next-work order, by dependencies and verification risk:

1. Correct and close the two local collector findings with focused failing tests, native controls, and the existing HTTP neighbors.
2. Finish the caller and source inventory, including HERMES, actual install/update calls, skills, sidecar endpoints, and derived consumers. Use it to make the remaining release scope concrete.
3. Define and test source provenance and the multi-fact reviewed publication contract using existing transaction machinery. Keep static-document classification distinct from mutable and generated content. These contracts unblock the remaining readers and writers.
4. Implement actual mount/RenderSoul and sidecar/API publication with current references, source admission, retry, recovery, and index invariants. Verify native outputs and real install/update behavior in disposable connector-enabled and connector-missing states.
5. Close derived readers, restricted delivery, children, compression, resumed and scheduled sessions, and adapter identity cases against those completed publication contracts.
6. Complete recoverable ownership setup and installation/update/backup/restore/rollback acceptance, then run the complete release gate and independent review as one release package. Keep ownership disabled until those gates pass.

No architectural rewrite is required by the two confirmed findings. The important review decisions are the source-publication identity model and whole-note fact mapping. The current tests do not establish either contract, do not prove the complete native UI or LAN cookie deployment, and do not justify enabling ownership. The review made no external-system change to undo.

Verification completion: the eight-module focused gate passed 107 tests in 111.379 seconds. The separate boundary probes still reproduce both findings, demonstrating missing test coverage despite the passing gate. The two distributed patch copies compare byte-for-byte equal. The reviewer created only this review artifact directory. While this report was being finalized, the primary agent began separate corrections in memory_sources.py, memory_wiki.py, and test_memory_wiki_corpus.py. Those concurrent edits are not evaluated in this report; its source copies preserve the reviewed version.
