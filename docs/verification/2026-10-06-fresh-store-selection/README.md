# Fresh store selection and return from the page

Date: 2026-10-06. This unit runs the complete fresh-start workflow through the plugin page in the disposable guest CT `100`. Adrian approved the [selection design](../../fresh-store-selection.md) on 2026-10-06. The guest starts from the snapshot `lifeos-page-60b1446`: stock Hermes with the page-installed LifeOS 7.40.4 and the Hermes patch. Production on `.212` stays unchanged.

## Steps and results

1. The owner claims the installation: `POST /memory/owner` returns HTTP 200 ([claim.json](claim.json)). The configuration keeps ownership and sharing disabled.
2. The page prepares a new candidate ([candidate2.json](candidate2.json)) and a fresh store for Adrian and Cerebo through `POST /memory/fresh/start`. The store reaches `review` with 0 active facts ([fresh-status.json](fresh-status.json)).
3. `POST /installation/selection` queues the detached selection worker. The first attempt rolls back ([select-status.json](select-status.json)); see the failures below. After the fix, the second attempt reaches `applied` ([select-status-2.json](select-status-2.json)). The profile setting names the store home and keeps `/home/hermes/HermesWorkspace` as the workspace. The memory configuration root names the store installation. The gateway and the dashboard are active, and the dashboard reports the store as its running home.
4. A turn answers: "I'm Cerebo and you're Adrian" ([turn-selected.txt](turn-selected.txt)). The hooks write their state under the store home. The account home `~/.claude` and `~/.config/LIFEOS` receive no writes during the turn.
5. `POST /installation/selection/return` reaches `applied` ([return-status.json](return-status.json)). The setting file is absent, the configuration root is `/home/hermes/.claude` again, and `SOUL.md` no longer names Cerebo. A turn answers as LifeOS ([turn-returned.txt](turn-returned.txt)). VersionDrift reports 0 changes. The fresh store stays on disk.

The guest snapshot `fresh-select-e64e2b1` retains this state.

## Failures found and fixed in this run

| Failure | Cause | Fix |
| --- | --- | --- |
| Store preparation failed: `The backup directory changes its physical path or owner permissions` | The guest user umask is 0002. Candidate and installed directories were group-writable, and the store refuses non-private trees. | `693ed30` clears group and other write bits from prepared and installed trees. |
| A second preparation failed the same way | The fresh store routes used the first candidate path, not the selected candidate. | `eac853f` uses the selected candidate. |
| The first selection rolled back: `The mount journal belongs to another installation or is invalid` | The profile mount journal names the installed root that wrote it. | `e64e2b1` accepts a finished journal of another home and still refuses a pending one. |

The rollback in the first selection attempt restored the previous setting, configuration root, and services without manual steps.

## Limits

- The memory status on the account installation reports `LifeOS MEMORY is outside the physical USER_DATA boundary`. A page installation keeps `LIFEOS/MEMORY` inside `~/.claude`, and native memory expects it under the user data tree. A fresh store moves it there. Managed memory views for the account installation therefore stay unavailable.
- Selection refuses a store with managed memory (enabled ownership or a native connector). Ownership activation remains a separate gate.
- The guest has no native Pulse unit, so the Pulse drop-in path is not exercised here.
- This run does not kill the selection worker. The transaction tests cover recovery after process death in three states.
- Native hooks run with `HOME` set to the store home. Tools that read other account dotfiles, beyond Hermes, Git identity, and helper model settings, see the store home.
