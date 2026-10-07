# Enabled private GitHub reminder acceptance

Date: 2026-10-07. Target: the isolated acceptance account on `192.168.8.252`. Adrian authorizes creation of a separate private repository for this test. The authenticated account is `0ut5ider`; the supplied `0ur5ider` spelling returns HTTP 404.

The [repository receipt](repository.json) verifies that [0ut5ider/lifeos-reminder-test](https://github.com/0ut5ider/lifeos-reminder-test) is private and supports issues. The control copies the actual installed [registration](registration.json), including asynchronous execution. It uses the actual bridge and native runner. The observer records actual process handles and waits for their exits; it does not substitute command results. [Source hashes](source-identity.json) bind the unchanged native router, work-config loader, bridge, and control script.

[The result](result.json) records 17 native runner processes with exit code 0 and five actual GitHub issues. [Created issue records](issues-created.json) retain the original prompt, type, labels, and parsed due date. [Delivery state](delivery-state.json) retains one acknowledged hash per tested session.

| Control | Verified result |
| --- | --- |
| Explicit reminder | One issue contains the prompt, reminder labels, Cerebo identity, and tomorrow's UTC date. A repeated submission creates no duplicate. |
| Research | One issue contains the prompt and research labels. A repeated submission creates no duplicate. |
| Queued work | One issue contains the prompt and queue labels. A repeated submission creates no duplicate. |
| Concurrent delivery | Eight bridge instances submit the same reminder in one session. One issue and one delivery marker result. |
| Authentication refusal and retry | The invalid-credential probe returns HTTP 401. The corresponding native attempt creates no issue and publishes no marker. Valid authentication then creates one issue. A further repeat creates no duplicate. |

The [launcher](reminder-live-launch.py) passes credentials through standard input. The test account uses an isolated home and GitHub configuration directory. Native asynchronous payloads are private and disappear when the runner consumes them. The [credential scan](credential-scan.json) finds no private credential in the exported artifacts. No GitHub login file is created.

## Investigation and readback

The [first fixture failure](reminder-live-first-failure.txt) inherits `/root` as its working directory. The test account cannot enter that directory. The corrected control changes into its own fixture home before dispatch.

The [second fixture failure](reminder-live-readback-failure.txt) reads an empty issue list immediately after acknowledged creation. Its [native state](readback-failure-delivery-state.json) records delivery. A later actual repository read finds the created issue. The [direct native diagnostic](reminder-native-diagnostic.txt) also creates an issue successfully. The [readback response](reminder-readback-headers.txt) declares `Cache-Control: private, max-age=60, s-maxage=60`.

The final control requests uncached list readback with a unique query value and waits up to 30 seconds for visibility. It does not repeat issue creation while it waits. It verifies issue closure from each actual PATCH response. This separates command acknowledgement from cached list visibility.

## Cleanup and limits

[Closed issue records](issues-closed.json) verify closure of all five acceptance issues. [Repository cleanup](repository-cleanup.json) verifies that all seven issues, including two investigation probes, are closed. The repository remains private for future tests. The temporary CLI binary, its fixture link, and the test work-repository binding are removed. [Fixture cleanup](cleanup.json) records those actions.

The test configures only the isolated reminder registration. The prior [complete installed group controls](../installed-release-controls/README.md) cover the combined workflow. Production `.212`, its Discord gateway, and FlashNext tiers do not change. The final `.252` account still omits optional GitHub integration.

These controls establish delivery and repeat suppression after acknowledged success. A server-side issue creation followed by a lost acknowledgement remains an unknown external outcome. They do not prove exactly-once delivery across that failure window. Actual Discord question, answer, timeout, and cancellation remain combined-release acceptance.

The [22 focused evidence and reminder tests](tests.txt) pass without skips. Exported HTTP headers normalize CRLF line endings to LF; their values remain unchanged. The development completion gate now passes. The release completion gate refuses only `release-adapter-01`. The checklist verifies 151 of 152 scenarios, and the accepted finite contract verifies all 74 registration effects. These counts do not assert universal native-handler parity beyond the accepted contract.
