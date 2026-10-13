Date: 2026-10-13
Role: Independent focused historical-worker interface reviewer
Question: Does the new first-install service guard refuse an unsupported historical package safely and report that refusal through the correct namespaces?
Model: gpt-6.1-sol, high reasoning effort

Reviewed head: 8e020023b4d761b94495504109cc951a09ab98ab
Comparison base: c9ada3bf705ef60e53b5ebee15fa863b5d1df52a
Exact code identities: reviewed-file-identities.json

## Result

This bounded follow-up is clear. I found no concrete defect in the guard, safe error class, namespace handling, or the revised refusal test. It adds refusal of an unsupported interface. It does not execute a compatibility path for historical first-install workers.

The controls below establish historical refusal and responsiveness during that refusal. They do not establish successful current-package review, first installation, update, or release qualification. The current guest's actual HTTP 200 review and concurrent authenticated health acceptance remain required.

## Source review

require_fresh_services inspects the qualified source controller signature and requires its explicit first_installation parameter. The current controller has that parameter. The historical 0.4.0-dev.1 prepared source does not.

CLI prepare checks the interface after package validation and installation selection, before prepare_runtime. The first-install controller constructor also checks it before invoking the source controller. This changes the known unsupported historical case from an uncaught TypeError to a bounded ReleaseRejected subclass.

The guard does not replace a historical controller, change its constructor arguments, create service definitions for it, or admit a historical plan as current. Existing installed updates retain their three-service interface. Unsupported artifact refusal occurs before active program or native publication.

FirstInstallationUnavailable constructs a fixed message. Its text contains no profile path, credentials, user values, exception traceback, or private operation narration. The asynchronous preparation process catches that exact class and records preparation_failed with the fixed message. The dashboard review route returns HTTP 409 with the same fixed message.

The dynamic dashboard namespace is important because importing the same Python source through two package namespaces creates different class identities. The API imports release_services through the same namespace as its commands, preparation, and worker. The actual namespace probe confirms that the dashboard preparation class and dashboard services class are identical. It also confirms the ordinary CLI/preparation package class identity. The historical source raises the expected dashboard class and the handler can match it.

The signature guard is a check for the known qualified source interface. It is not a claim that arbitrary future controller implementations are compatible. Their behavior still requires full package qualification.

## Test interpretation

The renamed historical test intentionally expects HTTP 409. It also verifies that the historical native destination remains absent and that a concurrent authenticated health request completes within its bound while the review holds the operation lock.

Changing this historical fixture's expected result is appropriate because the fixture lacks the required service interface. It must remain labeled refusal evidence. The test does not replace the required successful review responsiveness check on the current managed guest.

The accompanying README and note make this distinction explicit. During isolated prerelease acceptance, the user must select the exact test release. The stable 0.4.1 release remains unchanged. No historical first-install compatibility execution is added.

The previously reviewed service-path boundary is now committed. The Linux first-install scope still requires physical paths without whitespace, dollar signs, quotes, backslashes, semicolons, or closing braces. Literal percent specifiers remain supported. The managed-dashboard and operator-recovery limits from earlier rounds remain unchanged.

## Controls run

The focused command runs test_release_configuration, test_release_preparation, test_release_services, and test_release_dashboard with the actual historical prepared operation fixture. All 22 tests pass in 6.574 seconds. There are no skips, errors, or failures. The run uses -B and treats ResourceWarning as an error.

The actual HTTP historical refusal test passes. It checks the fixed first-install refusal and concurrent authenticated health. The actual process-selection and systemd parser component controls also pass in this command.

The separate guard_namespace_probe.py passes with empty stderr. It loads the real current and historical source controllers, confirms their signature difference, catches the historical refusal through the dashboard class, and checks both namespace identity pairs. It does not execute installation or read personal records.

Unittest writes its normal verbose result to python.stderr. python.stdout is empty. There are no unexpected warnings or diagnostics.

## Remaining evidence gates

1. Successful current guest HTTP 200 review and concurrent authenticated health.
2. Actual fresh installation using the final sealed source.
3. User-initiated update acceptance after that installation.
4. Actual caught-error and abrupt-exit recovery, with public CLI and retained-worker paths distinguished.
5. Final native and integration qualification, certificate checks, and review of the sealed artifact identities.

I did not edit product source, mutate a guest, publish a release, commit, push, or call memory tools. This review does not select either live development or daily programs.

## Raw data

- followup.diff: complete c9-to-8e source, tests, and documentation diff.
- reviewed-file-identities.json: reviewed head and source hashes.
- python.stdout/python.stderr: exact focused 22-test run.
- guard_namespace_probe.py: repeatable source/interface and namespace check.
- guard-namespace-probe.json: real current/historical signature and identity result.
- guard-namespace-probe.stderr: empty diagnostics.
