# Patch line accounting probe

Date: 2026-09-27

Hermes V4A patches contain removed and added lines. The bridge previously built a Claude-shaped Edit input with only `new_string`. LifeOS `ComplexityRatchet` computes net added lines from `new_string` minus `old_string`, so it counted a one-line replacement as one line of growth.

A local regression test first failed because `old_string` was absent from the PostToolUse payload. The adapter now collects lines prefixed with `-` into `old_string` and lines prefixed with `+` into `new_string` for each file. It keeps empty strings for additions, deletions, and moved destinations when the patch does not provide removed text.

On the isolated `.212` account, a temporary LifeOS root ran the installed `ComplexityRatchet` through the bridge. For a synthetic `-old` to `+new` patch, the old bridge recorded `cumulative: 1`; the corrected bridge recorded `cumulative: 0`. No real file was patched in this probe.

The patch provides changed lines, not a full preimage or postimage. A hook that needs unchanged context must read the file or use a Hermes tool result with that content.
