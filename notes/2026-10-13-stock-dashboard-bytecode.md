# Stock dashboard review changes the candidate it reviews

2026-10-13, LifeOS release UI acceptance on stock Hermes v0.21.7.

The native web form installs manager 0.4.1 successfully. A real Hermes conversation loads its release skill and prepares public 0.4.1 in 86.3 seconds. The owner reviews the ready operation. The next installation click refuses before admission because the qualified bridge contains four unrecorded Python bytecode files. The active programs stay unchanged.

The dashboard process uses Python with `-I`. Its environment contains `PYTHONDONTWRITEBYTECODE=1`, but isolated Python ignores that variable. The first review imports the candidate and writes bytecode. The second validation correctly refuses those additional files. Previous command-line acceptance uses `-B`; the complete managed runtime also disables bytecode. Those paths do not reproduce the stock dashboard condition.

A regression starts actual isolated Python with the environment variable set. It imports the bridge and its release-version module. Before the fix, the test finds two bytecode files. The source loader now sets `sys.dont_write_bytecode` before importing qualified code. The test must find no additional files. The original rejected operation remains retained. Acceptance requires another clean preparation, owner review, and installation. Removing the unexpected files from the original operation would hide the cause and is not a repair test.
