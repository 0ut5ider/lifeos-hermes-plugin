PR23 corrects the release manager when the service HOME differs from the profile account. The manager resolves the physical owner account and preserves the native data HOME.

The first review finds one missing installed-caller regression. Three tests close this finding. The second review is clear at program commit a1abb579.

Validation passes: 39 focused tests, 683 archive-bound integration tests, and 716 native Hermes tests in 38 files. The integration run has no skips or ResourceWarnings. The archive file map matches before and after the tests.

The synthetic daily-layout guest passes update, rollback, and controlled interruption recovery. All three service HOME bindings, the model mapping, and memory references stay unchanged. A fact saved after the update survives rollback and recovery. The final dashboard apply selects the exact 0.4.3 archive.

The corrected off-server whole-guest restore passes for 64,282 artifacts, nine program targets, and all three Atlas cases. The guest also passes a real reboot without manual service starts. The qualification operator review finds one missing journal seal check. Four regression controls reproduce and close this finding. Final evidence review remains in progress. Daily .253 stays on 0.3.1. Development .252 stays on 0.4.2. Published 0.4.2 assets stay immutable. Release publication and daily promotion remain pending.
