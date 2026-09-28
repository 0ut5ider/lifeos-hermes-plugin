# Live browser result safety routing

Date: 2026-09-28. A prior `.212` probe proved that a real `browser_snapshot` result reached the installed LifeOS `WebFetch` safety matcher. The bridge mapped seven other content-bearing browser tool names in tests, but those tests supplied synthetic result text.

The new optional test served a page on `127.0.0.1` with a title, page marker, console message, and image alt text. Hermes's real `browser_navigate`, `browser_snapshot`, `browser_console`, and `browser_get_images` tools each returned success. For each result, the bridge invoked a `WebFetch` PostToolUse matcher. The recorded payloads contained the page marker, console marker, or image marker expected for that tool. The real Chromium test passed in 4.822 seconds on `.212`, then closed its browser session and loopback server.

`browser_vision` needs a configured vision provider. `browser_cdp` needs a connected Chrome DevTools Protocol endpoint, and `browser_dialog` needs its supervisor. `browser_exec` belongs to the separate Browser Use backend. Their native results remain unverified on this test install. The bridge has synthetic matcher tests for their names; those tests do not prove end-to-end delivery.
