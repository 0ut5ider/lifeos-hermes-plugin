# Atlas initialization and publication boundaries

Date: 2026-10-10

The installed fresh-store check previously returned the native instruction to run an Atlas sync. Local narrative tests created a graph directly with `new Store()`. Those fixtures proved generation from a graph, but they did not prove managed initialization. The new baseline has two sync failures because the owner service has no synchronization operation.

The same baseline has two narrative publication failures. An actual destination change after publication or after the final source snapshot causes refusal, but the operation has already removed its recovery journal. Atlas needs the destination checks and post-publication conflict handling used by the other narrative publishers.

The implementation renders admitted Gear and Projects collectors with the native functions. Native `Store.applyRun` reconciles a private database copy. The planner checkpoints that copy and selects SQLite DELETE journal mode before returning its bytes. The owner service publishes the database and redacted snapshot as one existing recoverable publication group. The service refuses live companion files and rechecks exact destination bytes before receipt finalization. This preserves native identities, incomplete-run observations, and the full-run sweep gate.

The selected release adds an explicit `atlas-sync` owner command. It adds no Atlas timer. Managed `tick` refuses before it consumes hints because an admitted event scheduler is outside this initialization change. Standalone tick behavior remains in the native implementation. Managed raw SQLite writers refuse. The Pulse views continue through their existing owner admission.

The graph remains at the native external state path. The existing USER_DATA backup excludes that path. Rebuilding from retained Gear and Projects files restores current derived assets, but it does not restore prior synchronization or lifecycle history. Final guest backup and recovery acceptance must cover that external directory if preservation of Atlas history is required.

Adrian moves private-channel setup after daily-guest creation. Atlas acceptance remains on the isolated `.252` profile. The live gateway and its disabled ownership configuration are outside this change.

Installed acceptance creates three initial assets and four after a Gear update. Two real private FlashNext responses use `xhigh` with the existing Fable pin. Dashboard reads reuse the current cache without inference. The explicit insight owner command intentionally regenerates; an initial acceptance check incorrectly expected command-level cache reuse. The direct operator also needs the installed Bun directory in its own PATH. Setting only the child command PATH does not cover direct service calls. Both failed attempts remain retained separately.

The final path characterization sets an inherited `ATLAS_DIR`. Native module loading creates that unselected directory even though the database planner uses its private copy. The baseline fails because the extra directory exists. Binding the selected directory before module import prevents the extra effect. The focused repeat and all 81 selected tests pass.
