# 2026-10-05: A timed-out native installer leaves its dependency worker alive

The first named fresh-store test times out after 300 seconds inside native DeployCore. The remaining process is `bun install` in the Remotion tool directory. Its parent and the test runner finish, but the dependency worker remains alive with process ID 2480789 in the detached test group 2480318. The fixture cleanup removes its working tree while that worker still exists.

The plugin uses `subprocess.run(..., timeout=300)`. Python terminates the direct child on timeout. It does not terminate the native child's descendants. A separate real-process control confirms a child can publish a marker after its parent times out at 0.2 seconds. The marker is absent when the timeout returns and present 0.8 seconds later.

The correction runs each native step in its own process group and cancels the complete group on timeout or interruption. Real timeout and SIGINT controls verify that descendants cannot publish after cancellation. The final installer gate passes 20 tests. The failed dependency run does not count as fresh-store readiness. The original synthetic profile remains unchanged. The orphaned test group is terminated after its identity is checked.

Ordinary Remotion dependency resolution times out after 90.092 seconds. The no-cache control times out after 90.093 seconds. This disproves the proposed cache remedy. The verified frozen lock completes in 0.042 seconds. The internal resolver cause remains unknown. Pinning existing dependencies is an independent release requirement.

The source TELOS dashboard lock also fails a direct frozen install because it does not match its package manifest. The successful native control supplies the matching lock. The release catalog covers all 12 source package trees. The installer seeds verified locks only in an empty target before native deployment. It refuses later lock edits. The complete named fresh-store test then passes in 15.385 seconds and retains all six native steps.

The [named-store evidence](../docs/verification/2026-10-05-named-fresh-store/README.md) retains the failed controls, final tests, source hashes, and lock provenance. No production deployment occurs.
