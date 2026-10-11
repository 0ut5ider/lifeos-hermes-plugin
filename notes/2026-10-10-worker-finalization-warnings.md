# Worker warnings survived warnings-as-errors

Date: 2026-10-10. Question: Why did the fresh-worker gate exit zero with ten ResourceWarnings?

The independent PR7 review found no blocking product defect. Its 35 storage checks nevertheless printed ten warnings for unclosed stdout and stderr pipes. The primary repeated that gate and reproduced all ten warnings. Unittest reported success and returned zero even with `-W error::ResourceWarning`. Python raised the warnings during file finalization and printed them as ignored exceptions, outside the ordinary test failure path.

Five actual worker processes had two captured pipes each. The tests called `Popen.wait`, which waits for termination but does not drain and close those streams. The tests now call `communicate`, preserve failure output in assertions, and still terminate the complete native process tree in the interruption case. The change affects only test subprocess handling.

The follow-up runner also rejects warning and ignored-exception lines in captured output. The baseline therefore fails its clean-output gate while preserving the underlying zero unittest exit. The [follow-up evidence](../docs/verification/2026-10-10-pr7-review-followup/before.json) records both outcomes. The correction leaves the frozen plugin package and its 200 program hashes unchanged.

The primary follow-up passes all 66 review tests with zero warning lines and no skipped cases. The template audit and exact release-certificate reproduction also pass. The 490-test batch and remote installation are not repeated because no plugin or native program byte changes.
