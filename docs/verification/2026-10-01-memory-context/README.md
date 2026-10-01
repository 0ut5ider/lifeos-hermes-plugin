# Governed native PULSE context builder

Date: 2026-10-01. All data is synthetic. Ownership remains disabled on running installations.

## Behavior

The managed native context builder requires current unrestricted owner recall before collecting context and before returning it. It reads the four native identity, goals, and project files through the source service. The service verifies exact physical paths, native text validation, and retirement policy. Each identity source has a 256 KiB limit. An excluded or missing source produces its native unavailable placeholder. The native prompt ordering, active-session slice, hot-memory formatter, retrieval, and 60,000-character ceiling remain present.

Managed context does not use the process-global file-mtime cache. Every managed request checks current policy and current native facts. Standalone context keeps its native cache. The managed-mode observation survives connector removal in the same process. A persistent managed HTTP marker preserves that refusal across restart; recoverable ownership setup must install that marker.

The native connector supplies the current environment explicitly to `spawnSync`. Real subprocess probes reproduce two Bun behaviors without this argument: a newly assigned caller context does not reach the child, and a removed initial owner context remains in the child. Both directions now receive the current caller metadata.

Display names come from a separate native configuration loader. Managed calls refresh those labels each turn and apply native text validation and retirement checks. Excluded labels use the native generic names. Configuration fields beyond those names do not enter this block.

## Evidence

- `before.txt`: twelve original cases reproduce raw identity output and cache bypasses. Owner hot-memory controls fail because the child environment does not receive the runtime context.
- `child-environment-before.txt`: two actual connector probes isolate both stale-environment directions.
- `cache-boundary-before.txt`: the environment correction restores the owner controls. Nine cases still fail at the raw identity and cache boundaries.
- `after.txt`: fourteen context and connector cases pass in 18.903 seconds.
- `display-names-before.txt`: an incomplete TOML fixture falls back to generic names. It does not establish private-label exclusion.
- `display-names-boundary-before.txt`: a valid native fixture reproduces private-name output and stale configured names.
- `expanded.txt`: the earlier expanded fixture still lacks the required native voice identifier. Its name results are superseded by the valid fixture in the complete gate.
- `focused.txt`: implemented cases pass, but an incorrect test module name fails the command. This is not a passing gate.
- `patch-gate.txt`: two preparation controls pass; the real-source case skips because the command omits repository inputs. This is not a complete preparation gate.
- `patch-gate-complete.txt`: all five actual-source preparation and patch-bundle cases pass in 4.429 seconds without skips.
- `focused-complete.txt`: the corrected combined command tests valid fixtures and actual source inputs.

The combined distributed gate passes 61 cases in 70.270 seconds without skips, failures, or errors. It includes eighteen native context cases, retained-source and native-delegation cases, child cases, seven actual Hermes provider cases, and five source-preparation and patch-bundle cases.

The detached broader gate at revision `6663d50` also completes with exit status zero. It tests the memory modules discovered at start, followed by the actual Hermes provider and source-preparation suites. `regression.txt` preserves the commands and full output. Wiki renderer fixtures created later are a separate gate, not part of this result.

Prepared inputs use Hermes `758ad514eb0e800547e015edf05aa18f78b78d82` and LifeOS `5e2f2e8c0abde612da0e99c16c0d07d4ec21b88c`. The existing LifeOS memory patch now changes 23 files. The nine Hermes patch groups and ten LifeOS patch groups remain unchanged.

## Limits

These tests exercise the exported context builder in a long-lived real Bun process. They do not translate Siri credentials into a memory grant, call the Claude Agent SDK, or verify final model delivery. A caller without a verified owner context receives an unavailable error. Restricted identity context and full lifecycle behavior remain open.

Unclassified identity sources retain the existing age rule: a source that predates a correction or forget request requires fresh review. The builder does not silently adopt that old source. This can produce unavailable identity sections until fresh source review occurs.

The dependency log installs the existing PULSE frozen lockfile into an owned test cache, with install scripts disabled. It adds no plugin dependency. It prepares later wiki tests. It does not constitute wiki coverage.
