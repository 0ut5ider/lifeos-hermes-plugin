# Current audience for learning and Wisdom

Date: 2026-10-08. Scope: the daily text release candidate. Installed ownership remains disabled.

The [initial experiment](before.txt) changes channel permission overrides after actual native source collection or rendering. Seven of eight cases fail. A configuration-only check permits learning hypotheses, rating reports, recurrence reads and registry writes, Wisdom frame reads, Wisdom synthesis reports, and frame updates after another member gains channel access.

The five service callbacks now use the existing current-context check. That check compares the configuration and resolved scope, and reads current Discord permissions through the authenticated audience API. A changed audience prevents publication or source delivery.

The [focused controls](after.txt) pass all eight cases. They use the actual native Bun operations, SQLite journal, and an authenticated local HTTP fixture. Observers run the real collection or renderer before changing the HTTP permission data. The tests check that source results stay withheld and native files remain unchanged. An unchanged-audience control publishes a real frame update.

The [combined gate](focused.txt) passes 96 tests without skips. It covers Discord admission, hypotheses, recurrence, learning ratings, Wisdom readers, and Wisdom updates. Existing comparisons use the pristine pinned LifeOS revision `5e2f2e8c0abde612da0e99c16c0d07d4ec21b88c` with the selected YAML 2.9.1 dependency. The [runner](run_gate.py) writes `focused.done`.

The initial regression runs use an incorrect patched comparison tree, then a pristine tree without its required YAML package. Their outputs remain recorded as `focused-control-source-error.txt` and `focused-pristine-dependency-error.txt`. Two focused test iterations also observe expected registry and lock initialization. The final fixture initializes the registry before comparing native artifacts. These failures do not count as passing release evidence.

This unit does not add the final outbound Discord delivery gate. Live audience acceptance, installed ownership, scheduled execution, and combined release acceptance remain open. No candidate application code deploys in this unit.
