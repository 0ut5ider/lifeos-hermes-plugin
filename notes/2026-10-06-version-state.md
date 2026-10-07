# Interrupted native version warning publication

Date: 2026-10-06. Step 1 requires the exact warning interval and preservation of prior valid state after interruption.

A controlled Date.now value verifies the native predicate at 60 minutes minus one millisecond, exactly 60 minutes, and plus one millisecond. The warning is suppressed only before the boundary. The bridge uses the actual installed-file baseline adapter during this component control. The preload changes the clock and no model response is fabricated.

The native marker write uses writeFileSync on the destination. A filesystem preload widens the actual truncate-before-write interval, signals the test, and waits. The test kills that process with SIGKILL. The previous valid state becomes zero bytes. This failure is about publication, not warning eligibility.

LifeOS already supplies atomicWriteText in its Pulse library. VersionDrift now uses that helper to write a private temporary sibling and rename it over the destination. The same interrupted write leaves the prior state byte-identical. A killed writer can leave a temporary sibling; readers do not treat that sibling as warning state. The fixture removes only its own temporary files. The exact interval and subsequent asynchronous delivery controls still pass.
