# KnowledgeDistill digest marking

Date: 2026-10-04. This gate exercises the actual native marking parser and counters with synthetic dated digests, registered current notes, and fixed tracking state. It makes no server changes.

The [initial baseline](before-output.txt) has five failures and one preserved malformed foreign-state control. The [baseline source](baseline-test-source.py) matches the original recorded hash. A separate [valid foreign-state baseline](redirect-before-output.txt) confirms that the original command writes through a redirected state file.

Managed marking requires current unrestricted owner write authority. It admits a bounded regular digest from the fixed dated digest directory. Native private-content validation and current retirement checks exclude private or forgotten claims. Native marking renders its counters and state. The service journals private publication and rechecks source, authority, and expected destination bytes before writing.

The first candidate passes 21 tests and two subtests. A separate [reservation probe](reserved-before-output.txt) then fails: revocation after journal reservation leaves an unknown outcome, and recovery removes a later state edit. Validation failures before publication now commit a conflict receipt. The next read preserves that edit. An actual exit 73 after publication still restores the previous bytes.

The [wide gate](final-output.txt) has one failure, 205 passes, and 104 passing subtests. The original-native comparison finds that compact JSON differs from the native indented state bytes. Values and counters match. The [final format correction](format-correction-output.txt) passes 25 tests and two subtests in 33.77 seconds. It includes all 14 marking controls and all 11 reader controls. Original-native counters and complete state bytes now match. The 205 other wide-gate cases precede this isolated indentation correction.

The [final recorder](format-controls-output.txt) captures 14 passing [native controls](format-native-outcomes/). It retains synthetic digest and state bytes, permissions, actual subprocess output, and exit status. The earlier failed recorder remains in the evidence. All [final correction source hashes](format-correction-command.json) match. The [source comparison](source-comparison.json) verifies all 48 distributed files against the candidate source, and both patches are byte-identical. The [prepared manifest](final-source-manifest.json) identifies the fixture. Dependencies are copied from the preceding prepared fixture; this gate does not claim a fresh installation or TypeScript type checking.

The managed CLI marking path is governed. Headless synthesis still uses its separate raw digest and tracking path and requires its own correction. Aggregate ownership recovery, import, management, jobs, private model acceptance, voice, and the combined release remain open. No running ownership or sharing changes occur.
