# Current authority before native responses

Date: 2026-10-08. The candidate uses the prepared Knowledge command sources.

The [baseline](before.txt) changes actual HTTP channel permissions after native canonical parsing and staged index rendering. Both governed operations still return private records or staging titles under the earlier scope. The two tests fail.

The public native memory service now captures the initial configuration and scope, dispatches the native operation, and checks current authority before returning its response. Existing publication callbacks still check authority before writes. This common response boundary covers native operations whose result shape differs from an ordinary tool receipt.

If authority changes after a write commits, the service returns `EACCESS_CHANGED` and says that it withholds the response. It does not report that the write failed. The committed fact and ledger receipt remain available to an authorized caller. An authorized retry does not create another fact.

The [first adjacent gate](first.txt) passes 72 tests. The [expanded adjacent gate](expanded.txt) passes 73 of 74 tests. The additional receipt test initially counts all lexical search matches instead of the exact saved content. Its query also matches the fixture's original fact. The corrected [focused gate](focused.txt) passes all four response checks in 5.122 seconds, with warnings treated as errors.

The [complete memory runner](run_regression.py) selects all 124 memory modules. It pins both host source selectors and the native LifeOS source. It restores ordinary SIGINT handling before child tests. The broad regression remains pending until its output and completion marker exist.

The new service check adds no native patch, dependency, model mapping, or deployed configuration change. Complete native caller coverage, installed application acceptance, background activation, recovery, and release deployment remain open. Ownership stays disabled on `.252`.
