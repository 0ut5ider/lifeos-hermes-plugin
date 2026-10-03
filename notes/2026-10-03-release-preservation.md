# 2026-10-03: Release preservation on .212

The release targets merged plugin commit `d5dafbc` on two existing profiles. The Discord profile needs 88 code-file changes; the browser profile needs nine. An exact file plan keeps local helpers and personal data in place. The disposable rehearsal verifies the copied bytes, restored bytes, removal of added files, and preservation of later data for both plans.

The first browser verification calls `Mount.ts --check` without owner authority. The merged memory policy refuses it. Issuing a short-lived grant from the staged package also fails because the grant validator binds the installed connector path. Loading the installed administrative module fixes that boundary. A direct prompt-preview diagnostic then proves that the grant environment cannot find Bun. Preserving the release PATH completes the check. The prompt has 37,863 characters and remains current. These changes affect the verification script, not the merged plugin.

The Discord recorder startup file exists at preflight and is absent from the profile snapshot made after dependency staging. The first real tool turn succeeds but creates no matching capture events. The inspection confirms the missing startup file in the selected Python interpreter. The release recreates the account-private startup file with the existing recorder source and config. The exact package-manager operation that removes it is not established.

A revision metadata update writes the recorder config as root. A fresh Python process reports `Development capture startup failed (PermissionError)`. The config has UID 0 instead of UID 1004. Restoring UID 1004 fixes startup. The next tool check records 496 events in its verification window, including 34 hook starts and 34 completions, with no failed hooks or capture gaps. The release restarts the existing Discord services to load the preserved recorder configuration.

The real tool turn also refreshes `ARCHITECTURE_SUMMARY.md`. The native baseline then reports one changed file. A byte comparison against the saved profile shows that only `last_updated` changes from September 30 to October 3. The operator reviews that generated timestamp and renews the baseline. The final mount, source, service, and model checks pass.

The useful release boundary is wider than plugin files. Managed dependencies, interpreter startup files, native generated documents, and private recorder metadata all need explicit preservation checks. Successful model inference alone does not prove that diagnostics survived the release.
