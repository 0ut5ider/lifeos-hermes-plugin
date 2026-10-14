# Pulse core editor focused second review

Date: 2026-10-14

Role: Independent code reviewer

Question: Do the current fixes resolve all five measured findings from the first core editor review?

Model: gpt-6.1-sol, high reasoning effort

## Result

The five baseline findings are resolved in the reviewed current implementation. I found no unresolved blocking issue in this focused review. This result covers the editor changes and synthetic acceptance paths below. It does not replace installed release qualification or prove a successful remount of a complete live installation.

I independently ran all 27 final editor tests. They pass in 45.434 seconds. I also ran strict TypeScript checking with the qualified Bun executable. It exits 0 with no standard output or error output. I used the rebuilt compiled dashboard for the actual browser checks.

The implementation changed during the review. I retained the first 26-test run, which had two failures: generated and registered files returned 503 instead of the expected 409 after the exception classification change. The primary agent corrected those paths. The final 27-test run includes the correction and the added program-swap read test. `final-source-hashes.txt` identifies the reviewed final files.

## Verified findings

### 1. Cached drafts and references remain paired

I repeated the first review's actual compiled browser reproduction against the rebuilt UI:

1. Open the synthetic identity row and let its initial GET complete.
2. Close the row and change the synthetic owner file on disk.
3. Delay the actual next GET by two seconds without replacing its response.
4. Reopen the row.

The UI displays no textarea while the fresh GET is pending. After the GET succeeds, the textarea contains the later owner bytes and Save remains disabled. The old cached bytes no longer seed the new draft.

I also tested a draft that remains open across a later refetch. I type a synthetic draft, change the owner file, and dispatch real browser offline and online events. The resulting actual GET returns the new bytes and reference. Save still uses the original reference paired with the draft. The actual PUT returns 409 and the file keeps the later bytes. No backup appears because no publication occurs.

Evidence: `browser-fixes.json` and `browser-fixture/browser-source-observation.json`.

### 2. Installation, program publication, and recovery serialize

The editor now takes the installation lock before the exclusive program lock. Nested core recovery borrows only the active physical-profile lease issued to the current thread. The existing lease checks reject another profile, thread, or expired lease.

I independently tested actual HTTP saves while holding the real installation lock and while holding the real exclusive program lock. Both return 503 and leave the file unchanged. A core read while the exclusive program lock is held returns 503 without source content. An installation lock alone can still permit a stable read when no exclusive program swap is active.

I repeated the unrelated-route recovery test. A real child process exits 86 after publishing an interrupted config edit. With both program transaction locks held, the authenticated memory search returns `status: unavailable`, and the interrupted bytes remain unchanged. After I release the locks, the same memory route returns `status: ok` and restores the original bytes.

The recovery guard applies when a core journal is recovered through any memory route. It takes locks without waiting inside the memory lock, which avoids reversing the update worker's waiting order. The read lease first allows pending recovery before it takes its shared program lock. This avoids asking the same read to upgrade its own shared lock during recovery.

Evidence: `backend-fixes.json`, `probe_fixes.py`, and the passing process recovery and lock tests in `focused-tests.stderr`.

### 3. Current owner denial withholds cached text

I close a cached identity row, remove the synthetic account's owner binding, and reopen the row. The actual GET requests return 403. The UI displays no textarea while admission is pending or after it fails. It shows `API error: 403 Forbidden` instead of cached owner text.

Evidence: `browser-fixes.json`, `revocationPending` and `revocationComplete`.

### 4. Native edits preserve the declared byte limit

The RPC dispatcher now admits the bounded `core_file_edit` view under the existing 3 MiB transport cap. The editor retains its separate 1,000,000-byte UTF-8 content limit. Native managed responses are awaited inside the error handler.

Independent actual native HTTP results:

| Content | UTF-8 bytes | Result | File result |
| --- | ---: | --- | --- |
| ASCII prose | 989,027 | HTTP 200, JSON | Exact requested bytes |
| Unicode prose | 980,025 | HTTP 200, JSON | Exact requested bytes |
| Unicode over the byte cap | 1,000,002 | HTTP 400, JSON | Original file unchanged |

The native listener produces no uncaught error output. The expanded editor suite also verifies a native save above the old 128 KiB RPC limit.

The first additional Unicode probe accidentally exceeded the byte cap because I counted characters instead of UTF-8 bytes. It correctly returned 400. I retained that measurement in `backend-fixes-first.json` and repeated with the 980,025-byte input above.

Evidence: `backend-fixes.json`, `backend-fixes.stderr`, and `probe_fixes.py`.

### 5. Invalid YAML no longer hides other safe files

With malformed synthetic `config.yaml`, the actual overview returns HTTP 200 and all 24 registry rows. The config row is not readable or editable. The safe identity row remains readable. The individual malformed config read still returns 503.

This preserves decoded-content privacy admission. It does not return unreviewed raw YAML. A malformed config remains a repair outside this editor until its complete content passes admission.

Evidence: `backend-fixes.json` and `test_invalid_configuration_withholds_only_its_own_row` in `focused-tests.stderr`.

## Artifacts and limits

- `focused-tests.stderr`: final 27-test pass.
- `focused-tests-first26.stderr`: retained intermediate two-failure run.
- `backend-fixes.json` and `probe_fixes.py`: independently measured native limits, locks, recovery, and malformed config behavior.
- `browser-fixes.json`: actual rebuilt browser requests, responses, draft state, and admission state.
- `compiled-file-map.json`: hashes of the compiled files used by the browser fixture.
- `dashboard-types.stdout` and `dashboard-types.stderr`: clean independent strict type check.
- `verification-status.json`: exact completed check outcomes.
- `final-source-hashes.txt` and `reviewed-product.diff`: reviewed implementation identity.

I did not edit implementation files, call memory tools, access production data, push, or modify either live server. The narrow browser fixture does not implement unrelated dashboard endpoints, so those requests can produce 404 diagnostics. Those diagnostics do not represent native core editor results.

The fixture's native Mount check lacks complete installed prompt inputs. This review does not certify a successful installed remount, the final package's source replay, the complete qualification suite, or release deployment. Those remain release acceptance work.

I closed my browser tab and stopped my synthetic fixture. Its recorded `process.done` is 0.
