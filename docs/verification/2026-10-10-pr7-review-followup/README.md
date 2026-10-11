# PR7 review verification and worker-test cleanup

Date: 2026-10-10. Adrian requests the review findings and correction of substantial issues.

The [independent review](../../agents/2026-10-10-pr7-daily-release-review/pr7-daily-release-review.md) finds no blocking product defect. The reviewer checks PR7 from base `531f86169550ae118b1624a9cffe809211d7a3bf` to head `4034bc27796433f71c6ba2ec061d1e7e8e135b8f`. It verifies fresh-store isolation, exact retained examples, private preparation, current authority, job deadlines, child lifetime, and release provenance.

The reviewer reports ten ResourceWarnings in worker tests. The [primary baseline](before.json) reproduces them. All 35 unittest assertions pass and unittest exits zero. The strict output check exits one because Python prints the finalization warnings as ignored exceptions. The existing warnings-as-errors option does not convert those exceptions into unittest failures.

Five worker processes leave their captured stdout and stderr pipes open after `wait`. The test correction uses `communicate` to drain and close both streams. Failure assertions retain the captured output. The interruption test still terminates the complete native process tree. No plugin or native program changes.

The [primary repeat](after.json) passes all 66 focused review tests with zero warnings, zero ignored exceptions, and no skipped cases. It covers fresh-store preparation, relay authentication and deadlines, concurrent Algorithm admission and shutdown, path isolation, signed review status, worker failure and interruption, and dashboard preparation. The runner rejects warning and ignored-exception lines instead of relying only on the unittest exit code.

The [primary certificate verification](primary-certificate-verification.json) reproduces the committed release certificate exactly. It compares 200 plugin files, 1,953 native fixture files, and 16,525 canonical Hermes fixture files. The [repeated archive and template audit](input-audit.json) checks archived plugin bytes, compiled Pulse pages, 54 empty personal files, three omitted example files, and exact retained originals. Missing provenance, a symlink leaf, and a missing Finance template marker all refuse preparation.

The [follow-up receipt](FOLLOWUP.json) records the tested worker-file hash and unchanged program identity. The frozen package remains at `11577ed4873a0b6186a1dfa13aa44f893254cb99`. Its archive and release certificate stay unchanged. The source archive contains the earlier test harness; this record separately verifies the corrected harness. The earlier 38-test fresh record includes the ten warnings and stays retained. It must not be called a clean-output result.

The primary does not repeat the 490-test batch, remote installation, or browser interaction. No product byte changes require those repeats. The original installed and browser evidence remains linked to the sealed package. This follow-up makes no remote system changes.

PR7 can proceed to merge after Adrian accepts its review. The daily VM, coherent off-server whole-guest restore, final private Discord channel, bot cutover, and memory activation remain separate release gates. The original review and this follow-up do not establish those results.

The reviewer's exact Git patch and SHA-256 are retained in [the raw patch record](../../agents/2026-10-10-pr7-daily-release-review/raw/reviewed-diff.patch.json). JSON preserves the patch's required blank context lines without a repository whitespace violation. A plain-text copy remains on disk as `reviewed-diff.patch.log`.
