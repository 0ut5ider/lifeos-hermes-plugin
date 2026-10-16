# Documentation audit

Date: 2026-10-16.
Role: Independent documentation reviewer.
Question: Can public readers and future agents find current setup instructions, source ownership, tests, and release evidence?
Model: gpt-6.1-sol, inherited Codex configuration.
Baseline: `455154c19611da320086592b98e15ead302817dc`.

## Result

The repository contains the needed operational evidence. Its active documentation does not provide a reliable entry point.
Current instructions share pages with superseded installation procedures, server-specific history, and completed work described as pending.
The primary agent can correct these documentation defects without changing product behavior or deployment.

The tracked baseline contains 20,148 files, including 921 Markdown files. The agent archive contains 4,854 files.
The verification archive contains 14,036 files. These are evidence inventories, not counts of independently supported features.
Keep those archives available, but give users and contributors shorter task-specific routes into them.

## Scope and method

I reviewed the root README, TODO, development README, direct `docs/*.md` guides, plugin manifests, installer entry points,
release-manager command parser, both dashboard bundles, and current 0.7.2 release evidence.
I did not inspect every archived fixture, vendor snapshot, personal store, or private runtime record.
The report records baseline findings even where the primary agent corrects the working tree during this audit.

I checked local Markdown links against tracked files and heading anchors. The initial scan found no missing targets,
untracked file targets, or unmatched heading anchors in the selected public guides.
This is a repository-target check. It does not verify remote HTTP availability or a browser-rendered document.

I ran `node --test tests/*.cjs`: all 42 tests pass, with no skips.
These tests use component and Software Development Kit fixtures. This result does not establish browser or installed-service acceptance.
I also ran the source-preparation and package-builder help commands to verify their documented argument names.

## Findings

### D1, P2: Current setup instructions route readers into superseded installation paths

Baseline evidence:

- `README.md:294` starts the supported complete-package workflow, but `README.md:383` starts another primary-looking installation guide.
- `README.md:366` says release 0.4.3 remains the latest stable package. `VERSION` and the current release record identify 0.7.2.
- `docs/installation-workflow.md:3` prescribes Hermes, Bridge plugin, then native LifeOS, rather than the current manager bootstrap.
- `docs/installation-workflow.md:11` names Bun 1.3.14. The 0.7.2 qualification records Bun 1.4.3.
- `docs/installation-workflow.md:20` names nine Hermes patch groups. The current source declares ten.
- `docs/installation-workflow.md:27` requires the earlier Hermes base `758ad514...`. Current source pins `71d34bad...`.

Impact: A public reader or agent can select the wrong bootstrap, old source base, or component-only update.
The old paths retain useful development history, but their placement makes them appear supported for current complete releases.

Correction: Make `docs/installation-workflow.md` the current complete-release installation procedure.
Use one concise README path into it. Keep current update and recovery instructions in `docs/update-policy.md`.
Keep manual source preparation in `docs/clean-install.md`, explicitly for source development and isolated verification.
Preserve superseded procedures in dated history, with visible dates and links to current guides.

### D2, P2: TODO and portability status contradict the deployed release

Baseline evidence:

- `TODO.md:3` says published 0.6.0 and both installations on 0.5.0.
- `TODO.md:16` leaves complete 0.7.0 qualification and deployment unchecked.
- `docs/memory-portability.md:3` says development and daily remain on 0.5.0.
- `docs/memory-portability.md:50` says no release check selects 0.6.0 on either server.
- `docs/verification/2026-10-16-release-0.7.2/PROGRESS.json` records `DEPLOYED_VERIFIED`, both updated, publication complete, and HTTP preservation verified.

Impact: Future agents can restart completed release work, misreport support, or treat implemented owner actions as missing features.

Correction: Keep current unfinished work in TODO. Move detailed completed release chronology to release evidence and the changelog.
Describe import, export, return, and removal as qualified owner actions. Installing a release does not execute those actions automatically.
Use the current release record for deployment state rather than repeating status across old plans.

### D3, P2: Patch reference gives the wrong active bundle

Baseline evidence:

