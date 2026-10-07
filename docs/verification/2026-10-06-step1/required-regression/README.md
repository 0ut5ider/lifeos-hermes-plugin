# Required regression fixture controls

Date: 2026-10-06. Eleven tests that require extra fixtures pass in separate source-bound runs. Seven alias-dependent checkpoint, partial patch, ISA gate, and remote ISA tests use an isolated HOME. Four additional controls verify actual browser content classes, installed plugin commands, a tagged installed source tree, and real title inference.

The browser control uses pinned agent-browser 0.26.0 and Chromium 145.0.7632.6. It serves a synthetic loopback page, reads navigation, snapshot, console, and image results, then closes the browser. It changes no active browser or gateway profile. The command control copies a real dependency generation and uses synthetic HTTP responses. It provides launcher and provider transport evidence. The title control uses actual private inference through the installed child adapter. It retains successful wire hashes. Full request bodies stay private on the development fixture.

The tagged fixture initially tags the whole source repository. Native VersionDrift scans installed-root paths, so that layout provides no matching changed files. A separate local tag points to a commit containing the actual install subtree. The measured warning and once-per-session state then pass. The upstream source repository remains unchanged.

The alias-dependent partial patch tests use component fixture file operations. Actual successful and operating-system-denied partial batch operations have separate retained functional controls. These eleven tests classify required fixtures for the final regression gate. They do not convert the earlier full regression run, which has one service error, into a clean result.
