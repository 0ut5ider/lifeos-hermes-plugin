# Pulse core editor review

Date: 2026-10-14

Role: Independent code reviewer

Question: Does the governed Pulse core editor preserve current authority, reviewed bytes, physical profiles, recovery, and native functionality?

Model: gpt-6.1-sol, high reasoning effort

## Result

The reviewed implementation needs changes. I found two high-priority issues and three medium-priority issues. Every finding has a measured synthetic reproduction. I changed review artifacts only. I did not change implementation files, push, call memory tools, or access production data.

The primary agent started fixes after receiving these findings. This report records the implementation that produced the measurements. It does not certify those later fixes. A repeat review must verify the updated source, compiled browser, and recovery paths.

The local `main` reference is old. I used the actual merged PR24 baseline, `c24dd7298932694d3d63a8fa3ee10f38ebd5054a`, rather than treating unrelated historical changes as this feature. The reviewed branch head was `d68ee4b1` with additional uncommitted editor changes. `source-hashes.txt` and `reviewed-product.diff` record the initial reviewed state.

## Findings

### P1: Cached drafts can overwrite later owner edits with a new reference

Location: Native `HermesFiles.tsx`, `FileRow` draft-seeding effect and Save action. The source enters this repository through `patches/lifeos-memory-access.patch`.

The component seeds `draft` from cached query data when a row opens. The mount refetch then updates `data.reference`, but the existing draft remains unchanged. Save sends the old draft with that new reference. The backend correctly accepts the new reference, so its stale-reference protection cannot detect the stale draft.

Measured reproduction with the actual compiled dashboard and actual native and Hermes HTTP servers:

1. Open `PRINCIPAL_IDENTITY.md`, then close it. The query cache retains the original bytes.
2. Write a later synthetic owner edit to the fixture file.
3. Delay the actual file GET by two seconds. The instrumentation does not replace its response.
4. Reopen the row and let the GET complete.
5. The GET returns the later bytes and current reference. The textarea still contains the old bytes, and Save is enabled.
6. Click Save. The actual PUT sends old bytes and the new reference. The server returns HTTP 200.
7. The actual file now contains the old bytes. It has mode 0600, and the private backup contains the displaced later edit.

Evidence: `cached-draft-overwrite.json` and `browser-fixture/browser-source-observation.json`.

Required behavior: Keep the draft's base bytes and reviewed reference together. A newly opened row must wait for a current admitted read before it seeds the draft. A background read must not silently replace the reference of an existing draft. Test cached close/reopen and updates during an open draft.

### P1: Editor publication and recovery bypass program transaction locks

Locations: `memory_preferences.py`, `edit_core_file`; `memory_access.py`, `_transaction`; `memory_core_file.py`, `edit`; `MemoryTransaction.recover`.

The editor uses the memory publication lock. Program update workers use the installation lock and exclusive program lock. The editor does not initially join those locks. The original and repeated real HTTP probes save a source successfully while another operation holds the actual installation lock.

Recovery needs the same protection. Locking the edit entry point alone does not cover recovery through other memory routes. I interrupted a real config save after publication with child exit 86. I then held the actual installation lock and exclusive program lock and invoked the authenticated memory search route. It returned `status: ok` and restored `config.yaml` from interrupted bytes to original bytes while both program transaction locks remained held.

Evidence: `backend-probes-before.json`, `backend-probes.json`, `recovery-lock-probe.json`, `probe_editor.py`, and `probe_recovery_lock.py`.

The first recovery probe lacked the fixture's normal `.hermes` alias. It returned unavailable and did not recover. I retained that result in `recovery-lock-missing-alias.json`, added the legitimate synthetic profile alias, and repeated the probe. The final result above uses the alias.

Required behavior: Serialize editor publication with installation and program transactions. Serialize pending core edit recovery from every route that can trigger it. Preserve the existing lock order: installation lock, program lock, memory lock. A recovery guard inside the memory lock must refuse conflicting leases without waiting, because an update worker can hold the program lock while waiting for memory.

### P2: A current read denial leaves cached owner text visible on reopen

Location: Native `HermesFiles.tsx`, file query and draft-seeding effect.

The component initially does not inspect the query error state. React Query retains previous successful data after a refetch error. Reopening a cached row seeds a textarea from that data even when current owner admission fails.