- `docs/patch-footprint.md:3` claims eleven Hermes groups plus twenty-five LifeOS patches, total 36.
- `docs/patch-footprint.md:19` lists `hermes-protected-instruction-approval.patch` as active.
- `docs/clean-install.md:15` claims all 17 patches pass.
- `scripts/prepare_sources.py:19` and `lifeos_hook_bridge/install_source.py:30` declare ten Hermes groups and twenty-five LifeOS patches.

Impact: Maintainers can reintroduce an inactive patch, miscompare patch copies, or mistake a valid source preparation for an incomplete bundle.

Correction: Keep `docs/patch-footprint.md` current at 35 active patches. Mark older reduction test counts as historical.
Point to the two ordered source declarations and both distributed patch directories.
Describe the removed protected-instruction patch only in its dated reduction decision or history.

### D4, P2: No contributor or agent entry point explains source ownership and test boundaries

Baseline evidence:

- The root tree has no tracked `CONTRIBUTING.md`, documentation index, or codebase map.
- `development/README.md:1` documents private hook capture. It is not a general contributor guide.
- The repository has 527 tracked files under `tests/` and two independently installed plugins.
- The two dashboard manifests point directly to tracked `dist/index.js` and `dist/style.css`.
- There is no plugin-local `package.json` or separate JSX source/build tree.
- `scripts/build_managed_release.py:23` refuses uncommitted tracked changes and packages selected committed paths.
- Its output declares `combined_release_verified: false`; package creation does not issue a qualification certificate.

Impact: New agents must infer the ownership split, may invent an npm build, or may use a package-builder success as release qualification.

Correction: Add `CONTRIBUTING.md` for bounded development and verification. Add `docs/codebase.md` for request flows and source locations.
Map the Bridge initializer, bridge event translation, dashboard API, memory policy/native adapter, HTTP transport, release manager,
worker/recovery journal, patch directories, tests, and private capture. Identify editable dashboard assets explicitly.
Separate component tests, prepared native tests, installed acceptance, package qualification, and deployment evidence.

### D5, P2: Long historical prose obscures the current public contract

Baseline evidence:

- The baseline README is 568 lines, with multiple very long paragraphs and repeated component checkpoints.
- `README.md:24` introduces historical 0.5.0 deployment details before the project description at `README.md:69`.
- `README.md:212` aggregates many paired-effect checkpoints in one paragraph.
- Later paragraphs repeatedly report remaining activation, release, or guest work that is complete in current evidence.
- `docs/full-experience-release-plan.md`, `docs/memory-import-plan.md`, and `docs/fresh-store-selection.md` mix accepted designs,
  obsolete pending decisions, installation-specific state, and implementation checkpoints.

Impact: Search results can select an old caveat as current policy. Public readers must understand Adrian's server history before installing.

Correction: Put the project purpose, current support boundary, install path, HTTP guide, and contributor route first.
Retain unique history in dated snapshots. Mark older design and test pages with a historical banner and a current destination.
Do not rewrite original test receipts or present inherited evidence as a new result.

### D6, P2: Discord instructions combine mutually different audience modes

Baseline evidence:

- `docs/discord-setup.md:25` describes the daily private channel and says sharing remains disabled, a dated checkpoint superseded by HTTP acceptance.
- `docs/discord-setup.md:31` starts the one-private-channel configuration that refuses threads and direct messages.
- `docs/discord-setup.md:51` then requests thread permissions in the general numbered setup.
- `docs/discord-setup.md:88` explains thread and direct-message admission without clearly separating the general Hermes mode.
- The guide embeds local channel IDs, account IDs, migration paths, and firewall UID history alongside public setup instructions.

Impact: A reader can follow later generic instructions and expect threads or direct messages to work with the restricted LifeOS profile.

Correction: Keep a current private-channel setup guide with placeholders. Separate general Hermes behavior and historical migration observations.
State that channel allowlisting and verified private-memory audience admission are separate checks.
Preserve historical IDs and firewall observations only in dated evidence or history.

### D7, P3: The portability reference needs the actual owner button sequence

Baseline evidence:

