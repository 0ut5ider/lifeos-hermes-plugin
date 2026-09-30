# Native proposal foundation closure

Date: 2026-09-30  
Role: Independent code and real-native regression reviewer  
Question: Do the upgrade identity and publication destination fixes close the two confirmed proposal foundation defects without breaking permission, receipt, decision, or recovery behavior?  
Model: GPT-6. The exact model variant is not exposed in this agent context.

## Conclusion

Both defects from the initial proposal foundation review are closed in the current reviewed snapshot. The two original reproduction scripts were run unchanged and now produce the required results. I found no additional meaningful defect in these focused fixes.

The initial findings remain documented in `../memory-proposal-foundation.md`, with their original raw outputs and source snapshots. This closure covers the implemented proposal operations and these corrections. It does not approve memory ownership activation or claim that raw native decision interception, automatic approval, proposal UI controls, or complete lifecycle/source coverage are finished.

## 1. Distinct diverted claims preserve distinct native records

Native `Upgrades.addUpgrade()` now appends its existing normalized claim hash to the timestamp and slug identifier. Different native claims with the same timestamp and eight-word slug therefore receive different destinations. The change retains the native claim deduplication mechanism.

The unchanged `probe_upgrade_collision.py` submitted eight distinct claims with the same first eight words:

| Observation | Initial source | Fixed source |
|---|---:|---:|
| Requests acknowledged as diverted | 8 | 8 |
| Distinct destination files | 2 | 8 |
| First retry's destination contains its original claim | No | Yes |

The current regression test also checks every saved claim against its destination and every identical retry against its original receipt. It passed. The actual final file contents and receipts are preserved in `raw/probe_upgrade_collision.txt`.

No clock, routing function, or native publication was mocked. The collision probe and its closure copy have identical hashes.

## 2. Dangling upgrade symlinks are rejected before journaling their destination

The publication helper now uses `lstatSync()` directly. It accepts absence only when the error code is `ENOENT`. An existing directory entry must be a regular file; symlinks, including dangling symlinks, are rejected. The helper retains its physical upgrade-store and USER_DATA parent checks.

The unchanged `probe_upgrade_symlink.py` still creates a dangling `.state.json` link pointing outside the synthetic user boundary, within the disposable fixture home. Its observed result now is:

```text
Outside target created: false
Operation: unknown, native publication needs a regular file destination
Next governed proposal review: []
Recovery journal remaining: false
```

The operation can have created its upgrade record before it reaches the invalid sidecar destination, so an `unknown` receipt followed by recovery is truthful. Recovery rolls back the partial record publication; it does not try to resolve an invalid sidecar path from the journal. The current regression confirms that no diverted record remains after recovery.

The unsafe symlink itself remains present. The operation did not create its outside target, and subsequent governed reads are no longer blocked by an unrecoverable journal. A further attempted publication through the same unsafe link still requires rejecting it or repairing the fixture; this closure does not silently remove user filesystem entries.

Complete output is in `raw/probe_upgrade_symlink.txt`.

## Other repeated verification

### Native approval interruption and retry

The unchanged approval recovery probe exited the Python child with status 73 immediately after the real native acceptance changed the target and queue, before the receipt commit. The next governed review restored the exact original bytes of both files, returned one pending proposal, and cleared the journal. An identical request retry committed once, with one occurrence of the edit in the target.

See `raw/probe_approval_recovery.txt`.

### Request and reference validation

All 13 unchanged service-boundary checks passed:

- Seven malformed or unsafe proposals were rejected, including private rationale and an invalid identity target.
- Four malformed references were rejected.
- An external creator without approval permission could not approve.
- A changed native queue row caused a revision conflict without changing the target.

See `raw/probe_proposal_api.txt`. These calls used the actual service, saved configuration, and native tools in disposable fixtures.

### Test suites

All commands used `/home/outsider/.cache/lifeos-plugin-memory/memory-plugin-test-env/bin/python`.

| Suite | Result | Output |
|---|---|---|
| Native proposal suite | 11 passed in 4.743 seconds | `raw/proposals-tests.txt` |
| Memory policy suite | 6 passed in 0.005 seconds | `raw/policy-tests.txt` |
| Memory service suite | 9 passed in 4.021 seconds | `raw/service-tests.txt` |
| Installed-copy MCP transport | 1 passed in 1.983 seconds | `raw/mcp-tests.txt` |

All 27 tests passed. The original four probe scripts also completed with their expected outcomes. The MCP test exercises the actual installed-copy transport; it is not a mocked tool schema test.

## Source verification

`raw/hashes.json` and `raw/snapshot-*` preserve the plugin, public native source, tests, and generated LifeOS patch used for this closure. Ending hashes match all starting hashes; `raw/source-drift.json` is empty. The top-level and bundled `lifeos-memory-access.patch` files are byte-identical, recorded in `raw/patch-verification.json`.

`raw/probe-hashes.json` records matching hashes for the four original probes and their saved closure copies. Commands are in `raw/commands.txt`.

This check confirms the actual managed native source and patch-copy equality. It does not claim that an entire release bundle was freshly prepared and activated by this reviewer; source preparation remains primary-agent work.

## Boundaries and remaining gates

No implementation files were edited or committed. No live server, production memory, journal, or fleet host was accessed. Tests used temporary user-data trees, real public native tools, synthetic proposal targets, and child process interruption. No memory ownership configuration was activated by this review.

The full older memory suite, generic host middleware tests, real SSHD sharing test, and browser UI were not repeated for these two focused proposal fixes. Their earlier results remain in preceding reports. The current proposal suite exercises creation, review, approval separation, target compare-and-swap, rejection, diversion, retries, and rollback within the managed API.

## What deserves Adrian's review

The concrete proposal foundation defects are independently closed. The next integration work must still govern raw native decision/helper paths and automatic approval before ownership activation. Proposal bodies and approved target edits must remain subject to the eventual complete source and conversation lifecycle checks. Those are declared open gates, not features certified by these 27 tests.
