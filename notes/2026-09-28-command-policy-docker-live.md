# Native Bash policy through a Docker terminal

Date: 2026-09-28. The `.212` test host ran the patched Hermes terminal tool with a disposable `composer:2.8` container. The real installed LifeOS `Safety.hook.ts` ran through the bridge. The test used a disposable Hermes home and LifeOS state root, and Docker networking was disabled.

The first test setup left root-owned files inside the disposable home because Hermes mounted a persistent container home. Python could not remove the temporary directory after the test. Setting `TERMINAL_CONTAINER_PERSISTENT=false` gave Docker a temporary filesystem and made teardown work. The two abandoned temporary directories were removed with sudo. No test container remained.

The completed test sent `curl -I http://192.168.8.1:9` through `terminal_tool`. LifeOS recorded a neutral permission decision. Hermes presented the command to the approval callback; the callback denied it, and the terminal returned `status: blocked`. Docker did not execute curl. A later `echo 67890` in the same disposable container returned exit code zero and its output; LifeOS recorded allow and Hermes did not prompt. The final verification took 2.465 seconds.

The test account received a temporary access control entry on `/run/docker.sock`. That entry was removed after verification. The container and its temporary directories were removed. Production `.211` and `.213` were untouched.
