# Native wiki retained sources

Date: 2026-10-01. This unit extends authenticated native wiki reads to retained silos and installed documentation. It uses private disposable profiles and the prepared public LifeOS and Hermes trees. No running installation changes.

## Outcomes

- [Initial regression](before.txt): ten collector cases expose absent sources and missing limits. Six failures and one error reproduce the initial gap.
- [Native read mismatch](documentation-before.txt): two tests fail because valid Markdown and larger read content use a fact write validator.
- [Before documentation probe](documentation-before-probe.json): only 2 of 60 native pages are admitted. Write validation rejects 54 pages for frontmatter and 4 for size.
- [Collector cases](corpus.txt): 18 cases pass in 9.360 seconds. Native standalone page bodies and tree grouping match after timestamp precision normalization. Private markup, invalid text, path redirects, retired content and labels, hidden sources, ambiguous slugs, source count, file size, and corpus size have behavioral coverage.
- [After documentation probe](documentation-after-probe.json): 58 of 60 pages are admitted. The three measured collections take 0.342, 0.345, and 0.359 seconds. The raw corpus contains 1,443,524 bytes. The largest file has 145,192 bytes.
- [Distributed focused gate](focused.txt): 122 cases pass in 105.487 seconds without skips, errors, or failures. The gate includes actual HTTP authentication, owner revocation and forget, canonical reads, retained startup readers, native standalone rendering, and ordered source preparation.
- [Completion marker](focused.done): exit status 0. The [runner](run_gate.py) records the exact prepared source and command.

The collector includes native work summaries, learning lessons and synthesis, wisdom frames and principles, research outputs, documentation, algorithm documents, and the installed system prompt. It uses the existing native renderer for page parsing, search, excerpts, backlinks, tree grouping, and graph output. The native worker preserves the supplied group field. All source selection remains plugin-owned. No native patch file or Hermes patch group is added.

## Explicit limits

`DOCUMENTATION/Memory/CortexContract.md` and `DOCUMENTATION/Memory/MemorySystem.md` contain literal private-boundary examples. Native private-content filtering changes those strings. The existing source policy excludes those complete pages. The probe does not establish all-document parity.

Unclassified sources require unrestricted owner recall. A source older than the latest relevant correction or forget remains excluded, including documentation. Exact physical paths, current retirement checks, UTF-8, canonical control rules, a 256 KiB file limit, a 3 MiB corpus limit, and a 2,048 source count limit remain enforced.

This unit does not govern Observability Knowledge edits, all native source readers, sidecar editors, the actual mount renderer, derived publication, restricted delivery, lifecycle, or recoverable ownership setup. It does not pass the full release gate. The complete regression follows the remaining source changes. No ownership activation, deployment, push, or changes to `.211`, `.212`, or `.213` occur.
