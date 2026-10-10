# Native dashboard TypeScript acceptance

Date: 2026-10-08. The candidate uses Bun 1.3.14 and the pinned dashboard dependencies. No dependency, compiler option, or lint rule changes.

The baseline TypeScript check reports two errors. The TELOS shell passes an openFile callback to SubTabs, but SubTabs accepts only telos and never calls the callback. LifeosConfig checks Bun's import.meta.main without a declaration in the dashboard compilation environment.

The characterization gate renders the actual SubTabs component with the public native TELOS sample. The output with the callback equals the output without it. The callback count is zero. Both candidates produce markup SHA256 85d7244cc5c904c7e98c104ddc7adcad2ccb988366012c68c70cedafdddd42b0. Actual Bun subprocesses verify direct configuration execution and module import in a disposable home.

The shell now passes only the accepted prop. The CLI checks a local import.meta reference for the main property and a true value. The direct import.meta expression still fails TypeScript narrowing; the first gate retains that result. The second gate passes all four tests, including the full strict dashboard type check.

The first adjacent runner omits its independent native control source. One editor comparison fails with the missing environment variable. The failed output remains in missing-control-adjacent-gate.txt. The corrected runner uses that control source and holds its implementation and source tree fixed for the accepted checks.

The overview and other native memory consumers remain release gates. These changes do not activate or deploy managed memory.

The accepted adjacent gate passes all 24 tests in 39.970 seconds with warnings treated as errors and no skips. The full dashboard build exits with status zero. It retains the existing multiple-lockfile workspace warning and ambiguous duration utility warning. The strict TypeScript check passes independently of the native build configuration.