- `docs/memory-portability.md` describes contracts and qualification well, but gives no complete user navigation sequence.
- The Bridge bundle exposes `Import Hermes memory`, `Export memory and return to Hermes`, and `Prepare return to built-in Hermes`.
- The Releases bundle exposes `Advanced: memory ownership and removal`, `Apply reviewed provider return`,
  `Prepare complete LifeOS removal`, and `Remove reviewed LifeOS software`.
- The source requires an explicit Discord-disablement acknowledgement and shows a retained standalone recovery command before removal.

Impact: The user cannot infer which page applies a reviewed return or why removal preparation is disabled.

Correction: Make `docs/memory-portability.md` the canonical user guide. Include source review, item decisions, plan approval,
export retention/capacity, separate provider-return application, removal acknowledgement, and recovery-command retention.
State that provider return, previous-installation selection, software removal, and data erasure are different actions.

## Canonical destinations

| Reader task | Canonical document |
| --- | --- |
| Understand the project and current support | `README.md` |
| Find a task guide | `docs/README.md` |
| Install a complete release | `docs/installation-workflow.md` |
| Update, inspect, recover, or roll back | `docs/update-policy.md` |
| Configure restricted Discord text | `docs/discord-setup.md` |
| Connect another agent over HTTPS | `docs/http-memory-mcp.md` |
| Import, export, return, or remove software | `docs/memory-portability.md` |
| Find code and request boundaries | `docs/codebase.md` |
| Contribute and select meaningful checks | `CONTRIBUTING.md` |
| Prepare pinned source trees | `docs/clean-install.md` |
| Record unfinished work | `TODO.md` |
| Inspect exact release support and limits | `docs/verification/2026-10-16-release-0.7.2/README.md` |
| Inspect historical decisions | dated history, `notes/`, and original evidence |

## Source facts to preserve in the cleanup

- Plugin declarations live in `plugin.yaml`. Dashboard declarations live in `dashboard/manifest.json`.
- The current integration targets Hermes base `71d34bad1045610252eda02ee79549436896e784` and LifeOS base `5e2f2e8c0abde612da0e99c16c0d07d4ec21b88c`.
- `hermes lifeos-release prepare` stages programs. The owner separately reviews and applies the exact operation.
- CLI actions are `prepare`, `status`, `start`, `recover`, and `rollback`. `--version`, `--name`, and `--assistant` belong to `prepare`.
- Managed native mounting requires authenticated dashboard owner admission. Do not advise a CLI bypass for that grant.
- Both update buttons select the complete qualified integration, not only the small manager plugin.
- Installation does not activate memory ownership, import data, authorize external clients, or configure a Discord bot automatically.
- Recovery and rollback refuse later divergent programs. A later remount can expire an earlier operation's rollback.
- The current release has one workstation error and one failure among 1,124 integration cases. All eight boundary cases pass under the isolated service account.
- Current release evidence explicitly records no new automatic morning observation and no repeated whole-guest restore.
- Private capture retains ordinary prompts and conversation content. Its redaction is not a guarantee that arbitrary secrets disappear.
- Optional SSH sharing remains a separately installed component. It is not a prerequisite for the recommended HTTP connection.

## Verification checklist for the primary agent

1. Compare new current guide commands and button labels with the source locations above.
2. Scan relative links, heading anchors, and tracked targets in all changed active guides and moved history.
3. Check the ordered patch counts and paired distributed patch bytes.
4. Verify current version declarations and the published/deployed status against the 0.7.2 evidence.
5. Keep dated verification and review artifacts unchanged except this new audit directory.
6. Confirm that documentation does not promise voice, media processing, automatic memory ownership, or arbitrary upstream compatibility.
7. Run `git diff --check` and check authored prose for em dashes.
8. Confirm that no product files or private runtime data enter the documentation change.

## Raw evidence

- `inventory.json`: selected public document inventory and baseline identity.
- `source-evidence.json`: original tracked excerpts with line numbers, active patch declarations, source entry points, and tracked-file counts.
- `relative-link-audit.json`: initial selected-guide repository link scan, no findings.
- `ui-command.txt`: raw 42-case Node test output.
- `cli-help.txt`: raw source-preparation and package-builder usage output.

These files contain tracked public material and safe command output only. I changed no product file and no active guide.
