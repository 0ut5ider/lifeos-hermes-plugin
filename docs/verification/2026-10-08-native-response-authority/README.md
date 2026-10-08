# Current authority before native responses

Date: 2026-10-08. The candidate uses the prepared Knowledge command sources.

The [baseline](before.txt) changes actual HTTP channel permissions after native canonical parsing and staged index rendering. Both governed operations still return private records or staging titles under the earlier scope. The two tests fail.

The public native memory service now captures the initial configuration and scope, dispatches the native operation, and checks current authority before returning its response. Existing publication callbacks still check authority before writes. This common response boundary covers native operations whose result shape differs from an ordinary tool receipt.

If authority changes after a write commits, the service returns `EACCESS_CHANGED` and says that it withholds the response. It does not report that the write failed. The committed fact and ledger receipt remain available to an authorized caller. An authorized retry does not create another fact.

The [first adjacent gate](first.txt) passes 72 tests. The [expanded adjacent gate](expanded.txt) passes 73 of 74 tests. The additional receipt test initially counts all lexical search matches instead of the exact saved content. Its query also matches the fixture's original fact. The corrected [focused gate](focused.txt) passes all four response checks in 5.122 seconds, with warnings treated as errors.

The first broad run used an incomplete environment. It omitted the pristine source selector for native comparisons and the locked TOOLS and PULSE package installations. The [retained run](environment-incomplete-regression/regression.txt.gz) contains these failures and its manual interruption. Compression preserves its original bytes. Its [receipt](environment-incomplete-regression/regression-results.json) records exit `-2`. No process from the interrupted child remains running.

The TOOLS and PULSE dependencies now use their existing frozen locks on both candidate and pristine sources. The [environment check](regression-environment-final.txt) passes three representative controls that failed in the incomplete environment. It includes the actual graph package, PULSE adapter schema, and native count comparisons.

The [complete memory runner](run_regression.py) selects all 127 memory modules. It pins both host source selectors, the native LifeOS source, and the pristine comparison source. Each module runs in a separate unittest process. Three test processes run concurrently. The runner records every command, exit status, source selection, and complete log. It restores ordinary SIGINT handling before child tests. Its original results and completion marker remain retained.

The [accepted regression](accepted-regression.json) verifies **1,428 tests in 127 modules**, with no skips or warnings in the accepted logs. The original broad run returns exit `1`. It contains one graph assertion that expects the earlier response contract. Its [corrected module](graph-response-authority.txt) passes 18 cases and requires the `EACCESS_CHANGED` response without output or a private receipt. The unchanged graph cache assertion remains active.

The broad log audit also finds three unclosed in-memory SQLite connections in the recovery test fixture. The fixture now closes each connection during cleanup. The [corrected module](review-connection-cleanup.txt) passes all nine cases without resource warnings. The original failure and warning logs remain in `regression-modules/`. The accepted receipt records the replacement logs and source hashes for these two modules. It does not report the original run as successful.

The new service check adds no native patch, dependency, model mapping, or deployed configuration change. Complete native caller coverage, installed application acceptance, background activation, recovery, and release deployment remain open. Ownership stays disabled on `.252`.
