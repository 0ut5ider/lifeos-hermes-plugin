# Managed native staged Knowledge publication

Date: 2026-10-01. Branch: `feature/lifeos-memory`. Data is synthetic. No running ownership activation.

## Publication contract

The owner previews one exact staged note or a batch of up to 50 notes. Publication binds staged bytes, the selected project, current canonical sources, harvest state, derived indexes, scope, and installation to that preview. The cooperating transaction records destination files, staging files, all five native indexes, and harvest state before publication. A changed preview refuses publication. A retry returns the original committed receipt.

The plugin preserves native note bytes except the native removal of `status: pending-review`. It registers the body with a current reference. Project assignment defaults to unclassified. A project reader cannot read an unclassified note. An explicit project assignment grants the declared project scope. Authenticated native callers retain their source session and writer.

Only four native harvest domains are supported: People, Companies, Ideas, and Research. Paths must resolve to exact physical locations. A source has a 256 KiB limit. The transaction has a 3 MiB declared-source limit. Existing destinations refuse the batch before publication. The managed batch limit is 50, matching the native backfill batch size; an accumulated larger queue needs multiple reviewed batches. This limit does not establish arbitrary-size native `promote --all` parity.

Native validation checks the unchanged body. Native Cortex parses metadata and requires unchanged source text. Current policy excludes forgotten or superseded claims and staged sources that predate a correction or forget request. A source-age refusal requires fresh review input. Publication does not change that retention rule. Unknown source adoption remains a separate operation.

## Derived indexes

Native KnowledgeHarvester retains its frontmatter parser, backlink rules, domain templates, and master template. The plugin supplies the current registered corpus and the promoted notes. The renderer returns declared writes without scanning another corpus. Unregistered and retired notes do not enter the generated indexes. Registered current notes remain present. The plugin validates destinations and publishes those indexes in the same transaction as the notes.

Native harvest state requires a valid clock. Arbitrary text cannot use that metadata slot to enter the master index. Native record identifiers must be unique across current and staged notes. Both the canonical service and the native managed response reject duplicate identifiers.

These results establish governed index generation during promotion. They do not govern every existing index reader, wiki cache, graph cache, harvester source collector, review or reject command. Those paths remain part of the open inventory.

## Commands

1. Run `bun KnowledgeHarvester.ts promote Research/<slug> --project <project>` to preview one note.
2. Review the returned note, project, signature, and index count.
3. Repeat the same selector and project with `--signature <signature> --request-id <identifier>` to publish it.
4. Reuse that identifier for retry of the same preview.

`promote --all` follows the same preview and application contract for the bounded queue. Omit `--project` to keep notes unclassified. Standalone LifeOS retains its native direct promotion command and output.

## Evidence

- `before.txt`: the unbound native promotion publishes and removes staging. The standalone byte and index control passes. Eight missing-module errors record the absent managed interface.
- `after.txt`: nine initial cases pass. The existing unclassified source-age rule excludes the tenth fixture after an unrelated forget request.
- `expanded.txt`: fourteen cases pass after separate fresh-source and aged-source controls.
- `clock-before.txt`: an arbitrary harvest clock enters index rendering before clock validation.
- `transaction.txt`: eighteen cases pass in 12.288 seconds, including death after staging removal and receipt recovery.
- `batch.txt`: nineteen cases pass in 15.592 seconds. The 50-note preview runs through the actual native connector deadline.
- `duplicate-id-before.txt`: the initial duplicate-ID test passes through an earlier fact-position refusal. It does not verify the duplicate-ID boundary.
- `duplicate-id-boundary-before.txt`: an equal-width ID mutation keeps fact positions valid. Native search and export select different notes with the same ID.
- `staged-id-before.txt`: a staged duplicate ID reaches the planned corpus before publication checks exist.
- `preparation.txt`: ordered distributed source preparation succeeds. The existing LifeOS memory patch now changes 22 files. Hermes patch groups remain unchanged.
- `focused.txt`: distributed staging, recovery, Cortex, and Knowledge-query results follow below.

Pinned source bases remain Hermes `758ad514eb0e800547e015edf05aa18f78b78d82` and LifeOS `5e2f2e8c0abde612da0e99c16c0d07d4ec21b88c`. Ownership setup and complete backup/restore remain open. Restricted prompts, delivery, lifecycle, and the full release gate remain open.

The distributed focused gate passes 65 cases in 72.749 seconds without skips, failures, or errors. It includes 20 staging cases, 18 recovery cases, 17 canonical cases, and ten Knowledge-query cases. The 50-note preview and process-death recovery use actual subprocesses and native files.

The detached complete memory regression at revision `39e7bae` passes 432 cases in 567.440 seconds. `regression.txt` records the raw output. `regression.done` records exit status zero. The separate actual Hermes memory-provider suite passes seven cases in 2.637 seconds. Both runs have no skips, failures, or errors. These are regression results for implemented behavior. The open inventory and activation gates remain open.
