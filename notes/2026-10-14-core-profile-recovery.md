# Core editor profile recovery, October 14

The new core-file editor passes its initial six actual HTTP owner/read/save controls. A controlled child exits with status 86 after publishing a reviewed profile edit. The source-file recovery case passes. The profile recovery case fails when the next action is a memory search rather than another editor read.

The HTTP envelope returns 200, but the actual tool status is `unavailable`. Instrumenting that status yields `The core file changes its profile boundary`. The new resolver uses the lexical default `.hermes` profile alias. Its parent-path check compares that alias with the physical directory and refuses the legitimate selected profile. The interrupted file remains changed with mode 0600 instead of its original 0640.

The core resolver now uses the captured physical profile while checking that the selected alias still resolves to it. It also verifies owner directory permissions and that the profile configuration binds the same LifeOS root. Native core imports receive the same physical profile. All 18 expanded checks pass after this correction, including cross-route recovery, later-edit preservation, and owner revocation. This changes only the staged editor. The daily 0.4.3 package stays unchanged.
