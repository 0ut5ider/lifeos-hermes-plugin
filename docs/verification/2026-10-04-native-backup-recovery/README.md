# Separate native backup recovery

Date: 2026-10-04. The [gate](gate.txt) passes 69 tests and 15 subtests without skips, failures, or uncaptured warnings. The [command and source identities](command.json) retain the environment and candidate hashes. The [completion marker](gate.done) records exit status 0.

The [capability check](capability-before.txt) fails before the recovery module exists. The [first gate](initial-gate.txt) passes six tests and fails an inaccurate ranking assertion. The corrected assertion checks that the retired claim is absent. Native ranking can return a different current fact. The [command control](command-before.txt) fails before Hermes supports the recovery option. The [passing command gate](command-gate.txt) then verifies actual parser discovery, selected-profile configuration, and native retrieval without model or HTTP calls.

`hermes lifeos-backup --recover BACKUP --signature SIGNATURE --destination DIRECTORY` reconstructs native USER_DATA and governance metadata in a new private tree. It requires the reviewed backup signature and unrestricted owner authority. It refuses existing targets, targets inside live data or program trees, targets inside the backup, and redirected parents. It verifies all active references through the actual native reader before publication. It preserves backed-up forgotten status, binary files, empty directories, original modes, and modification times.

The recovery tree has its own physical data boundary and relative USER and MEMORY links. Its TOOLS link uses the installed native memory tools. The recovery receipt reports that path. The result preserves the original store, including later facts and later forget decisions. It does not select the recovered tree as the profile's memory provider or start a service. A recovered snapshot can contain facts forgotten after the backup. Activating it requires separate current-state review.

An actual child process exits with code 73 before final tree publication. The original store remains readable. The private staging tree retains a `.native-recovery.json` file with its source, backup signature, destination, and inactive ownership state. The actual native reader verifies the staged references. A fresh recovery succeeds without deleting that staging tree.

The gate also reconstructs a backup after the live USER_DATA directory becomes unavailable. This test retains the original directory under another name. The recovered native references remain readable, and the original directory remains untouched. Existing current-fact repair and staged-publication tests also pass.

The component adds no dependency or host patch. It reconstructs native data only. Hermes configuration, history, skills, program restoration, service recovery, automatic staging recovery, and ownership cutover remain open. The running `.212` profiles remain unchanged, and memory ownership remains disabled.
