# Web cache reads and LifeOS Safety

On 2026-09-28, I checked how Hermes delivers long web extracts and browser snapshots. Both store the omitted text under `cache/web` and return a `read_file` instruction to the model. LifeOS's installed Safety hook matches `WebFetch`, not `Read`. Before this change, a later Read of the stored page missed that warning.

The bridge now identifies a Read whose resolved path is inside Hermes's web cache. It asks Hermes for the backend-visible cache path, so the same classification can work when a backend presents the cache under a mounted path. Only that Read result also matches `WebFetch` PostToolUse registrations. Other Reads keep their existing routing. Generic Read hooks and the transcript retain the `Read` name.

A regression failed before the change because the cache Read produced no Safety context. Afterward, the cache Read received one `WebFetch` hook result, an ordinary note received none, and both transcript entries stayed `Read`. A second test covered a simulated backend mapping from a host cache path to `/root/.hermes/cache/web`. The full `.212` suite passed 112 tests.

A native probe through the Hermes launcher ran the installed `Safety.hook.ts` against a synthetic cache Read. It returned the external-content warning. The same probe passed an ordinary local note and received no warning. Its transcript held two Read calls and results. No page was fetched and no cache file was written. A live remote backend read of a mounted cache file remains unverified.
