# Wiki source review observations

Date: 2026-10-01. The Astra review uses disposable local fixtures and synthetic text.

The existing 107-case read gate passes, but a private filename still appears in native page titles, slugs, and tree labels. Body validation does not validate emitted path metadata. The collector now submits each full source path with its body to the existing native private-content and control-character validator. Rejected sources remain unchanged on disk.

The traversal probe consumes all 6,000 non-Markdown entries before refusing the directory. Hidden populations and unrelated WORK entries have no effective count bound. Python 3.14 `Path.iterdir()` materializes directory entries before yielding them. Counting its yields therefore cannot bound the scan. Streaming `os.scandir()` counts every yielded entry before filtering or sorting. All retained silos share the 2,048-entry budget. The scan refuses on entry 2,049.

Five new tests fail against the preceding implementation. All 23 corpus cases pass after these two plugin corrections. The distributed native patches remain unchanged. Independent closure and the neighboring read gate follow this result. Source classification, reviewed edits, mount publication, lifecycle, and ownership activation remain separate open requirements.

The expanded primary gate passes 124 tests in 121.219 seconds. Fresh Astra closure passes 66 tests in 47.903 seconds and ten probes, with no additional material defect. The primary independently reruns all ten probes. Exactly 2,048 hidden entries succeeds, and entry 2,049 refuses before the remaining population is read. Ordinary grouping, fallback titles, backlinks, private body exclusion, and physical-path guards remain operational. The public source probe still admits 58 of 60 pages. Ownership remains disabled.
