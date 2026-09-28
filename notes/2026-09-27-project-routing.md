# Project hook routing in one session

Date: 2026-09-27

An isolated Hermes process on `.212` used a temporary `HERMES_HOME` configuration that trusted two disposable Git repositories. Each repository had a different project `PreToolUse:Bash` registration writing the event's `cwd` and command to a temporary log. The bridge received two terminal tool calls under the same session ID, with a different `workdir` for each call.

The log contained exactly two events. The first had the first repository as `cwd` and `echo one`; the second had the second repository as `cwd` and `echo two`. The bridge's session project set contained both roots. The probe did not execute either shell command or change the running dashboard's trust configuration.

This verifies local per-tool project hook routing within one session. It does not establish file watching inside a remote or container backend.
