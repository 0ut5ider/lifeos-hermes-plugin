# Generated output blocked removal after real use

2026-10-15, disposable guest 192.168.8.244, installed checkpoint e813806f.

Removal preparation 1145c791317a4ecc963f1d6bdd679a34 stages the complete stock runtime after the host prerequisite is installed. It then refuses `LIFEOS/DOCUMENTATION/ARCHITECTURE_SUMMARY.md` because the current bytes differ from the qualified source. An authenticated read-only phase probe reproduces that refusal in `native_inventory`.

The existing drift module declares this exact path in `GENERATED_FILES`. The update planner excludes it from immutable system files. Native `RebuildArchSummary.ts` regenerates it during session lifecycle handling. The removal inventory already exempts generated output from its unknown-file scan, but its earlier qualified-file comparison still checks and selects the summary. A freshly installed unused store can therefore pass an inventory that refuses after normal use.

Two added controls reproduce the failure and constrain the correction. Removal retains the current generated summary through actual software publication and restoration. A linked summary and an unrelated owner document still refuse. A separate read-only candidate probe on the real guest admits 1,838 program files and 12 dependency roots, one fewer program file than the original unused-store inventory. The candidate source digest matches the local correction. This is a diagnostic candidate result, not installed removal acceptance.

The first 19-test correction run passes assertions but exposes an unclosed SQLite connection in the data-barrier test. The isolated original case reproduces that warning. The test now closes the connection explicitly. The verification runner also treats unhandled resource diagnostics as failure even when Python exits zero. The historical 223-test result remains assertion evidence and is not a clean qualification result.
