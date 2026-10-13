# PR18 final review and default GitHub installation replay

The review covers the complete PR18 product diff and the final review corrections at b9d353cdf1cca571194d1f60c269efdc97880fe5.

The first review identifies two defects. The running dashboard profile is not bound to the selected installation. Synchronous preparation does not hold the dashboard preparation lease. The recorded failing probes reproduce both defects before correction.

The next review identifies redundant decoding of effective systemd percent signs. The primary real unit test also finds that systemctl omits empty EnvironmentFiles. The parser preserves the effective path and rejects nonempty environment files.

The actual CT106 trial identifies the official bundled Hermes launcher as an additional command shape. The adapter recognizes only that exact inline source. Real child tests reject foreign profiles and unrelated inline programs.

The final actual CT106 service component trial passes. A foreign profile keeps PID 5018 after admission refuses. No service journal is written. A matching profile drains and restarts from PID 5030 to PID 5052. The main dashboard PID 4038, configuration hash, and release hash stay unchanged. Temporary units and synthetic profiles are removed. This trial does not claim complete installation acceptance.

The primary repeats 111 selected tests (108 executed and three optional fixture skips), seven archive and lease controls without skips, three UI contracts, and eight version tests. The complete archive-bound rc.3 qualification and post-merge default GitHub web replay are separate gates.

Published rc.1 and rc.2 assets remain historical checkpoints. The corrected candidate uses rc.3. Production and development deployments are outside this replay.