Measured reproduction: After the cached row test, I close the row, remove the synthetic dashboard account's owner binding, and reopen the row. Two actual file GET requests return HTTP 403. The textarea continues to display the previous owner text.

Evidence: `revoked-cached-draft.json`.

The server refuses current access correctly. This finding concerns the browser's current visible surface, not a server authority bypass or an ability to erase information already received by an authorized owner.

Required behavior: Clear or withhold the visible draft and its review state after a current admission error. Do not seed cached personal content before a fresh admitted read. Cover current account revocation and a cached row reopen in the compiled browser.

### P2: Native core saves fail above the unrelated 128 KiB RPC limit

Locations: `memory_rpc.py`, input admission around `algorithm_edit`; native `PULSE/modules/hermes.ts`, managed async response returns.

The editor declares a native content limit of 1,000,000 UTF-8 bytes. Its native request body limit is 3 MiB. The RPC dispatcher exempts only `algorithm_edit` from the older 131,072-byte input limit. It therefore refuses a valid core edit before the authenticated relay can process it.

The handler returns `memoryHTTPResponseAsync(...)` without awaiting the promise inside its try block. The invalid RPC result rejects later and escapes the intended private error response.

Measured result: An actual native core PUT with 161,037 content bytes returns HTTP 500 and a Bun HTML error page. It does not save the file. The HTML includes internal local paths, and the native listener writes an uncaught error. The content is below the declared 1,000,000-byte limit.

Evidence: `backend-probes.json`, `native-limit-first.stderr`, and `native-limit-response.stderr`. The first probe attempted JSON decoding of the HTML response and failed. I retained that failure, then repeated with explicit content-type and body capture and an assertion for the expected native diagnostic.

Required behavior: Admit the bounded `core_file_edit` RPC request under the existing 3 MiB transport cap, while retaining the editor's UTF-8 content cap. Await managed async responses inside the handler's try block. Test the actual native HTTP path above 128 KiB and near the content cap. Test private JSON failures rather than accepting a framework error page.

### P2: One malformed YAML file disables the complete core manifest

Locations: `memory_core_file.py`, `_admit_content` YAML decoding and `_snapshot` withheld-source handling.

The overview permits metadata-only rows for `CoreSourceWithheld`. Malformed YAML raises the broader `MemoryUnavailable` instead. One malformed `config.yaml` therefore fails the complete manifest, including unrelated public program files and other safe owner files.

Measured result: A fixture `config.yaml` containing `model: [synthetic-incomplete` returns HTTP 503 for the individual read and HTTP 503 for `/api/hermes`. Other safe files exist and remain independently readable.

Evidence: `backend-probes-before.json` and `backend-probes.json`.

Required behavior: Preserve safe rows in the overview when one structured source cannot pass complete decoded-content admission. Keep the malformed source withheld and explain the required repair path. This recommendation does not authorize returning unreviewed raw structured content or bypassing privacy admission.

## Verification and limits

I independently ran all 22 existing editor tests with the qualified Bun 1.4.3 and frozen Python environment. They pass in 35.480 seconds. Logs are `focused-tests.stdout` and `focused-tests.stderr`. These tests cover real native HTTP and authenticated Hermes HTTP, normal saves, references, private backups, credential containment, revoked owner requests, physical source redirects, and process interruption. Their success does not cover the findings above.

The browser probes use the actual compiled Next dashboard with actual synthetic backend responses. The only network instrumentation delays a real GET and records its real request and response. It does not replace responses. Other dashboard routes are absent from the narrow fixture and produce unrelated 404 diagnostics. I did not treat those diagnostics as editor defects.

The browser also displays a native Mount diagnostic failure as `stale`, because exit code 1 is the existing drift contract. The synthetic fixture lacks complete installed prompt inputs. This result does not prove a successful installed remount. I did not report it as a new defect. An installed candidate test must verify a successful real remount with complete inputs.

The primary agent separately reported obsolete compiled chunks in the combined historical output patch and is repairing that patch. I did not independently certify the corrected fresh replay. That check remains part of release qualification.

I stopped my synthetic browser fixture, verified `process.done` is 0, and closed my browser tabs. I did not change either live server or the pending automatic morning observation.
