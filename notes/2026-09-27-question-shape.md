# Clarify question shape probe

Date: 2026-09-27

Hermes `clarify` takes a top-level `question`, `choices`, and `multi_select`. The installed LifeOS `TabState` PreToolUse hook reads Claude Code's `AskUserQuestion.questions[0].question` or its short `header`. The bridge mapped the tool name but passed Hermes's input object unchanged. A native `.212` probe with the Hermes shape stamped the fallback title `Awaiting input`.

The bridge now wraps the question in Claude's `questions` list, turns each string choice into a labeled option, and maps `multi_select` to `multiSelect`. A local test using Hermes's actual argument shape failed before the change and passed afterward. With the translated payload, the installed native hook stamped `Which project should` from `Which project should we review first?` under a temporary home. The hook exited zero. No persistent tab state was changed by the probe.
